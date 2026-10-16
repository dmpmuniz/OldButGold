#!/usr/bin/env python3
"""OldButGold — HDD Revival Toolkit for Linux."""
import os
import shutil
import subprocess
import sys
import time
from obg import __version__
from obg.ui.app import ObgApp
from obg.utils import logger


def _create_mock_image(path: str, size_gb: int = 1) -> None:
    total = size_gb * 1024 * 1024 * 1024
    block_size = 1024 * 1024
    import math
    blocks = total // block_size
    logger.info("MAIN", f"Creating mock disk image: {path} ({size_gb} GB)")
    with open(path, "wb") as f:
        f.truncate(block_size * blocks)
    logger.info("MAIN", "Mock disk image created")


def _run_elevated(cmd: list[str]) -> int:
    """Run the elevation command attached to this terminal; return its rc."""
    try:
        proc = subprocess.Popen(cmd)
    except FileNotFoundError:
        return 127
    return proc.wait()


def _launch_in_terminal(cmd: list[str]) -> bool:
    """Spawn a terminal emulator running cmd; report if it took over.

    The old os.execvp replaced this process: when the terminal failed to
    open — or the elevation inside it failed instantly — the app died with
    no fallback and no message, and the double-click launch looked broken.
    """
    candidates = [
        (name, "--") for name in ("ptyxis", "gnome-terminal", "kgx", "blackbox")
    ] + [
        (name, "-e") for name in ("konsole", "xfce4-terminal", "lxterminal", "xterm",
                                  "alacritty", "kitty", "foot", "sakura", "terminator",
                                  "mate-terminal", "tilix", "terminology", "deepin-terminal",
                                  "x-terminal-emulator")
    ]
    attempts: list[str] = []
    for name, sep in candidates:
        term = shutil.which(name)
        if not term:
            continue
        logger.info("MAIN", f"Not a TTY, launching terminal: {term}")
        try:
            proc = subprocess.Popen([term, sep] + cmd)
        except OSError as e:
            attempts.append(f"{name}: {e}")
            continue
        time.sleep(1)  # let instant failures surface before declaring success
        if proc.poll() is None:
            return True  # the window owns the session now
        attempts.append(f"{name}: exited rc={proc.poll()}")
    for line in attempts:
        logger.error("MAIN", f"terminal launch failed: {line}")
    return False


def main() -> None:
    logger.setup()
    logger.info("MAIN", "OldButGold started")

    test_mode = "--test" in sys.argv
    mock_path = None

    remaining = []
    for arg in sys.argv[1:]:
        if arg == "--mock" or arg.startswith("--mock="):
            if "=" in arg:
                mock_path = arg.split("=", 1)[1]
            else:
                mock_path = "test_disk_1gb.img"
        else:
            remaining.append(arg)

    for arg in remaining:
        if arg in ("--version", "-V"):
            print(f"OldButGold v{__version__}")
            logger.close()
            sys.exit(0)
        elif arg == "--test":
            continue
        else:
            print(f"Unknown argument: {arg}")
            print("Usage: obg [--version] [--test] [--mock[=path]]")
            logger.close()
            sys.exit(1)

    if mock_path and not os.path.exists(mock_path):
        print(f"Creating mock disk image: {mock_path}")
        _create_mock_image(mock_path)

    if test_mode:
        logger.info("MAIN", "TEST MODE — Badblocks will scan ~1% of disk")

    # Privilege escalation via pkexec
    if os.geteuid() != 0:
        is_module = sys.argv[0] in ("-m", "obg") or sys.modules["obg"].__file__.endswith("__main__.py") and "-m" in sys.argv
        if is_module:
            base_cmd = [sys.executable, "-m", "obg"]
        else:
            base_cmd = [os.path.abspath(sys.argv[0])]
        pkexec_cmd = ["pkexec"] + base_cmd + sys.argv[1:]
        sudo_cmd = ["sudo"] + base_cmd + sys.argv[1:]
        if not sys.stdout.isatty():
            # Double-click from a file manager: hand off to a terminal window.
            if not _launch_in_terminal(pkexec_cmd):
                print("No usable terminal emulator. Run from a terminal: sudo ./OldButGold")
                logger.error("MAIN", "No usable terminal emulator found")
                sys.exit(1)
            logger.close()
            sys.exit(0)
        # Real terminal: pkexec first (GUI password dialog); a failing pkexec
        # (missing, no polkit authentication agent, denied) falls back to
        # sudo, which prompts right here in the terminal.
        for elevate_cmd in (pkexec_cmd, sudo_cmd):
            logger.info("MAIN", f"Not root, elevating via {elevate_cmd[0]}")
            rc = _run_elevated(elevate_cmd)
            if rc == 0:
                logger.close()
                sys.exit(0)  # the elevated instance ran and finished
            logger.error("MAIN", f"elevation via {elevate_cmd[0]} failed (rc={rc})")
        print("Could not elevate to root. Run: sudo ./OldButGold")
        sys.exit(1)

    logger.info("MAIN", "Running with elevated privileges")

    try:
        ObgApp(test_mode=test_mode, mock_path=mock_path).run()
    except Exception as e:
        logger.error("APP", f"Unhandled exception: {e}")
        raise
    finally:
        logger.close()


if __name__ == "__main__":
    main()
