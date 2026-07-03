from __future__ import annotations
import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from obg.utils import logger


@dataclass
class RunResult:
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float


def _bundle_dir() -> Path | None:
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return None


def _resolve_tool(name: str) -> str:
    bundle = _bundle_dir()
    if bundle:
        tp = bundle / "tools" / name
        if tp.exists() and os.access(tp, os.X_OK):
            return str(tp)
        logger.warn("BUNDLE", f"Tool '{name}' not in bundle, falling back to host")
    which = shutil.which(name)
    if which:
        return which
    raise FileNotFoundError(f"Required tool not found: {name}")


def _build_env() -> dict[str, str]:
    env = os.environ.copy()
    bundle = _bundle_dir()
    if bundle and (bundle / "lib").exists():
        lib_path = str(bundle / "lib")
        existing = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = f"{lib_path}:{existing}" if existing else lib_path
    # Clean _MEI paths from env
    ld = env.get("LD_LIBRARY_PATH", "")
    if ld:
        parts = [p for p in ld.split(":") if "_MEI" not in p]
        env["LD_LIBRARY_PATH"] = ":".join(parts)
    return env


def run(
    command: list[str],
    timeout: int | None = None,
    on_output: Callable[[str], None] | None = None,
    input_data: str | None = None,
) -> RunResult:
    resolved = [_resolve_tool(command[0])] + command[1:]
    cmd_str = " ".join(resolved) if len(" ".join(resolved)) < 200 else " ".join(resolved[:3]) + " ..."
    logger.debug("CMD", f"run: {cmd_str}")
    env = _build_env()
    start = time.monotonic()

    if on_output:
        proc = subprocess.Popen(
            resolved,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE if input_data else None,
            env=env,
            preexec_fn=os.setsid,
            text=True,
        )
        stdout_lines = []
        stderr_lines = []

        def _reader(stream, lines):
            assert stream is not None
            buf = ""
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    if buf:
                        line = buf.rstrip("\r\n")
                        if line:
                            lines.append(line)
                            on_output(line)
                    break
                buf += chunk
                while "\n" in buf or "\r" in buf:
                    nidx = buf.find("\n")
                    ridx = buf.find("\r")
                    if nidx >= 0 and (ridx < 0 or nidx <= ridx):
                        idx = nidx
                    elif ridx >= 0:
                        idx = ridx
                    else:
                        break
                    line = buf[:idx].rstrip("\r\n")
                    buf = buf[idx + 1:]
                    if line:
                        lines.append(line)
                        on_output(line)

        t_out = threading.Thread(target=_reader, args=(proc.stdout, stdout_lines), daemon=True)
        t_err = threading.Thread(target=_reader, args=(proc.stderr, stderr_lines), daemon=True)
        t_out.start()
        t_err.start()

        try:
            t_out.join(timeout=timeout)
            t_err.join(timeout=timeout)
            proc.wait(timeout=timeout if timeout else None)
        except (subprocess.TimeoutExpired, Exception):
            os.killpg(os.getpgid(proc.pid), 15)
            proc.wait()
            raise
        duration = time.monotonic() - start
        logger.debug("CMD", f"  -> rc={proc.returncode} duration={duration:.1f}s")
        return RunResult(
            returncode=proc.returncode or 0,
            stdout="\n".join(stdout_lines),
            stderr="\n".join(stderr_lines),
            duration_seconds=duration,
        )
    else:
        result = subprocess.run(
            resolved,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            preexec_fn=os.setsid,
            stdin=subprocess.PIPE if input_data else None,
            input=input_data,
        )
        duration = time.monotonic() - start
        logger.debug("CMD", f"  -> rc={result.returncode} duration={duration:.1f}s")
        return RunResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_seconds=duration,
        )
