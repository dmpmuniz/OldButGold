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

    def fake_run(cmd, on_output=None):
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
