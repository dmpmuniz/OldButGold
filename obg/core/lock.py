from __future__ import annotations
import fcntl
import os
from pathlib import Path


_LOCK_DIR = Path("/tmp") / "oldbutgold-locks"
_fds: dict[str, int] = {}


def _lock_path(device: str) -> Path:
    safe = device.replace("/", "_")
    return _LOCK_DIR / f"{safe}.lock"


def acquire_lock(device: str) -> bool:
    _LOCK_DIR.mkdir(parents=True, exist_ok=True)
    path = _lock_path(device)
    try:
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _fds[device] = fd
        return True
    except (OSError, IOError):
        return False


def release_lock(device: str) -> None:
    fd = _fds.pop(device, None)
    if fd is not None:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        except OSError:
            pass
    path = _lock_path(device)
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
