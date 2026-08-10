from __future__ import annotations
import hashlib
import json
import os
from obg.models.disk import DiskInfo
from obg.utils.runner import run


def _read_proc_mounts() -> list[str]:
    try:
        with open("/proc/mounts") as f:
            return f.readlines()
    except OSError:
        return []


def _get_boot_device(mounts: list[str]) -> str | None:
    for line in mounts:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "/":
            return parts[0]
    return None


def _is_disk_mounted(device_name: str, mounts: list[str]) -> bool:
    dev_prefix = f"/dev/{device_name}"
    for line in mounts:
        parts = line.split()
        if parts and parts[0].startswith(dev_prefix):
            return True
    return False


def _detect_transport(device_name: str, tran_field: str | None) -> str:
    if tran_field == "usb":
        driver_link = f"/sys/block/{device_name}/device/../../driver"
        try:
            driver_path = os.path.realpath(driver_link)
            driver = os.path.basename(driver_path)
            if driver == "uas":
                return "usb-uas"
            return "usb-bot"
        except OSError:
            return "usb-unknown"
    if tran_field == "sata":
        return "sata"
    if tran_field == "nvme":
        return "nvme"
    if tran_field:
        return tran_field
    return "unknown"


def _check_smart(device: str) -> bool:
    try:
        result = run(["smartctl", "-i", device], timeout=10)
    except Exception:
        return False
    if result.returncode != 0:
        return False
    for line in result.stdout.splitlines():
        if "SMART support is: Available" in line:
            return True
        if "SMART overall-health" in line:
            return True
        if "NVMe" in line and "SMART" in line:
            return True
    # NVMe devices always expose SMART/Health (no "support" line in -i output).
    if "NVMe" in result.stdout:
        return True
    return False


def _parse_capacity_human(size_bytes: int) -> str:
    if size_bytes >= 1_000_000_000_000:
        return f"{size_bytes / 1_000_000_000_000:.1f} TB"
    if size_bytes >= 1_000_000_000:
        return f"{size_bytes / 1_000_000_000:.1f} GB"
    return f"{size_bytes / 1_000_000:.1f} MB"


def _is_rotational(dev: dict) -> bool:
    # lsblk emits ROTA as JSON bool/0/1; unknown (missing) defaults to True so
    # we err on the side of showing the drive rather than hiding it.
    rota = dev.get("rota", True)
    return not (rota is False or rota == "0" or rota == 0)


def _is_unsupported(dev: dict) -> bool:
    name = dev.get("name", "")
    # Block pseudo/special devices entirely
    if name.startswith(("loop", "zram", "ram", "dm-", "sr", "fd")):
        return True
    # Only whole disks
    if dev.get("type") not in ("disk", "loop"):
        return True
    # Only mechanical HDDs (rotational media) are valid validation targets.
    # SSDs and NVMe drives are shown in the UI but disabled (shown, not usable).
    if not _is_rotational(dev):
        return True
    return False


def list_disks() -> list[DiskInfo]:
    cmd = [
        "lsblk", "-J", "-b", "-o",
        "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,MODEL,SERIAL,REV,TRAN,ROTA,PHY-SEC,LOG-SEC,PTTYPE,WWN",
    ]
    result = run(cmd, timeout=15)
    if result.returncode != 0:
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    mounts = _read_proc_mounts()
    boot_device = _get_boot_device(mounts)

    disks: list[DiskInfo] = []
    for dev in data.get("blockdevices", []):
        if dev.get("type") != "disk":
            continue

        name = dev.get("name", "")
        size = dev.get("size", 0) or 0
        is_unsupported = _is_unsupported(dev)
        boot_disk = boot_device is not None and boot_device.startswith(f"/dev/{name}")
        mounted = _is_disk_mounted(name, mounts)

        model = dev.get("model") or "Unknown"
        serial = dev.get("serial") or "Unknown"
        interface = dev.get("tran") or "unknown"
        transport = _detect_transport(name, dev.get("tran"))
        rotational = _is_rotational(dev)

        disk_info = DiskInfo(
            device=f"/dev/{name}",
            model=model,
            serial=serial,
            firmware=dev.get("rev") or "Unknown",
            capacity_bytes=size,
            capacity_human=_parse_capacity_human(size),
            interface=interface,
            transport=transport,
            logical_sector=dev.get("log-sec", 512),
            physical_sector=dev.get("phy-sec", 512),
            smart_supported=_check_smart(f"/dev/{name}"),
            uas_enabled=(transport == "usb-uas"),
            current_fs=dev.get("fstype"),
            partition_table=dev.get("pttype"),
            is_mounted=mounted,
            is_boot_disk=boot_disk,
            temperature=None,
            power_on_hours=None,
            wwn=dev.get("wwn") or None,
            is_supported=not is_unsupported,
            rotational=rotational,
        )
        disks.append(disk_info)

    return disks


def list_mock_disks(image_path: str) -> list[DiskInfo]:
    try:
        size = os.path.getsize(image_path)
    except OSError:
        return []
    name = os.path.basename(image_path)
    return [DiskInfo(
        device=os.path.abspath(image_path),
        model=f"Mock Disk ({name})",
        serial="MOCK-" + hashlib.md5(image_path.encode()).hexdigest()[:8].upper(),
        firmware="1.0",
        capacity_bytes=size,
        capacity_human=_parse_capacity_human(size),
        interface="virtual",
        transport="mock",
        logical_sector=512,
        physical_sector=4096,
        smart_supported=False,
        uas_enabled=False,
        current_fs=None,
        partition_table=None,
        is_mounted=False,
        is_boot_disk=False,
        temperature=None,
        power_on_hours=None,
        is_supported=True,
        is_mock=True,
    )]


def verify_identity(device: str, expected_model: str, expected_serial: str) -> bool:
    cmd = ["lsblk", "-o", "NAME,MODEL,SERIAL", device, "-J"]
    result = run(cmd, timeout=15)
    if result.returncode != 0:
        return False
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    blockdevices = data.get("blockdevices", [])
    if not blockdevices:
        return False
    dev = blockdevices[0]
    model = (dev.get("model") or "").strip()
    serial = (dev.get("serial") or "").strip()
    # Both sides carry inconsistent whitespace from lsblk; compare normalized.
    return model == expected_model.strip() and serial == expected_serial.strip()
