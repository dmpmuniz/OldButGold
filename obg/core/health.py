from __future__ import annotations
import re
import time
from datetime import datetime
from typing import Callable
from obg.models.disk import SmartData
from obg.utils.runner import run


def _extract_raw_value(line: str) -> int | None:
    parts = line.split()
    if not parts:
        return None
    try:
        return int(parts[-1])
    except (ValueError, IndexError):
        return None


def _parse_attribute_table(output: str) -> dict[int, int]:
    attrs: dict[int, int] = {}
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("ID#") or line.startswith("="):
            continue
        parts = line.split()
        if len(parts) < 10:
            continue
        try:
            attr_id = int(parts[0])
        except ValueError:
            continue
        raw_val = _extract_raw_value(line)
        if raw_val is not None:
            attrs[attr_id] = raw_val
    return attrs


class SmartReadError(Exception):
    """Raised when smartctl cannot be run (missing tool, no permission, device open failed)."""


def read_smart(device: str) -> SmartData | None:
    result = run(["smartctl", "-a", device])
    if result.returncode == 4:
        # Device open failed — usually permission / not found. Surface as an error
        # rather than silently returning None (which would force a FAILED classification).
        raise SmartReadError(
            f"smartctl could not open {device} (rc={result.returncode}). "
            "Root privileges are required to read SMART data."
        )
    if result.returncode != 0:
        raise SmartReadError(
            f"smartctl failed on {device} (rc={result.returncode}): {result.stdout.strip() or result.stderr.strip()}"
        )

    output = result.stdout

    if _is_nvme(output):
        return _parse_nvme(device, output)

    overall_health = "UNKNOWN"
    health_match = re.search(
        r"SMART overall-health self-assessment test result:\s+(\S+)", output
    )
    if health_match:
        overall_health = health_match.group(1)

    attrs = _parse_attribute_table(output)

    temperature = attrs.get(194)
    power_on_hours = attrs.get(9)

    return SmartData(
        overall_health=overall_health,
        reallocated_sectors=attrs.get(5, 0),
        pending_sectors=attrs.get(197, 0),
        uncorrectable_sectors=attrs.get(198, 0),
        crc_errors=attrs.get(199, 0),
        temperature=temperature,
        power_on_hours=power_on_hours,
        raw_output=output,
        collected_at=datetime.now(),
    )


def _is_nvme(output: str) -> bool:
    # NVMe devices expose a SMART/Health Information log and never an ATA
    # attribute table ("SMART Attributes Data Structure"). Detect via the
    # NVMe-specific markers so we don't mis-parse them as ATA (all zeros).
    nvme_markers = (
        "SMART/Health Information" in output,
        "Media and Data Integrity Errors:" in output,
        "Percentage Used:" in output,
        "Available Spare:" in output,
    )
    ata_marker = "SMART Attributes Data Structure" in output
    return any(nvme_markers) and not ata_marker


def _parse_nvme(device: str, output: str) -> SmartData:
    # NVMe has no ATA attribute table. Derive real health signals from the
    # SMART/Health Information log instead of returning all-zero placeholders.
    critical_warning = 0
    m = re.search(r"Critical Warning:\s*0x([0-9a-fA-F]+)", output)
    if m:
        critical_warning = int(m.group(1), 16)

    # Critical Warning bits: 0=raw, 1=temp, 2=spare, 3=readonly, 4=volatile,
    # 5=media errors, 6=any. Non-zero => drive is not healthy.
    overall_health = "FAILED" if critical_warning != 0 else "PASSED"

    temp_m = re.search(r"Temperature:\s*(\d+)\s*Celsius", output)
    temperature = int(temp_m.group(1)) if temp_m else None

    poh_m = re.search(r"Power On Hours:\s*(\d+)", output)
    power_on_hours = int(poh_m.group(1)) if poh_m else None

    # Media and Data Integrity Errors — NVMe's analog of uncorrectable sectors.
    media_m = re.search(r"Media and Data Integrity Errors:\s*(\d+)", output)
    uncorrectable = int(media_m.group(1)) if media_m else 0

    # Available Spare / Percentage Used give a reallocation-style signal.
    spare_m = re.search(r"Available Spare:\s*(\d+)%", output)
    used_m = re.search(r"Percentage Used:\s*(\d+)%", output)
    reallocated = 0
    if used_m and spare_m:
        reallocated = int(used_m.group(1))

    # NVMe has no separate pending/CRC counters; map media errors to uncorrectable.
    return SmartData(
        overall_health=overall_health,
        reallocated_sectors=reallocated,
        pending_sectors=0,
        uncorrectable_sectors=uncorrectable,
        crc_errors=0,
        temperature=temperature,
        power_on_hours=power_on_hours,
        raw_output=output,
        collected_at=datetime.now(),
    )


def run_short_test(device: str, on_output: Callable[[str], None] | None = None) -> bool:
    result = run(["smartctl", "-t", "short", device])
    if result.returncode not in (0, 2):
        return False
    return poll_smart_test(device, timeout_seconds=300, on_output=on_output)


def poll_smart_test(
    device: str,
    timeout_seconds: int,
    on_output: Callable[[str], None] | None,
) -> bool:
    deadline = time.monotonic() + timeout_seconds
    poll_interval = 5
    start_time = time.monotonic()
    last_pct = 0
    while time.monotonic() < deadline:
        result = run(["smartctl", "-a", device])
        if result.returncode not in (0, 2):
            return False
        output = result.stdout
        if "Completed without error" in output:
            return True
        if "Self-test execution status:" in output:
            status_match = re.search(r"Self-test execution status:\s*\(\s*(\d+)\s*\)", output)
            if status_match:
                code = int(status_match.group(1))
                if code == 0:
                    return True
                if code >= 249:
                    time.sleep(poll_interval)
                    continue
        pct_match = re.search(r"(\d+)% of test remaining", output)
        if pct_match and on_output:
            pct = 100 - int(pct_match.group(1))
            elapsed = time.monotonic() - start_time
            if pct > last_pct and pct > 0:
                rate = pct / elapsed
                eta_s = (100 - pct) / rate if rate > 0 else 0
                eta_str = f", ETA {int(eta_s // 60)}m{int(eta_s % 60):02d}s" if eta_s < 3600 else ""
                last_pct = pct
            else:
                eta_str = ""
            on_output(f"SMART test: {pct}% complete{eta_str}")
        time.sleep(poll_interval)
    return False
