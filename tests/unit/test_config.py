import json
import pytest
from obg.config import DEFAULT_CONFIG, load_config, save_config, reset_config, _config_path


@pytest.fixture(autouse=True)
def clean_config():
    path = _config_path()
    if path.exists():
        path.unlink()
    yield
    if path.exists():
        path.unlink()


def test_config_load_defaults():
    config = load_config()
    assert config == DEFAULT_CONFIG


def test_config_load_existing():
    path = _config_path()
    custom = {"filesystem": "ntfs"}
    with open(path, "w") as f:
        json.dump(custom, f)
    config = load_config()
    assert config["filesystem"] == "ntfs"
    assert config["profile"] == "recommended"


def test_config_save():
    save_config(DEFAULT_CONFIG)
    path = _config_path()
    assert path.exists()
    with open(path) as f:
        loaded = json.load(f)
    assert loaded == DEFAULT_CONFIG


def test_config_reset_to_defaults():
    save_config({"filesystem": "ntfs"})
    config = reset_config()
    assert config == DEFAULT_CONFIG


def test_config_invalid_values_use_defaults():
    path = _config_path()
    with open(path, "w") as f:
        json.dump({"filesystem": "btrfs", "profile": "ultra"}, f)
    config = load_config()
    assert config["filesystem"] == "ext4"
    assert config["profile"] == "recommended"
