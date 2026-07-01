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


def read_smart(device: str) -> SmartData | None:
    result = run(["smartctl", "-a", device])
    if result.returncode == 4:
        return None
    if result.returncode != 0:
        return None

    output = result.stdout

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


def run_short_test(device: str) -> bool:
    result = run(["smartctl", "-t", "short", device])
    if result.returncode not in (0, 2):
        return False
    return poll_smart_test(device, timeout_seconds=300, on_output=None)


def run_long_test(device: str) -> bool:
    result = run(["smartctl", "-t", "long", device])
    if result.returncode not in (0, 2):
        return False
    return poll_smart_test(device, timeout_seconds=36000, on_output=None)


def poll_smart_test(
    device: str,
    timeout_seconds: int,
    on_output: Callable[[str], None] | None,
) -> bool:
    deadline = time.monotonic() + timeout_seconds
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
                    time.sleep(60)
                    continue
        pct_match = re.search(r"(\d+)% of test remaining", output)
        if pct_match and on_output:
            on_output(f"{pct_match.group(1)}% remaining")
        time.sleep(60)
    return False
