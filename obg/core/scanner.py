from __future__ import annotations
from typing import Callable
from obg.utils.runner import run


def _get_block_count(device: str) -> int:
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
    command = ["badblocks", "-w", "-s", "-v", device]
    if resume_offset > 0:
        MARGIN_BLOCKS = 100
        total_blocks = _get_block_count(device)
        start_block = max(0, int(total_blocks * resume_offset / 100) - MARGIN_BLOCKS)
        command = ["badblocks", "-w", "-s", "-v", "-b", "4096", device, str(total_blocks), str(start_block)]
        on_output(f"RESUME: resuming from {resume_offset:.0f}% (block {start_block}/{total_blocks})")
    elif test_mode:
        total_blocks = _get_block_count(device)
        limit = max(1000, int(total_blocks * 0.01))
        command = ["badblocks", "-w", "-s", "-v", "-b", "4096", device, str(limit), "0"]
        on_output(f"TEST MODE: testing {limit} of {total_blocks} blocks (~1%)")

    last_checkpoint = [-1]
    def _line_handler(offset_base=0):
        def handler(line: str) -> None:
            on_output(line)
            if on_checkpoint and "%" in line:
                try:
                    pct = float(line.split("%")[0].strip())
                    bucket = int(pct // 10) * 10
                    if bucket > last_checkpoint[0]:
                        last_checkpoint[0] = bucket
                        on_checkpoint(offset_base + pct)
                except (ValueError, IndexError):
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
