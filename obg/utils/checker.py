from __future__ import annotations
import os
import sys
from pathlib import Path


def _bundle_dir() -> Path | None:
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return None


def _tool_path(name: str) -> str | None:
    bundle = _bundle_dir()
    if bundle:
        tp = bundle / "tools" / name
        if tp.exists() and os.access(tp, os.X_OK):
            return str(tp)
    return None


def check_root() -> None:
    pass  # pkexec handles this in __main__


def check_dependencies() -> None:
    pass  # Runtime check happens at tool invocation
