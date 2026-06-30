from __future__ import annotations
import json
from obg.utils.paths import config_file as _config_path

DEFAULT_CONFIG = {
    "profile": "recommended",
    "filesystem": "ext4",
    "label": "",
}

VALID_PROFILES = ["recommended", "extended"]
VALID_FILESYSTEMS = ["ext4", "ntfs", "exfat", "fat32"]


def load_config() -> dict:
    path = _config_path()
    if path.exists():
        try:
            with open(path) as f:
                user = json.load(f)
            cfg = DEFAULT_CONFIG.copy()
            if user.get("profile") in VALID_PROFILES:
                cfg["profile"] = user["profile"]
            if user.get("filesystem") in VALID_FILESYSTEMS:
                cfg["filesystem"] = user["filesystem"]
            if isinstance(user.get("label"), str):
                cfg["label"] = user["label"]
            return cfg
        except (json.JSONDecodeError, OSError):
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)


def reset_config() -> dict:
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()
