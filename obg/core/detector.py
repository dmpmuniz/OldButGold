from __future__ import annotations
import json
import os
import re
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
    result = run(["smartctl", "-i", device])
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if "SMART support is: Available" in line:
                return True
    return False


def _parse_capacity_human(size_bytes: int) -> str:
    if size_bytes >= 1_000_000_000_000:
        return f"{size_bytes / 1_000_000_000_000:.1f} TB"
    if size_bytes >= 1_000_000_000:
        return f"{size_bytes / 1_000_000_000:.1f} GB"
    return f"{size_bytes / 1_000_000:.1f} MB"


def _is_unsupported(dev: dict) -> bool:
    rota = dev.get("rota", False)
    if rota is True or rota == 1 or rota == "1":
        return False
    return True


def list_disks() -> list[DiskInfo]:
    cmd = [
        "lsblk", "-J", "-b", "-o",
        "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,MODEL,SERIAL,TRAN,ROTA,PHY-SEC,LOG-SEC,MIN-IO,OPT-IO,ALIGNMENT",
    ]
    result = run(cmd)
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
        is_ssd = _is_unsupported(dev)
        boot_disk = boot_device is not None and boot_device.startswith(f"/dev/{name}")
        mounted = _is_disk_mounted(name, mounts)

        model = dev.get("model") or "Unknown"
        serial = dev.get("serial") or "Unknown"
        interface = dev.get("tran") or "unknown"
        transport = _detect_transport(name, dev.get("tran"))

        disk_info = DiskInfo(
            device=f"/dev/{name}",
            model=model,
            serial=serial,
            firmware="Unknown",
            capacity_bytes=size,
            capacity_human=_parse_capacity_human(size),
            interface=interface,
            transport=transport,
            logical_sector=dev.get("log-sec", 512),
            physical_sector=dev.get("phy-sec", 512),
            min_io=dev.get("min-io", 512),
            optimal_io=dev.get("opt-io", 0),
            alignment_offset=dev.get("alignment", 0),
            rpm=None,
            smart_supported=_check_smart(f"/dev/{name}"),
            uas_enabled=(transport == "usb-uas"),
            current_fs=dev.get("fstype"),
            partition_table=None,
            is_mounted=mounted,
            is_boot_disk=boot_disk,
            temperature=None,
            power_on_hours=None,
            is_supported=not is_ssd and not mounted and not boot_disk,
        )
        disks.append(disk_info)

    return disks


def verify_identity(device: str, expected_model: str, expected_serial: str) -> bool:
    cmd = ["lsblk", "-o", "NAME,MODEL,SERIAL", device, "-J"]
    result = run(cmd)
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
    return model == expected_model and serial == expected_serial
