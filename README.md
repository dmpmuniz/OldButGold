# OldButGold

**OldButGold** is a Linux terminal (TUI) toolkit for reviving and certifying
used HDDs/SSDs/NVMe drives. It runs a full hardware-validation pipeline —
SMART health check, destructive/non-destructive surface scan (badblocks),
GPT partitioning, filesystem formatting, and a graded classification
(Gold / Silver / Bronze / Failed) with a generated markdown report.

## Quick start

Run the self-contained binary as root:

```bash
pkexec ./OldButGold
```

Or from source (requires root):

```bash
sudo python -m obg --test    # non-destructive ~1% smoke test
sudo python -m obg           # full validation
```

## What it does

1. **Drive Identification** — enumerate disks, read SMART and geometry.
2. **Initial Health Check** — SMART short self-test + baseline capture.
3. **Surface Validation** — badblocks surface scan (non-destructive `--test`,
   destructive full run otherwise). Resumable if interrupted.
4. **Final Health Check** — re-read SMART and compute deltas.
5. **Prepare / Partition / Format** — GPT + chosen filesystem.
6. **Report** — graded classification with a markdown report.

## Requirements

- Linux, Python 3.10+
- `root` privileges (SMART + badblocks require raw device access)
- Bundled `tools/` (smartctl, badblocks, lsblk, blockdev, sgdisk, partprobe,
  mkfs.*) and `lib/` — no host dependencies needed when run from the bundle.

## License

MIT — see [LICENSE](LICENSE).
