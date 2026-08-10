from unittest.mock import patch

from obg.ui.app import BB_LINE_RE, ExecutionScreen, ObgApp, _is_scan_operation
from obg.models.disk import DiskInfo


def _make_disk():
    return DiskInfo(
        device="/dev/sdb", model="Test HDD", serial="SN123", firmware="FW1",
        capacity_bytes=1000000000000, capacity_human="1.0 TB",
        interface="sata", transport="usb-uas",
        logical_sector=512, physical_sector=4096,
        smart_supported=True, uas_enabled=True,
        current_fs=None, partition_table=None,
        is_mounted=False, is_boot_disk=False,
        temperature=None, power_on_hours=None,
        is_supported=True, rotational=True,
    )


def _parse(line):
    return BB_LINE_RE.match(line)


def test_bb_regex_matches_write_pass():
    line = "Testing with pattern 0xaa:   50.00% done, 0:05:00 elapsed. (0/0/0 errors)"
    m = _parse(line)
    assert m is not None
    pattern, pct, elapsed, r, w, c = m.groups()
    assert pattern == "0xaa"
    assert pct == "50.00"
    assert r == "0" and w == "0" and c == "0"


def test_bb_regex_matches_read_pass():
    line = "Reading and comparing:   50.00% done, 0:05:00 elapsed. (0/0/0 errors)"
    m = _parse(line)
    assert m is not None
    pattern, pct, elapsed, r, w, c = m.groups()
    assert pattern is None
    assert pct == "50.00"
    assert r == "0" and w == "0" and c == "0"


def test_bb_regex_matches_errors_without_closing_paren():
    line = "Testing with pattern 0xaa:   50.00% done, 0:05:00 elapsed. (1/2/3 errors"
    m = _parse(line)
    assert m is not None
    pattern, pct, elapsed, r, w, c = m.groups()
    assert pattern == "0xaa"
    assert r == "1" and w == "2" and c == "3"


def test_bb_regex_matches_read_pass_no_errors():
    line = "Reading and comparing:   75.00% done, 0:10:00 elapsed."
    m = _parse(line)
    assert m is not None
    pattern, pct, elapsed, r, w, c = m.groups()
    assert pattern is None
    assert pct == "75.00"


def test_bb_regex_does_not_match_other_lines():
    for line in [
        "badblocks: Setting up in the badblocks file",
        "Pass completed, 0 bad blocks found.",
        "SMART test: 10% complete",
        "Reached end of file while reading",
    ]:
        assert _parse(line) is None, f"regex matched unrelated line: {line!r}"


def test_is_scan_operation():
    assert _is_scan_operation("Writing 0xaa") is True
    assert _is_scan_operation("Reading 0xaa") is True
    assert _is_scan_operation("badblocks (pattern 0xaa)") is True
    assert _is_scan_operation("SMART Short Self-Test") is False
    assert _is_scan_operation("") is False


def test_estimate_eta_resets_on_progress_backwards():
    screen = ExecutionScreen.__new__(ExecutionScreen)
    screen._last_pct = 95.0
    screen._last_pct_time = 111.0
    screen._progress = 0.0
    screen._eta = "1h 30m 00s"
    screen._speed = 100.0
    screen.disk = _make_disk()

    with patch("obg.ui.app.time.monotonic", return_value=120.0):
        screen._estimate_eta()

    assert screen._eta == ""
    assert screen._speed == 0.0
    assert screen._last_pct == 0.0
    assert screen._last_pct_time == 120.0


def test_estimate_eta_recomputes_after_reset():
    screen = ExecutionScreen.__new__(ExecutionScreen)
    screen._last_pct = 0.0
    screen._last_pct_time = 100.0
    screen._progress = 50.0
    screen._eta = ""
    screen._speed = 0.0
    screen.disk = _make_disk()

    with patch("obg.ui.app.time.monotonic", return_value=102.0):
        screen._estimate_eta()

    assert screen._eta != ""
    assert screen._speed > 0


def test_rotational_hdd_is_supported():
    disk = DiskInfo(
        device="/dev/sdb", model="WD HDD", serial="SN1", firmware="FW1",
        capacity_bytes=1000000, capacity_human="1 MB",
        interface="sata", transport="sata",
        logical_sector=512, physical_sector=512,
        smart_supported=True, uas_enabled=False,
        current_fs=None, partition_table=None,
        is_mounted=False, is_boot_disk=False,
        temperature=None, power_on_hours=None,
        is_supported=True, rotational=True,
    )
    assert disk.rotational is True
    assert disk.is_supported is True


def test_non_rotational_is_disabled():
    disk = DiskInfo(
        device="/dev/nvme0n1", model="NVMe SSD", serial="SN2", firmware="FW1",
        capacity_bytes=1000000, capacity_human="1 MB",
        interface="nvme", transport="nvme",
        logical_sector=512, physical_sector=4096,
        smart_supported=True, uas_enabled=False,
        current_fs=None, partition_table=None,
        is_mounted=False, is_boot_disk=False,
        temperature=None, power_on_hours=None,
        is_supported=False, rotational=False,
    )
    assert disk.rotational is False
    assert disk.is_supported is False


def test_mock_disk_default_rotational():
    disk = DiskInfo(
        device="/tmp/mock.img", model="Mock", serial="MOCK", firmware="1.0",
        capacity_bytes=1000000, capacity_human="1 MB",
        interface="virtual", transport="mock",
        logical_sector=512, physical_sector=4096,
        smart_supported=False, uas_enabled=False,
        current_fs=None, partition_table=None,
        is_mounted=False, is_boot_disk=False,
        temperature=None, power_on_hours=None,
        is_supported=True, is_mock=True,
    )
    assert disk.rotational is True


async def test_execution_screen_badblocks_write_then_read():
    """Verify operation text switches from Writing to Reading during badblocks."""
    disk = DiskInfo(
        device="/tmp/mock.img", model="Mock HDD", serial="MOCK", firmware="1.0",
        capacity_bytes=1000000000000, capacity_human="1.0 TB",
        interface="sata", transport="sata",
        logical_sector=512, physical_sector=4096,
        smart_supported=False, uas_enabled=False,
        current_fs=None, partition_table=None,
        is_mounted=False, is_boot_disk=False,
        temperature=None, power_on_hours=None,
        is_supported=True, rotational=True,
    )
    config = {"profile": "recommended", "filesystem": "ext4", "label": ""}

    with patch("obg.ui.app.run_pipeline") as mock_pipeline:
        mock_pipeline.return_value = None
        app = ObgApp(test_mode=True, mock_path="/tmp/test_disk_large.img")
        async with app.run_test() as pilot:
            screen = ExecutionScreen(disk, config)
            app.push_screen(screen)
            await pilot.pause()
            await pilot.pause()

            # Write pass
            screen._append("Checking for bad blocks in read-write mode")
            await pilot.pause()
            screen._append("Testing with pattern 0xaa:   10.00% done, 0:00:10 elapsed. (0/0/0 errors)")
            await pilot.pause()

            assert "Writing" in screen._operation
            assert screen._pattern == "0xaa"
            assert screen._progress == 10.0

            # Read pass — progress resets to 0, operation should switch to Reading
            screen._append("Reading and comparing:   0.00% done, 0:01:40 elapsed. (0/0/0 errors)")
            await pilot.pause()

            assert "Reading" in screen._operation, f"Expected 'Reading' in operation, got: {screen._operation}"
            assert screen._pattern == "0xaa"
            assert screen._progress == 0.0
            # ETA and speed are cleared right after the progress reset
            assert screen._eta == ""
            assert screen._speed == 0.0

            screen._append("Reading and comparing:   50.00% done, 0:02:10 elapsed. (0/0/0 errors)")
            await pilot.pause()

            assert "Reading" in screen._operation, f"Expected 'Reading' in operation, got: {screen._operation}"
            assert screen._pattern == "0xaa"
            assert screen._progress == 50.0