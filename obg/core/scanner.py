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
    if resume_offset > 0:
        on_output(f"RESUME: resuming from {resume_offset:.0f}% (safety margin applied)")

    command = ["badblocks", "-w", "-s", "-v", device]
    if test_mode:
        total_blocks = _get_block_count(device)
        limit = max(1000, int(total_blocks * 0.01))
        command = ["badblocks", "-w", "-s", "-v", "-b", "4096", device, str(limit), "0"]
        on_output(f"TEST MODE: testing {limit} of {total_blocks} blocks (~1%)")

    last_checkpoint = -1
    def _on_line(line: str) -> None:
        nonlocal last_checkpoint
        on_output(line)
        if on_checkpoint and "%" in line:
            try:
                pct = float(line.split("%")[0].strip())
                bucket = int(pct // 10) * 10
                if bucket > last_checkpoint:
                    last_checkpoint = bucket
                    on_checkpoint(pct)
            except (ValueError, IndexError):
                pass

    result = run(command, on_output=_on_line)
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
        last_checkpoint_read = -1
        def _on_read_line(line: str) -> None:
            nonlocal last_checkpoint_read
            on_output(line)
            if on_checkpoint and "%" in line:
                try:
                    pct = float(line.split("%")[0].strip())
                    bucket = int(pct // 10) * 10
                    if bucket > last_checkpoint_read:
                        last_checkpoint_read = bucket
                        on_checkpoint(100 + pct)
                except (ValueError, IndexError):
                    pass
        read_result = run(read_cmd, on_output=_on_read_line)
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
