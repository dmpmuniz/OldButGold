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
    pkg_dir = Path(__file__).resolve().parent.parent.parent
    if (pkg_dir / "tools").is_dir():
        return pkg_dir
    return None


def _resolve_tool(name: str) -> str:
    exe_dir = _tool_dir()
    if exe_dir:
        tp = exe_dir / "tools" / name
        if tp.exists() and os.access(tp, os.X_OK):
            loader = _find_loader(exe_dir)
            if loader:
                return f"{loader} --library-path {exe_dir / 'lib'} {tp}"
            return str(tp)
    which = shutil.which(name)
    if which:
        return which
    if getattr(sys, 'frozen', False):
        raise FileNotFoundError(
            f"Required tool '{name}' not found in application bundle "
            f"or system PATH. OldButGold must be executed from a complete distribution."
        )
    raise FileNotFoundError(f"Required tool not found: {name}")


def _find_loader(exe_dir: Path) -> str | None:
    import glob as _glob
    matches = _glob.glob(str(exe_dir / "lib" / "ld-linux*.so*"))
    for m in matches:
        if os.path.isfile(m) and os.access(m, os.X_OK):
            return m
    return None


def _build_env(use_bundled_libs: bool = False) -> dict[str, str]:
    env = os.environ.copy()
    if use_bundled_libs:
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
    resolved_str = _resolve_tool(command[0])
    resolved = resolved_str.split() + command[1:]
    cmd_str = " ".join(resolved) if len(" ".join(resolved)) < 200 else " ".join(resolved[:3]) + " ..."
    logger.debug("CMD", f"run: {cmd_str}")
    env = _build_env(use_bundled_libs=getattr(sys, 'frozen', False))
    start = time.monotonic()

    if on_output:
        proc = subprocess.Popen(
            resolved,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE if input_data else None,
            env=env,
            preexec_fn=os.setsid,
        )
        buf = b""
        lines = []
        fd = proc.stdout.fileno()
        while True:
            chunk = os.read(fd, 4096)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf or b"\r" in buf:
                idx = -1
                nidx = buf.find(b"\n")
                ridx = buf.find(b"\r")
                if nidx >= 0 and (ridx < 0 or nidx < ridx):
                    idx = nidx
                elif ridx >= 0 and (nidx < 0 or ridx < nidx):
                    idx = ridx
                if idx < 0:
                    break
                part = buf[:idx].decode("utf-8", errors="replace").rstrip("\r\n")
                if part:
                    lines.append(part)
                    on_output(part)
                buf = buf[idx + 1:]
        remaining = buf.decode("utf-8", errors="replace").strip()
        if remaining:
            lines.append(remaining)
            on_output(remaining)
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
