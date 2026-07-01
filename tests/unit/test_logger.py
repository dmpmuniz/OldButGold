import os
import sys
import tempfile
from pathlib import Path


def test_logger_creates_file_in_cache_dir():
    from obg.utils import logger
    cache_home = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
    log_path = logger.setup()
    assert log_path.parent == Path(cache_home) / "obg"
    assert log_path.name.startswith("obg_")
    assert log_path.suffix == ".log"
    assert log_path.exists()
    logger.close()


def test_logger_writes_entries():
    from obg.utils import logger
    log_path = logger.setup()
    try:
        logger.info("TEST", "hello world")
        logger.warn("TEST", "warning")
        content = log_path.read_text()
        assert "[INFO ] [TEST] hello world" in content
        assert "[WARN ] [TEST] warning" in content
    finally:
        logger.close()
