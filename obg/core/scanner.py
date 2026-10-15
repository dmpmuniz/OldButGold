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
    # 4 KiB blocks: the 1024-byte default is a legacy of the e2fsprogs era;
    # modern HDDs have 4096-byte physical sectors (256 KB I/O batches).
    return ["badblocks", "-w", "-s", "-v", "-b", "4096", device]


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
    MARGIN_PCT = 10
    total_blocks = 0
    start_block = 0
    last_block = None  # None = whole device (badblocks default)
    if resume_offset > 0:
        total_blocks = _get_block_count(device)
        start_block = max(0, int(total_blocks * resume_offset / 100) - int(total_blocks * MARGIN_PCT / 100))
        # badblocks positional args are ABSOLUTE positions (man page:
        # "last_block is the last block to be checked"), so a resumed scan
        # must end at the real end of the disk — passing a block count here
        # silently skipped the tail of the disk.
        last_block = max(start_block, total_blocks - 1)
        if test_mode:
            limit = max(1000, int(total_blocks * 0.01))
            last_block = min(last_block, start_block + limit - 1)
        on_output(
            f"RESUME: resuming from {resume_offset:.0f}% "
            f"(block {start_block}, checking {last_block - start_block + 1} blocks)"
        )
    elif test_mode:
        total_blocks = _get_block_count(device)
        limit = min(total_blocks, max(1000, int(total_blocks * 0.01)))
        last_block = max(0, limit - 1)
        on_output(f"TEST MODE: destructive test of {limit} of {total_blocks} blocks (~1%)")

    command = get_profile_command(profile, device)
    if last_block is not None:
        command += [str(last_block), str(start_block)]

    # Checkpoints are stored as percent-of-DISK. badblocks reports percent
    # of the scanned range, which is not the disk position on resumed or
    # test-mode runs.
    if total_blocks and last_block is not None:
        start_pct = start_block / total_blocks * 100
        range_pct = (last_block - start_block + 1) / total_blocks * 100
    else:
        start_pct, range_pct = 0.0, 100.0

    last_checkpoint = [-1]
    def _line_handler(start_pct=0.0, range_pct=100.0):
        def handler(line: str) -> None:
            on_output(line)
            if on_checkpoint and "%" in line:
                m = re.search(r"([\d.]+)%", line)
                if m:
                    try:
                        pct = float(m.group(1))
                        absolute_pct = start_pct + pct * range_pct / 100
                        bucket = int(pct // 10) * 10
                        if bucket > last_checkpoint[0]:
                            last_checkpoint[0] = bucket
                            on_checkpoint(absolute_pct)
                    except ValueError:
                        pass
        return handler

    result = run(command, on_output=_line_handler(start_pct, range_pct), stop_check=is_cancelled, idle_timeout=idle_timeout)
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
