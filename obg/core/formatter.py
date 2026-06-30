from __future__ import annotations
from typing import Callable
from obg.utils.runner import run

LABEL_MAX_LEN = {
    "ext4": 16,
    "ntfs": 32,
    "exfat": 11,
    "fat32": 11,
}

def format_filesystem(
    partition: str,
    filesystem: str,
    label: str,
    on_output: Callable[[str], None],
) -> None:
    max_len = LABEL_MAX_LEN.get(filesystem, 16)
    if len(label) > max_len:
        on_output(f"Label truncated from '{label}' to '{label[:max_len]}' (max {max_len} chars for {filesystem})")
        label = label[:max_len]

    if filesystem == "ext4":
        cmd = ["mkfs.ext4", "-L", label, partition]
    elif filesystem == "ntfs":
        cmd = ["mkfs.ntfs", "-f", "-L", label, partition]
    elif filesystem == "exfat":
        cmd = ["mkfs.exfat", "-n", label, partition]
    elif filesystem == "fat32":
        cmd = ["mkfs.fat", "-F", "32", "-n", label, partition]
    else:
        raise ValueError(f"Unsupported filesystem: {filesystem}")

    result = run(cmd, on_output=on_output)
    if result.returncode != 0:
        raise RuntimeError(f"mkfs failed: {result.stderr}")
