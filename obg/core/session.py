from __future__ import annotations
import json
import uuid
from datetime import datetime
from pathlib import Path
from obg.models.disk import DiskInfo, SmartData

_SESSION_DIR = Path.home() / ".local" / "share" / "oldbutgold" / "sessions"


def _session_path(serial: str) -> Path:
    _SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return _SESSION_DIR / f"{serial}.json"


def _smart_to_dict(sd: SmartData) -> dict:
    return {
        "overall_health": sd.overall_health,
        "reallocated_sectors": sd.reallocated_sectors,
        "pending_sectors": sd.pending_sectors,
        "uncorrectable_sectors": sd.uncorrectable_sectors,
        "crc_errors": sd.crc_errors,
        "temperature": sd.temperature,
        "power_on_hours": sd.power_on_hours,
        "power_cycle_count": sd.power_cycle_count,
        "collected_at": sd.collected_at.isoformat(),
    }


def _smart_from_dict(d: dict) -> SmartData | None:
    if not d:
        return None
    try:
        return SmartData(
            overall_health=d["overall_health"],
            reallocated_sectors=d["reallocated_sectors"],
            pending_sectors=d["pending_sectors"],
            uncorrectable_sectors=d["uncorrectable_sectors"],
            crc_errors=d["crc_errors"],
            temperature=d.get("temperature"),
            power_on_hours=d.get("power_on_hours"),
            power_cycle_count=d.get("power_cycle_count"),
            raw_output="",
            collected_at=datetime.fromisoformat(d["collected_at"]),
        )
    except (KeyError, ValueError):
        return None


def create_session(disk: DiskInfo) -> str:
    sid = str(uuid.uuid4())
    data = {
        "session_id": sid,
        "created_at": datetime.now().isoformat(),
        "model": disk.model,
        "serial": disk.serial,
        "firmware": disk.firmware,
        "capacity_bytes": disk.capacity_bytes,
        "logical_sector": disk.logical_sector,
        "physical_sector": disk.physical_sector,
        "wwn": disk.wwn,
        "state": "in_progress",
        "badblocks_offset": 0,
        "current_stage": "",
        "smart_snapshot_a": None,
    }
    path = _session_path(disk.serial)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return sid


def find_session(disk: DiskInfo) -> dict | None:
    path = _session_path(disk.serial)
    if not path.exists():
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        fingerprint_match = (
            data.get("model") == disk.model
            and data.get("serial") == disk.serial
            and data.get("firmware") == disk.firmware
            and data.get("capacity_bytes") == disk.capacity_bytes
        )
        if fingerprint_match and data.get("state") == "in_progress":
            return data
        return None
    except (json.JSONDecodeError, OSError):
        return None


def _session_update(disk: DiskInfo, **kwargs) -> None:
    path = _session_path(disk.serial)
    if not path.exists():
        return
    try:
        with open(path) as f:
            data = json.load(f)
        data.update(kwargs)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except (OSError, json.JSONDecodeError):
        pass


def update_stage(disk: DiskInfo, stage: str) -> None:
    _session_update(disk, current_stage=stage)


def update_checkpoint(disk: DiskInfo, offset: float) -> None:
    _session_update(disk, badblocks_offset=offset)


def save_smart_snapshot_a(disk: DiskInfo, sd: SmartData) -> None:
    _session_update(disk, smart_snapshot_a=_smart_to_dict(sd))


def load_smart_snapshot_a(disk: DiskInfo) -> SmartData | None:
    path = _session_path(disk.serial)
    if not path.exists():
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        return _smart_from_dict(data.get("smart_snapshot_a"))
    except (OSError, json.JSONDecodeError):
        return None


def complete_session(disk: DiskInfo) -> None:
    path = _session_path(disk.serial)
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass
