import json
import uuid

import pytest

from obg.core import session as sess
from obg.models.disk import DiskInfo


@pytest.fixture
def tmp_session(tmp_path, monkeypatch):
    monkeypatch.setattr(sess, "_SESSION_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def disk():
    return DiskInfo(
        device="/dev/sdb", model="TestDrive", serial="SN12345", firmware="FW1.0",
        capacity_bytes=1000000000, capacity_human="1 GB",
        interface="usb", transport="usb-uas", logical_sector=512, physical_sector=4096,
        min_io=4096, optimal_io=0, alignment_offset=0, rpm=5400,
        smart_supported=True, uas_enabled=True,
        current_fs=None, partition_table=None,
        is_mounted=False, is_boot_disk=False,
        temperature=None, power_on_hours=None, is_supported=True,
    )


def test_create_session_creates_file(tmp_session, disk):
    sess.create_session(disk)
    assert (tmp_session / f"{disk.serial}.json").exists()


def test_create_session_returns_uuid(tmp_session, disk):
    sid = sess.create_session(disk)
    uuid.UUID(sid)


def test_find_session_match(tmp_session, disk):
    sess.create_session(disk)
    result = sess.find_session(disk)
    assert result is not None
    assert result["state"] == "in_progress"
    assert result["serial"] == disk.serial


def test_find_session_no_file(tmp_session, disk):
    assert sess.find_session(disk) is None


def test_find_session_fingerprint_mismatch(tmp_session, disk):
    sess.create_session(disk)
    wrong = DiskInfo(**{**disk.__dict__, "model": "WrongDrive"})
    assert sess.find_session(wrong) is None


def test_find_session_wrong_state(tmp_session, disk):
    path = tmp_session / f"{disk.serial}.json"
    sess.create_session(disk)
    data = json.loads(path.read_text())
    data["state"] = "completed"
    path.write_text(json.dumps(data))
    assert sess.find_session(disk) is None


def test_update_checkpoint(tmp_session, disk):
    sess.create_session(disk)
    sess.update_checkpoint(disk, 42.5)
    data = json.loads((tmp_session / f"{disk.serial}.json").read_text())
    assert data["badblocks_offset"] == 42.5


def test_complete_session_deletes_file(tmp_session, disk):
    sess.create_session(disk)
    path = tmp_session / f"{disk.serial}.json"
    assert path.exists()
    sess.complete_session(disk)
    assert not path.exists()

