#!/usr/bin/env python3
"""OldButGold — HDD Revival Toolkit for Linux."""
import os
import sys
import shutil
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
            python = sys.executable
            base_cmd = [python, "-m", "obg"]
            pkexec_cmd = ["pkexec"] + base_cmd + sys.argv[1:]
        else:
            binary = os.path.abspath(sys.argv[0])
            pkexec_cmd = ["pkexec", binary] + sys.argv[1:]
        if not sys.stdout.isatty():
            for term_cmd in ("ptyxis", "gnome-terminal", "kgx", "blackbox"):
                term = shutil.which(term_cmd)
                if term:
                    logger.info("MAIN", f"Not a TTY, launching terminal: {term}")
                    try:
                        os.execvp(term, [term, "--"] + pkexec_cmd)
                    except OSError:
                        continue
            for term_cmd in ("konsole", "xfce4-terminal", "lxterminal", "xterm", "alacritty", "kitty", "foot", "sakura", "terminator", "mate-terminal", "tilix", "terminology", "deepin-terminal", "x-terminal-emulator"):
                term = shutil.which(term_cmd)
                if term:
                    logger.info("MAIN", f"Not a TTY, launching terminal: {term}")
                    try:
                        os.execvp(term, [term, "-e"] + pkexec_cmd)
                    except OSError:
                        continue
            logger.error("MAIN", "No terminal emulator found. Run from a terminal: pkexec ./OldButGold")
            sys.exit(1)
        logger.info("MAIN", "Not root, re-executing via pkexec")
        os.execvp("pkexec", pkexec_cmd)

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
