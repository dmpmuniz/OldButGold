from pathlib import Path

import sys


def config_file() -> Path:
    p = Path.home() / ".config" / "oldbutgold" / "config.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _app_dir() -> Path | None:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return None


def reports_dir() -> Path:
    # Self-contained bundle keeps reports inside the app dir; source/dev falls back
    # to the XDG location so the repo isn't polluted.
    app = _app_dir()
    if app:
        p = app / "reports"
    else:
        p = Path.home() / ".local" / "share" / "oldbutgold" / "reports"
    p.mkdir(parents=True, exist_ok=True)
    return p