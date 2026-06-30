from __future__ import annotations
import os
import time
from obg.utils.runner import run


def create_gpt(device: str) -> None:
    result = run(["sgdisk", "--zap-all", device])
    if result.returncode != 0:
        raise RuntimeError(f"sgdisk --zap-all failed: {result.stderr}")


def create_partition(device: str) -> str:
    result = run(["sgdisk", "-n", "1:0:0", "-t", "1:8300", device])
    if result.returncode != 0:
        raise RuntimeError(f"sgdisk create partition failed: {result.stderr}")

    result = run(["partprobe", device])
    time.sleep(2)

    name = os.path.basename(device)
    if name[-1].isdigit():
        return f"{device}p1"
    else:
        return f"{device}1"
