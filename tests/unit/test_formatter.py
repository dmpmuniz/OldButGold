from unittest.mock import patch, MagicMock
import pytest
from obg.core.formatter import format_filesystem


@patch("obg.core.formatter.run")
def test_format_ext4_command(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    on_output = MagicMock()
    format_filesystem("/dev/sdb1", "ext4", "mydata", on_output)
    mock_run.assert_called_once_with(
        ["mkfs.ext4", "-L", "mydata", "/dev/sdb1"],
        on_output=on_output,
    )


@patch("obg.core.formatter.run")
def test_format_ntfs_command(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    on_output = MagicMock()
    format_filesystem("/dev/sdb1", "ntfs", "win", on_output)
    mock_run.assert_called_once_with(
        ["mkfs.ntfs", "-f", "-L", "win", "/dev/sdb1"],
        on_output=on_output,
    )


@patch("obg.core.formatter.run")
def test_format_exfat_command(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    on_output = MagicMock()
    format_filesystem("/dev/sdb1", "exfat", "shared", on_output)
    mock_run.assert_called_once_with(
        ["mkfs.exfat", "-n", "shared", "/dev/sdb1"],
        on_output=on_output,
    )


@patch("obg.core.formatter.run")
def test_format_fat32_command(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    on_output = MagicMock()
    format_filesystem("/dev/sdb1", "fat32", "boot", on_output)
    mock_run.assert_called_once_with(
        ["mkfs.fat", "-F", "32", "-n", "boot", "/dev/sdb1"],
        on_output=on_output,
    )


@patch("obg.core.formatter.run")
def test_label_truncation(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    on_output = MagicMock()
    format_filesystem("/dev/sdb1", "exfat", "a" * 20, on_output)
    cmd = mock_run.call_args[0][0]
    assert cmd[2] == "a" * 11


def test_unsupported_filesystem_raises():
    on_output = MagicMock()
    with pytest.raises(ValueError, match="Unsupported filesystem"):
        format_filesystem("/dev/sdb1", "btrfs", "data", on_output)
