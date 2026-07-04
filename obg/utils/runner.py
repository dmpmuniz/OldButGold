from __future__ import annotations
import os
import shutil
import subprocess
import sys
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


def _tool_dir() -> Path | None:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return None


def _resolve_tool(name: str) -> str:
    exe_dir = _tool_dir()
    if exe_dir:
        tp = exe_dir / "tools" / name
        if tp.exists() and os.access(tp, os.X_OK):
            return str(tp)
        raise FileNotFoundError(
            f"Required tool '{name}' not found in application bundle. "
            f"OldButGold must be executed from a complete distribution."
        )
    which = shutil.which(name)
    if which:
        return which
    raise FileNotFoundError(f"Required tool not found: {name}")


def _build_env() -> dict[str, str]:
    env = os.environ.copy()
    exe_dir = _tool_dir()
    if exe_dir and (exe_dir / "lib").exists():
        lib_path = str(exe_dir / "lib")
        existing = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = f"{lib_path}:{existing}" if existing else lib_path
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
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE if input_data else None,
            env=env,
            preexec_fn=os.setsid,
            text=True,
        )
        lines = []
        for raw_line in proc.stdout:
            line = raw_line.rstrip("\r\n")
            if line:
                lines.append(line)
                on_output(line)
        proc.wait()
        duration = time.monotonic() - start
        logger.debug("CMD", f"  -> rc={proc.returncode} duration={duration:.1f}s")
        return RunResult(
            returncode=proc.returncode or 0,
            stdout="\n".join(lines),
            stderr="",
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
