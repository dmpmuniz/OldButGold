from __future__ import annotations
import logging
import os
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime

_LOG_FILE: Path | None = None
_LOGGER = logging.getLogger("obg")
_HANDLER: logging.Handler | None = None
_ORIGINAL_EXCEPTHOOK: object | None = None


def setup() -> Path:
    global _LOG_FILE, _HANDLER, _ORIGINAL_EXCEPTHOOK
    ts = time.strftime("%Y%m%d_%H%M%S")
    log_dir = Path(os.getcwd())
    _LOG_FILE = log_dir / f"obg_{ts}.log"

    _HANDLER = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    _HANDLER.setFormatter(logging.Formatter("%(message)s"))
    _LOGGER.setLevel(logging.DEBUG)
    _LOGGER.addHandler(_HANDLER)

    _write_raw("=" * 70)
    from obg import __version__
    _write_raw(f"  OldButGold v{__version__}  -  Session Log")
    _write_raw(f"  Started:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    _write_raw(f"  Platform: {sys.platform}")
    _write_raw(f"  Python:   {sys.version.split()[0]} ({sys.version.split()[2] if len(sys.version.split()) > 2 else '?'})")
    _write_raw(f"  Args:     {' '.join(sys.argv)}")
    _write_raw(f"  PID:      {os.getpid()}")
    _write_raw(f"  User:     {os.geteuid()} (root={os.geteuid() == 0})")
    _write_raw(f"  Host:     {os.uname().nodename}")
    _write_raw(f"  OS:       {os.uname().sysname} {os.uname().release}")
    _write_raw(f"  CWD:      {os.getcwd()}")
    _write_raw("=" * 70)

    _ORIGINAL_EXCEPTHOOK = sys.excepthook
    sys.excepthook = _unhandled_exception

    return _LOG_FILE


def close() -> None:
    global _ORIGINAL_EXCEPTHOOK, _HANDLER, _LOG_FILE
    if _LOG_FILE is None:
        return
    _write_raw("=" * 70)
    _write_raw(f"  Session ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    _write_raw("=" * 70)
    if _ORIGINAL_EXCEPTHOOK:
        sys.excepthook = _ORIGINAL_EXCEPTHOOK
        _ORIGINAL_EXCEPTHOOK = None
    if _HANDLER:
        _LOGGER.removeHandler(_HANDLER)
        _HANDLER.close()
        _HANDLER = None
    _LOG_FILE = None


def _write_raw(line: str) -> None:
    if _LOG_FILE is None:
        return
    _LOGGER.debug(line)


def _fmt(level: str, tag: str, msg: str) -> str:
    ts = time.strftime("%H:%M:%S")
    return f"[{ts}] [{level:5s}] [{tag}] {msg}"


def write(level: str, tag: str, msg: str) -> None:
    _LOGGER.info(_fmt(level, tag, msg))


def info(tag: str, msg: str) -> None:
    write("INFO", tag, msg)


def warn(tag: str, msg: str) -> None:
    write("WARN", tag, msg)


def error(tag: str, msg: str) -> None:
    write("ERROR", tag, msg)
    tb = traceback.format_exc().strip()
    if tb and tb != "NoneType: None":
        _LOGGER.debug(tb)


def debug(tag: str, msg: str) -> None:
    write("DEBUG", tag, msg)


def _unhandled_exception(exc_type, exc_value, exc_tb) -> None:
    _LOGGER.debug("")
    _LOGGER.debug("!" * 70)
    _LOGGER.debug(f"  UNHANDLED EXCEPTION: {exc_type.__name__}: {exc_value}")
    _LOGGER.debug("  Traceback:")
    for line in traceback.format_tb(exc_tb):
        _LOGGER.debug(f"    {line.rstrip()}")
    _LOGGER.debug("!" * 70)
    sys.__excepthook__(exc_type, exc_value, exc_tb)
