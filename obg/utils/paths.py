from pathlib import Path


def config_file() -> Path:
    p = Path.home() / ".config" / "oldbutgold" / "config.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def reports_dir() -> Path:
    p = Path.home() / ".local" / "share" / "oldbutgold" / "reports"
    p.mkdir(parents=True, exist_ok=True)
    return p
