from __future__ import annotations
import subprocess
from typing import Callable
from obg.utils.runner import run


def _get_block_count(device: str) -> int:
    size_out = subprocess.check_output(["blockdev", "--getsz", device], text=True)
    total_512 = int(size_out.strip())
    return total_512 // 8


def run_badblocks(
    device: str,
    on_output: Callable[[str], None],
    test_mode: bool = False,
) -> int:
    command = ["badblocks", "-w", "-s", "-v", device]
    if test_mode:
        total_blocks = _get_block_count(device)
        limit = max(1000, int(total_blocks * 0.02))
        command = ["badblocks", "-w", "-s", "-v", "-b", "4096", device, str(limit), "0"]
        on_output(f"TEST MODE: testing {limit} of {total_blocks} blocks (~2%)")
    result = run(command, on_output=on_output)
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
