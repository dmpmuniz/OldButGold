from unittest.mock import patch


def test_run_elevated_returns_child_exit_code():
    from obg.__main__ import _run_elevated

    assert _run_elevated(["/bin/true"]) == 0
    assert _run_elevated(["/bin/false"]) == 1


def test_run_elevated_missing_binary_returns_127():
    from obg.__main__ import _run_elevated

    assert _run_elevated(["/no/such/binary-xyz"]) == 127


def test_launch_in_terminal_falls_back_when_terminal_dies(tmp_path):
    """os.execvp used to replace the process: when the terminal (or the
    elevation inside it) failed instantly, the app died with no fallback
    and no message. A dead terminal must move on to the next candidate."""
    from obg.__main__ import _launch_in_terminal

    dying = tmp_path / "dying-term"
    dying.write_text("#!/bin/sh\nexit 3\n")
    living = tmp_path / "living-term"
    living.write_text("#!/bin/sh\nexec sleep 30\n")
    for f in (dying, living):
        f.chmod(0o755)

    which = {"ptyxis": str(dying), "gnome-terminal": str(living)}
    with patch("obg.__main__.shutil.which", side_effect=lambda name: which.get(name)):
        assert _launch_in_terminal(["pkexec", "/x/OldButGold"]) is True


def test_launch_in_terminal_reports_failure_when_all_die(tmp_path):
    from obg.__main__ import _launch_in_terminal

    dying = tmp_path / "dying-term"
    dying.write_text("#!/bin/sh\nexit 3\n")
    dying.chmod(0o755)

    which = {"ptyxis": str(dying), "gnome-terminal": str(dying)}
    with patch("obg.__main__.shutil.which", side_effect=lambda name: which.get(name)):
        assert _launch_in_terminal(["pkexec", "/x/OldButGold"]) is False


class _FakeStdout:
    def __init__(self, tty):
        self._tty = tty

    def isatty(self):
        return self._tty


def test_no_tty_handoff_uses_sudo():
    """Double-click handoff must elevate via sudo inside the opened terminal:
    pkexec depends on a polkit authentication agent that can be broken or
    absent (reported on the author's KDE box); sudo prompts in the terminal
    itself, on every desktop."""
    import pytest
    import obg.__main__ as main_mod

    with patch("sys.argv", ["obg"]), patch("sys.stdout", _FakeStdout(False)), patch(
        "obg.__main__.os.geteuid", return_value=1000
    ), patch("obg.__main__._launch_in_terminal") as launch, patch(
        "obg.__main__.logger"
    ):
        with pytest.raises(SystemExit):
            main_mod.main()

    assert launch.call_args[0][0][0] == "sudo"


def test_tty_elevation_tries_sudo_before_pkexec():
    """From a real terminal, sudo comes first (prompts right here); pkexec
    stays as a fallback for passwordless-polkit setups."""
    import pytest
    import obg.__main__ as main_mod

    with patch("sys.argv", ["obg"]), patch("sys.stdout", _FakeStdout(True)), patch(
        "obg.__main__.os.geteuid", return_value=1000
    ), patch("obg.__main__._run_elevated", return_value=0) as run, patch(
        "obg.__main__.logger"
    ):
        with pytest.raises(SystemExit) as exc:
            main_mod.main()

    assert exc.value.code == 0
    assert run.call_args[0][0][0] == "sudo"
