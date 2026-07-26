from __future__ import annotations
import os
import re
from typing import Callable
from obg.utils.runner import run


def _get_block_count(device: str) -> int:
    if os.path.isfile(device):
        return os.path.getsize(device) // 4096
    result = run(["blockdev", "--getsz", device])
    if result.returncode != 0:
        raise RuntimeError(f"blockdev --getsz failed: {result.stderr}")
    total_512 = int(result.stdout.strip())
    return total_512 // 8


def run_badblocks(
    device: str,
    on_output: Callable[[str], None],
    on_checkpoint: Callable[[float], None] | None = None,
    test_mode: bool = False,
    profile: str = "recommended",
    resume_offset: float = 0,
) -> int:
    def _base() -> list[str]:
        cmd = ["badblocks", "-w", "-s", "-v"]
        if profile == "recommended":
            cmd += ["-t", "0x55"]
        cmd += [device]
        return cmd

    if resume_offset > 0:
        MARGIN_PCT = 10
        total_blocks = _get_block_count(device)
        pct_of_total = resume_offset / 100
        start_block = max(0, int(total_blocks * pct_of_total) - int(total_blocks * MARGIN_PCT / 100))
        if test_mode:
            limit = max(1000, int(total_blocks * 0.01))
            blocks_count = limit
            command = _base() + ["-b", "4096", str(blocks_count), str(start_block)]
        else:
            blocks_count = total_blocks - start_block
            command = _base() + ["-b", "4096", str(blocks_count), str(start_block)]
        on_output(f"RESUME: resuming from {resume_offset:.0f}% (block {start_block}, checking {blocks_count} blocks)")
    elif test_mode:
        total_blocks = _get_block_count(device)
        limit = max(1000, int(total_blocks * 0.01))
        command = _base() + ["-b", "4096", str(limit), "0"]
        on_output(f"TEST MODE: destructive test of {limit} of {total_blocks} blocks (~1%)")
    else:
        command = _base()

    last_checkpoint = [-1]
    def _line_handler(offset_base=0):
        def handler(line: str) -> None:
            on_output(line)
            if on_checkpoint and "%" in line:
                m = re.search(r"([\d.]+)%", line)
                if m:
                    try:
                        pct = float(m.group(1))
                        bucket = int(pct // 10) * 10
                        if bucket > last_checkpoint[0]:
                            last_checkpoint[0] = bucket
                            on_checkpoint(offset_base + pct)
                    except ValueError:
                        pass
        return handler

    result = run(command, on_output=_line_handler())
    output = result.stdout + result.stderr
    bad_count = 0
    for line in output.splitlines():
        if "bad blocks found" in line.lower():
            parts = line.split(",")
            if len(parts) >= 2:
                num_part = parts[1].strip().split()
                if num_part:
                    try:
                        bad_count = int(num_part[0])
                    except ValueError:
                        pass

    if profile == "extended" and bad_count == 0:
        on_output("Extended profile: running additional read-only verification pass")
        read_cmd = ["badblocks", "-n", "-s", "-v", device]
        if test_mode:
            total_blocks = _get_block_count(device)
            limit = max(1000, int(total_blocks * 0.01))
            read_cmd = ["badblocks", "-w", "-s", "-v", "-b", "4096", device, str(limit), "0"]
            on_output(f"TEST MODE: destructive pass limited to {limit} blocks (~1%)")
        last_checkpoint[0] = -1
        read_result = run(read_cmd, on_output=_line_handler(offset_base=100))
        read_output = read_result.stdout + read_result.stderr
        for line in read_output.splitlines():
            if "bad blocks found" in line.lower():
                parts = line.split(",")
                if len(parts) >= 2:
                    num_part = parts[1].strip().split()
                    if num_part:
                        try:
                            bad_count = int(num_part[0])
                        except ValueError:
                            pass

    return bad_count
