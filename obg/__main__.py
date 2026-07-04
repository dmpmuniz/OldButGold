#!/usr/bin/env python3
"""OldButGold — HDD Revival Toolkit for Linux."""
import os
import sys


def main() -> None:
    from obg import __version__
    from obg.ui.app import ObgApp
    from obg.utils import logger
    logger.setup()
    logger.info("MAIN", "OldButGold started")

    test_mode = "--test" in sys.argv

    for arg in sys.argv[1:]:
        if arg in ("--version", "-V"):
            print(f"OldButGold v{__version__}")
            logger.close()
            sys.exit(0)
        elif arg != "--test":
            print(f"Unknown argument: {arg}")
            print("Usage: obg [--version] [--test]")
            logger.close()
            sys.exit(1)

    if test_mode:
        logger.info("MAIN", "TEST MODE — Badblocks will scan ~1% of disk")

    # Privilege escalation via pkexec
    if os.geteuid() != 0:
        binary = os.path.abspath(sys.argv[0])
        if not sys.stdout.isatty():
            import shutil
            for term_cmd in ("ptyxis", "gnome-terminal"):
                term = shutil.which(term_cmd)
                if term:
                    logger.info("MAIN", f"Not a TTY, launching terminal: {term}")
                    cmd = "pkexec " + binary + "".join(f" {a}" for a in sys.argv[1:])
                    os.execvp(term, [term, "-x", cmd])
            for term_cmd in ("kgx", "konsole", "xfce4-terminal", "lxterminal", "xterm", "x-terminal-emulator"):
                term = shutil.which(term_cmd)
                if term:
                    logger.info("MAIN", f"Not a TTY, launching terminal: {term}")
                    os.execvp(term, [term, "-e", "pkexec", binary] + sys.argv[1:])
            logger.error("MAIN", "No terminal emulator found. Run from a terminal: pkexec ./OldButGold")
            sys.exit(1)
        logger.info("MAIN", "Not root, re-executing via pkexec")
        os.execvp("pkexec", ["pkexec", binary] + sys.argv[1:])

    logger.info("MAIN", "Running with elevated privileges")

    # Resize terminal to 100×30 for consistent layout
    sys.stdout.write("\x1b[8;30;100t")
    sys.stdout.flush()

    try:
        ObgApp(test_mode=test_mode).run()
    except Exception as e:
        logger.error("APP", f"Unhandled exception: {e}")
        raise
    finally:
        logger.close()


if __name__ == "__main__":
    main()
