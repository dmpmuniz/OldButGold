from __future__ import annotations
import json
import uuid
from datetime import datetime
from pathlib import Path
from obg.models.disk import DiskInfo

_SESSION_DIR = Path.home() / ".local" / "share" / "oldbutgold" / "sessions"


def _session_path(serial: str) -> Path:
    _SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return _SESSION_DIR / f"{serial}.json"


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
        "state": "in_progress",
        "badblocks_offset": 0,
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


def update_checkpoint(disk: DiskInfo, offset: float) -> None:
    path = _session_path(disk.serial)
    if not path.exists():
        return
    try:
        with open(path) as f:
            data = json.load(f)
        data["badblocks_offset"] = offset
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except (OSError, json.JSONDecodeError):
        pass


def complete_session(disk: DiskInfo) -> None:
    path = _session_path(disk.serial)
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def delete_session(serial: str) -> None:
    path = _session_path(serial)
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass
