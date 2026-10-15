from unittest.mock import patch

import pytest

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
    assert _is_scan_operation("Pass 2/2 — verifying 0xaa") is True
    assert _is_scan_operation("SMART Short Self-Test") is False
    assert _is_scan_operation("") is False


def test_parse_hms_variants():
    from obg.ui.app import _parse_hms

    assert _parse_hms("0:05:00") == 300
    assert _parse_hms("12:34") == 754
    assert _parse_hms("42") == 42


def test_eta_is_average_over_remaining_passes():
    """ETA must come from badblocks' own elapsed (average rate), not from the
    instantaneous rate of the last two progress lines — that underestimated
    badly on zoned HDDs (1h promised, 3h real)."""
    screen = ExecutionScreen.__new__(ExecutionScreen)
    screen.disk = _make_disk()
    screen._total_passes = 2
    screen._pass_number = 1
    screen._progress = 50.0
    screen._pass_elapsed_s = 600.0
    screen._scan_bytes = 1_000_000_000
    screen._eta = ""
    screen._speed = 0.0
    screen._recompute_eta()
    # 600s for 50% → 600s left on this pass; one more pass estimated at the
    # full-pass rate (1200s) → 1800s total = 30m.
    assert screen._eta == "30m 00s"
    # Average speed over the scanned range, not the instantaneous window.
    assert screen._speed == pytest.approx(50.0 / 600.0 * 1_000_000_000 / 1_000_000)


def test_eta_last_pass_excludes_remaining_passes():
    screen = ExecutionScreen.__new__(ExecutionScreen)
    screen.disk = _make_disk()
    screen._total_passes = 2
    screen._pass_number = 2
    screen._progress = 50.0
    screen._pass_elapsed_s = 600.0
    screen._scan_bytes = 1_000_000_000
    screen._eta = ""
    screen._speed = 0.0
    screen._recompute_eta()
    assert screen._eta == "10m 00s"


def test_recompute_eta_skipped_without_progress():
    screen = ExecutionScreen.__new__(ExecutionScreen)
    screen.disk = _make_disk()
    screen._total_passes = 2
    screen._pass_number = 1
    screen._progress = 0.0
    screen._pass_elapsed_s = 0.0
    screen._scan_bytes = 1_000_000_000
    screen._eta = "stale"
    screen._speed = 5.0
    screen._recompute_eta()
    # Nothing to compute from — earlier values must survive untouched.
    assert screen._eta == "stale"
    assert screen._speed == 5.0


def test_start_pass_increments_counter_and_resets_per_pass_metrics():
    screen = ExecutionScreen.__new__(ExecutionScreen)
    screen._total_passes = 2
    screen._pass_number = 1
    screen._pattern = "0xaa"
    screen._eta = "30m 00s"
    screen._speed = 100.0
    screen._start_pass(write=False)
    assert screen._pass_number == 2
    assert screen._eta == ""
    assert screen._speed == 0.0
    assert "verifying" in screen._operation.lower()
    assert "2/2" in screen._operation


def test_start_pass_write_labels_pattern_and_pass():
    screen = ExecutionScreen.__new__(ExecutionScreen)
    screen._total_passes = 8
    screen._pass_number = 0
    screen._pattern = "0x55"
    screen._eta = ""
    screen._speed = 0.0
    screen._start_pass(write=True)
    assert screen._pass_number == 1
    assert "writing 0x55" in screen._operation.lower()
    assert "1/8" in screen._operation


def test_session_pct_is_percent_of_disk():
    """badblocks_offset is stored as a percent (0-100), not a block count."""
    from obg.ui.app import MainScreen

    disk = _make_disk()
    assert MainScreen._session_pct(disk, {"badblocks_offset": 50.0}) == 50
    assert MainScreen._session_pct(disk, {"badblocks_offset": 3.0}) == 3


def test_session_pct_clamps_above_99():
    from obg.ui.app import MainScreen

    disk = _make_disk()
    assert MainScreen._session_pct(disk, {"badblocks_offset": 100.0}) == 99


def test_profile_descriptions_match_actual_profiles():
    """The screen must describe what actually runs — the old text claimed
    'Two destructive patterns (0xaa / 0x55)' for Recommended while the
    scanner runs a single 0xaa pattern."""
    from obg.ui.app import ConfigScreen

    recommended = ConfigScreen.PROFILE_DESCRIPTIONS["recommended"]
    assert "One destructive pattern" in recommended
    assert "2 passes" in recommended
    extended = ConfigScreen.PROFILE_DESCRIPTIONS["extended"]
    assert "8 passes" in extended


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

            assert "writing" in screen._operation.lower()
            assert "1/2" in screen._operation
            assert screen._pattern == "0xaa"
            assert screen._progress == 10.0

            # Read pass — progress resets to 0, operation should switch to verifying
            screen._append("Reading and comparing:   0.00% done, 0:01:40 elapsed. (0/0/0 errors)")
            await pilot.pause()

            assert "verifying" in screen._operation.lower(), f"Expected 'verifying' in operation, got: {screen._operation}"
            assert "2/2" in screen._operation
            assert screen._pattern == "0xaa"
            assert screen._progress == 0.0
            # Per-pass ETA and speed reset when the new pass starts
            assert screen._eta == ""
            assert screen._speed == 0.0

            screen._append("Reading and comparing:   50.00% done, 0:02:10 elapsed. (0/0/0 errors)")
            await pilot.pause()

            assert "verifying" in screen._operation.lower(), f"Expected 'verifying' in operation, got: {screen._operation}"
            assert screen._pattern == "0xaa"
            assert screen._progress == 50.0
            # Honest ETA: 130s for 50% → 130s remaining, last pass → "2m 10s"
            assert screen._eta == "2m 10s"


async def test_execution_screen_tracks_scan_range_and_passes():
    """Speed must be computed over the scanned range, not the whole disk, and
    pass labels must show what the drive is actually doing."""
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

            # Scanner announces a 1000-block test window (of 100000): the
            # speed denominator must shrink to the window, not the 1 TB disk.
            screen._append("TEST MODE: destructive test of 1000 of 100000 blocks (~1%)")
            await pilot.pause()
            assert screen._scan_bytes == 1000 * 4096

            screen._append("Testing with pattern 0xaa:   10.00% done, 0:00:10 elapsed. (0/0/0 errors)")
            await pilot.pause()
            assert screen._pass_number == 1
            assert "writing" in screen._operation.lower()

            screen._append("Reading and comparing:   50.00% done, 0:00:40 elapsed. (0/0/0 errors)")
            await pilot.pause()
            assert screen._pass_number == 2
            assert "verifying" in screen._operation.lower()
            # Speed over the scanned window: 50%/40s * 4096000 bytes ≈ 5.12 MB/s
            assert screen._speed == pytest.approx(50.0 / 40.0 * 1000 * 4096 / 1_000_000)


async def test_output_log_autoscrolls_to_end():
    """Raw output panel must keep scrolling to the bottom as lines arrive."""
    from textual.containers import VerticalScroll

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

            log = screen.query_one("#output-log", VerticalScroll)
            for i in range(300):
                screen._append(f"raw output line {i:03d} " + "x" * 60)
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()

            assert log.max_scroll_y > 0, "log content should overflow the panel"
            assert log.scroll_offset.y >= log.max_scroll_y, (
                f"autoscroll stuck: offset={log.scroll_offset.y}, max={log.max_scroll_y}"
            )


async def test_config_screen_prefills_label_from_disk_model():
    """Label input must suggest the CURRENT disk's brand, never a stale saved label."""
    from textual.widgets import Input

    disk = DiskInfo(
        device="/dev/sda", model="TOSHIBA MQ01ABD050", serial="SN", firmware="FW1",
        capacity_bytes=1000000000000, capacity_human="1.0 TB",
        interface="sata", transport="sata",
        logical_sector=512, physical_sector=4096,
        smart_supported=True, uas_enabled=False,
        current_fs=None, partition_table=None,
        is_mounted=False, is_boot_disk=False,
        temperature=None, power_on_hours=None,
        is_supported=True, rotational=True,
    )

    app = ObgApp(test_mode=True, mock_path="/tmp/test_disk_large.img")
    async with app.run_test() as pilot:
        from obg.ui.app import ConfigScreen
        from textual.widgets import Input

        screen = ConfigScreen(disk)
        app.push_screen(screen)
        await pilot.pause()
        await pilot.pause()
        label_input = screen.query_one("#label-input", Input)
        assert label_input.value == "TOSHIBA"