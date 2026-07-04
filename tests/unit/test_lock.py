import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
from obg.core import lock as lock_mod
from obg.models.disk import DiskInfo


@pytest.fixture
def disk():
    return DiskInfo(
        device="/dev/sdb", model="Test", serial="SN123", firmware="FW1",
        capacity_bytes=1000000, capacity_human="1 MB",
        interface="usb", transport="usb-uas", logical_sector=512, physical_sector=4096,
        min_io=4096, optimal_io=0, alignment_offset=0, rpm=5400,
        smart_supported=True, uas_enabled=True,
        current_fs=None, partition_table=None,
        is_mounted=False, is_boot_disk=False,
        temperature=None, power_on_hours=None, is_supported=True,
    )


def test_acquire_lock_success(disk):
    with tempfile.TemporaryDirectory() as tmp:
        lock_mod._LOCK_DIR = Path(tmp) / "locks"
        assert lock_mod.acquire_lock(disk.device) is True
        lock_mod.release_lock(disk.device)


def test_acquire_lock_fails_when_held(disk):
    with tempfile.TemporaryDirectory() as tmp:
        lock_mod._LOCK_DIR = Path(tmp) / "locks"
        assert lock_mod.acquire_lock(disk.device) is True
        assert lock_mod.acquire_lock(disk.device) is False
        lock_mod.release_lock(disk.device)


def test_release_lock(disk):
    with tempfile.TemporaryDirectory() as tmp:
        lock_mod._LOCK_DIR = Path(tmp) / "locks"
        lock_mod.acquire_lock(disk.device)
        lock_mod.release_lock(disk.device)
        assert lock_mod.acquire_lock(disk.device) is True
        lock_mod.release_lock(disk.device)


def test_release_lock_noop_when_not_held(disk):
    with tempfile.TemporaryDirectory() as tmp:
        lock_mod._LOCK_DIR = Path(tmp) / "locks"
        lock_mod.release_lock(disk.device)


def test_acquire_lock_creates_lock_dir(disk):
    with tempfile.TemporaryDirectory() as tmp:
        lock_dir = Path(tmp) / "new-locks"
        lock_mod._LOCK_DIR = lock_dir
        assert lock_mod.acquire_lock(disk.device) is True
        assert lock_dir.exists()
        lock_mod.release_lock(disk.device)
