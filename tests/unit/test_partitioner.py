from unittest.mock import patch, MagicMock
import pytest
from obg.core.partitioner import create_gpt, create_partition


@patch("obg.core.partitioner.run")
def test_create_gpt_calls_sgdisk(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    create_gpt("/dev/sdb")
    mock_run.assert_called_once_with(["sgdisk", "--zap-all", "/dev/sdb"])


@patch("obg.core.partitioner.run")
def test_create_partition_calls_sgdisk(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    with patch("obg.core.partitioner.time"):
        create_partition("/dev/sdb")
    mock_run.assert_any_call(["sgdisk", "-n", "1:0:0", "-t", "1:8300", "/dev/sdb"])


@patch("obg.core.partitioner.run")
def test_create_gpt_failure_raises(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stderr="error")
    with pytest.raises(RuntimeError, match="sgdisk --zap-all failed"):
        create_gpt("/dev/sdb")


@patch("obg.core.partitioner.time")
@patch("obg.core.partitioner.run")
def test_partition_returns_partition_path(mock_run, mock_time):
    mock_run.return_value = MagicMock(returncode=0)

    assert create_partition("/dev/sdb") == "/dev/sdb1"
    assert create_partition("/dev/nvme0n1") == "/dev/nvme0n1p1"
