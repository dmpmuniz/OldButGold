from __future__ import annotations
import os
import re
from typing import Callable
from obg.utils.runner import run


def get_profile_command(profile: str, device: str) -> list[str]:
    # Recommended: single pattern (0xaa) -> 1 write pass + 1 read pass (2 passes total).
    if profile == "recommended":
        return ["badblocks", "-w", "-s", "-v", "-b", "4096", "-t", "0xaa", device]
    # Extended: all default patterns (0xaa, 0x55, 0xff, 0x00) -> 8 passes total.
    return ["badblocks", "-w", "-s", "-v", device]


def _get_block_count(device: str) -> int:
    if os.path.isfile(device):
        return os.path.getsize(device) // 4096
    result = run(["blockdev", "--getsz", device], timeout=15)
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
    is_cancelled: Callable[[], bool] | None = None,
    idle_timeout: float | None = 600,
) -> int:
    if resume_offset > 0:
        MARGIN_PCT = 10
        total_blocks = _get_block_count(device)
        pct_of_total = resume_offset / 100
        start_block = max(0, int(total_blocks * pct_of_total) - int(total_blocks * MARGIN_PCT / 100))
        if test_mode:
            limit = max(1000, int(total_blocks * 0.01))
            blocks_count = limit
            command = get_profile_command(profile, device) + [str(blocks_count), str(start_block)]
        else:
            blocks_count = total_blocks - start_block
            command = get_profile_command(profile, device) + [str(blocks_count), str(start_block)]
        on_output(f"RESUME: resuming from {resume_offset:.0f}% (block {start_block}, checking {blocks_count} blocks)")
    elif test_mode:
        total_blocks = _get_block_count(device)
        limit = max(1000, int(total_blocks * 0.01))
        command = get_profile_command(profile, device) + [str(limit), "0"]
        on_output(f"TEST MODE: destructive test of {limit} of {total_blocks} blocks (~1%)")
    else:
        command = get_profile_command(profile, device)

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

    result = run(command, on_output=_line_handler(), stop_check=is_cancelled, idle_timeout=idle_timeout)
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

    return bad_count
