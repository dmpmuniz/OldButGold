import json
import pytest
from unittest.mock import patch, MagicMock
from obg.models.disk import DiskInfo
from obg.core.detector import list_disks, verify_identity


MOCK_LSBLK = {
    "blockdevices": [
        {
            "name": "sdb", "size": 2000398934016, "type": "disk",
            "mountpoint": None, "fstype": "ntfs",
            "model": "WD Elements 25A3", "serial": "WX41A19XXXXX",
            "tran": "usb", "rota": True, "phy-sec": 4096, "log-sec": 512,
            "min-io": 4096, "opt-io": 33553920, "alignment": 0
        },
        {
            "name": "sdc", "size": 500107862016, "type": "disk",
            "mountpoint": None, "fstype": None,
            "model": "Samsung SSD 860", "serial": "S3Z9NB0K123456",
            "tran": "sata", "rota": False, "phy-sec": 512, "log-sec": 512,
            "min-io": 512, "opt-io": 0, "alignment": 0
        },
        {
            "name": "nvme0n1", "size": 1000204886016, "type": "disk",
            "mountpoint": None, "fstype": None,
            "model": "Samsung NVMe SSD", "serial": "NVME123",
            "tran": "nvme", "rota": False, "phy-sec": 512, "log-sec": 512,
            "min-io": 512, "opt-io": 0, "alignment": 0
        },
    ]
}


def mock_run_factory(lsblk_json=None):
    def mock_run(command, timeout=None, on_output=None, input_data=None):
        cmd_str = " ".join(command)
        result = MagicMock()
        result.returncode = 0
        result.duration_seconds = 0.1
        if "lsblk" in cmd_str and "-J" in cmd_str:
            result.stdout = json.dumps(lsblk_json or MOCK_LSBLK)
        else:
            result.stdout = ""
        result.stderr = ""
        return result
    return mock_run


@patch("obg.core.detector.run")
def test_parse_lsblk_output(mock_run):
    mock_run.side_effect = mock_run_factory()
    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.readlines.return_value = ["/dev/sda / ext4 defaults 0 0\n"]
        disks = list_disks()
    hdds = [d for d in disks if d.is_supported]
    assert len(hdds) >= 1


@patch("obg.core.detector.run")
def test_unsupported_devices_shown(mock_run):
    mock_run.side_effect = mock_run_factory()
    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.readlines.return_value = ["/dev/sda / ext4 defaults 0 0\n"]
        disks = list_disks()
    unsupported = [d for d in disks if not d.is_supported]
    assert len(unsupported) > 0
    names = [d.device for d in unsupported]
    assert any("sdc" in n for n in names)
    assert any("nvme" in n for n in names)


@patch("obg.core.detector.run")
def test_filter_boot_disk(mock_run):
    lsblk_data = {
        "blockdevices": [
            {
                "name": "sda", "size": 500107862016, "type": "disk",
                "mountpoint": None, "fstype": "ext4",
                "model": "Boot Disk", "serial": "BOOT123",
                "tran": "sata", "rota": True, "phy-sec": 512, "log-sec": 512,
                "min-io": 512, "opt-io": 0, "alignment": 0
            }
        ]
    }
    mock_run.side_effect = mock_run_factory(lsblk_json=lsblk_data)
    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.readlines.return_value = ["/dev/sda1 / ext4 defaults 0 0\n"]
        disks = list_disks()
    assert len(disks) == 0


@patch("obg.core.detector.run")
def test_verify_identity_mismatch(mock_run):
    mismatch_data = {
        "blockdevices": [{"name": "sdb", "size": 2000398934016, "type": "disk",
                          "model": "WD Elements 25A3", "serial": "DIFFERENT_SERIAL"}]
    }
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(mismatch_data), stderr="", duration_seconds=0.1)
    result = verify_identity("/dev/sdb", "WD Elements 25A3", "WX41A19XXXXX")
    assert result == False
