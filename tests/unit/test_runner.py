import os
import pytest
from obg.utils.runner import run, RunResult, ProcessAborted, ProcessStalled

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


def test_run_stop_check_aborts_streaming():
    import time as _t
    start = _t.monotonic()
    with pytest.raises(ProcessAborted):
        run(
            ["bash", "-c", "while true; do echo tick; sleep 0.2; done"],
            on_output=lambda _: None,
            stop_check=lambda: _t.monotonic() - start > 1,
            idle_timeout=60,
        )


def test_run_idle_timeout_aborts_streaming():
    with pytest.raises(ProcessStalled):
        run(
            ["sleep", "30"],
            on_output=lambda _: None,
            stop_check=lambda: False,
            idle_timeout=1,
        )


def test_run_on_output_still_streams_lines():
    lines = []
    r = run(
        ["printf", "a\nb\nc\n"],
        on_output=lines.append,
        stop_check=lambda: False,
        idle_timeout=10,
    )
    assert lines == ["a", "b", "c"]