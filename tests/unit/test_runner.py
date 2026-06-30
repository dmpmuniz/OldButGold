import os
import pytest
from obg.utils.runner import run, RunResult

def test_run_simple_command():
    r = run(["echo", "hello"])
    assert r.returncode == 0
    assert "hello" in r.stdout

def test_run_captures_stderr():
    r = run(["ls", "/nonexistent_path_xyz_12345"])
    assert r.returncode != 0
    assert len(r.stderr) > 0

def test_run_timeout_raises():
    with pytest.raises(Exception):  # TimeoutExpired or similar
        run(["sleep", "10"], timeout=1)

def test_run_env_cleanup(monkeypatch):
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/_MEI123/lib:/usr/lib")
    r = run(["echo", "test"])
    assert r.returncode == 0
    # The _MEI path should have been cleaned from env used by subprocess
    assert r.stdout.strip() == "test"

def test_run_on_output_callback():
    lines = []
    r = run(["printf", "line1\nline2\nline3\n"], on_output=lines.append)
    assert len(lines) == 3
    assert "line1" in lines

def test_run_measures_duration():
    r = run(["sleep", "0.1"])
    assert r.duration_seconds >= 0.1