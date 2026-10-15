from unittest.mock import patch, MagicMock, call
import pytest
from obg.core.scanner import run_badblocks


@patch("obg.core.scanner.run")
def test_badblocks_parses_bad_count(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="", stderr="0, 5 bad blocks found\n"
    )
    result = run_badblocks("/dev/sdb", MagicMock())
    assert result == 5


@patch("obg.core.scanner.run")
def test_badblocks_zero_bad_blocks(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="", stderr="0, 0 bad blocks found\n"
    )
    result = run_badblocks("/dev/sdb", MagicMock())
    assert result == 0


@patch("obg.core.scanner.run")
def test_checkpoint_callback_fired(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="", stderr="0, 0 bad blocks found\n"
    )
    on_output = MagicMock()
    on_checkpoint = MagicMock()

    def fake_run(cmd, on_output=None, **kwargs):
        if on_output:
            on_output("  0.00%")
            on_output("  10.00%")
            on_output("  20.00%")
            on_output("100.00% done")
        return MagicMock(returncode=0, stdout="", stderr="0, 0 bad blocks found\n")

    mock_run.side_effect = fake_run
    run_badblocks("/dev/sdb", on_output, on_checkpoint=on_checkpoint)

    assert on_checkpoint.call_count >= 3
    calls = [c[0][0] for c in on_checkpoint.call_args_list]
    assert 10.0 in calls
    assert 20.0 in calls


@patch("obg.core.scanner.run")
def test_extended_profile_command(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="", stderr="0, 0 bad blocks found\n"
    )
    run_badblocks("/dev/sdb", MagicMock(), profile="extended")
    cmd = mock_run.call_args[0][0]
    assert cmd == ["badblocks", "-w", "-s", "-v", "/dev/sdb"]


@patch("obg.core.scanner.run")
def test_recommended_profile_command_single_pattern(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="", stderr="0, 0 bad blocks found\n"
    )
    run_badblocks("/dev/sdb", MagicMock(), profile="recommended")
    cmd = mock_run.call_args[0][0]
    # 1 write pass + 1 read pass of a single pattern (0xaa) = 2 passes total.
    assert cmd == ["badblocks", "-w", "-s", "-v", "-b", "4096", "-t", "0xaa", "/dev/sdb"]
    assert "-t" in cmd
    assert cmd.count("-t") == 1


@patch("obg.core.scanner._get_block_count", return_value=1000)
@patch("obg.core.scanner.run")
def test_resume_command_uses_absolute_positions(mock_run, mock_count):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="", stderr="0, 0 bad blocks found\n"
    )
    run_badblocks("/dev/sdb", MagicMock(), resume_offset=50)
    cmd = mock_run.call_args[0][0]
    # Resume at 50%: start = 50% - 10% margin = block 400. last_block must be
    # the absolute END of the disk (block 999), not a block count (old bug: 600,
    # which silently skipped the last 40% of the disk).
    assert cmd[-2:] == ["999", "400"]


@patch("obg.core.scanner._get_block_count", return_value=1000)
@patch("obg.core.scanner.run")
def test_resume_checkpoint_is_absolute_disk_position(mock_run, mock_count):
    on_checkpoint = MagicMock()

    def fake_run(cmd, on_output=None, **kwargs):
        if on_output:
            on_output("Reading and comparing:  50.00% done, 0:05:00 elapsed.")
        return MagicMock(returncode=0, stdout="", stderr="0, 0 bad blocks found\n")

    mock_run.side_effect = fake_run
    run_badblocks("/dev/sdb", MagicMock(), on_checkpoint=on_checkpoint, resume_offset=50)
    # Resumed range = blocks 400..999 = 60% of the disk. badblocks reports 50%
    # OF THE RANGE; the checkpoint must store the absolute disk position:
    # 40% + 50% * 60% = 70% (old bug: stored 50, corrupting saved progress).
    assert on_checkpoint.call_args[0][0] == pytest.approx(70.0)


@patch("obg.core.scanner._get_block_count", return_value=100000)
@patch("obg.core.scanner.run")
def test_test_mode_resume_scans_window_from_offset(mock_run, mock_count):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="", stderr="0, 0 bad blocks found\n"
    )
    run_badblocks("/dev/sdb", MagicMock(), test_mode=True, resume_offset=50)
    cmd = mock_run.call_args[0][0]
    # Test mode scans a ~1% window; resumed, the window must START at the
    # resume point (block 40000 of 100000), not at zero.
    assert cmd[-2:] == ["40999", "40000"]


@patch("obg.core.scanner._get_block_count", return_value=100000)
@patch("obg.core.scanner.run")
def test_test_mode_checkpoint_is_absolute_disk_pct(mock_run, mock_count):
    on_checkpoint = MagicMock()

    def fake_run(cmd, on_output=None, **kwargs):
        if on_output:
            on_output("  50.00% done, 0:00:30 elapsed.")
        return MagicMock(returncode=0, stdout="", stderr="0, 0 bad blocks found\n")

    mock_run.side_effect = fake_run
    run_badblocks("/dev/sdb", MagicMock(), on_checkpoint=on_checkpoint, test_mode=True)
    # Fresh test-mode range = first 1000 of 100000 blocks = 1% of the disk:
    # 50% of that range = 0.5% absolute, so sessions no longer claim ~100%.
    assert on_checkpoint.call_args[0][0] == pytest.approx(0.5)
