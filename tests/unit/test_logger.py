import os
import sys
import tempfile
from pathlib import Path


def test_logger_creates_file_in_cwd():
    from obg.utils import logger
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            log_path = logger.setup()
            assert log_path.parent == Path(tmp)
            assert log_path.name.startswith("obg_")
            assert log_path.suffix == ".log"
            assert log_path.exists()
        finally:
            os.chdir(original_cwd)
        logger.close()


def test_logger_writes_entries():
    from obg.utils import logger
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            log_path = logger.setup()
            logger.info("TEST", "hello world")
            logger.warn("TEST", "warning")
            content = log_path.read_text()
            assert "[INFO ] [TEST] hello world" in content
            assert "[WARN ] [TEST] warning" in content
        finally:
            os.chdir(original_cwd)
        logger.close()
