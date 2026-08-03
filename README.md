# OldButGold

**OldButGold** is a Linux terminal (TUI) toolkit for reviving and certifying
used HDDs/SSDs/NVMe drives. It runs a full hardware-validation pipeline —
SMART health check, destructive surface scan (badblocks), GPT partitioning,
filesystem formatting, and a graded classification (Gold / Silver / Bronze /
Failed) with a generated markdown report.

## Quick start

Run the self-contained binary as root:

```bash
pkexec ./OldButGold
```

Try the full flow without touching any real drive (uses an image file):

```bash
pkexec ./OldButGold --test --mock
```

Or from source:

```bash
pkexec python -m obg --test --mock   # safe trial on a mock image
pkexec python -m obg                 # full validation
```

## Test mode vs mock

- `--test` limits the badblocks scan to ~1% of the drive, but it is **still
  destructive** (it writes test patterns). Use it only on drives you don't care
  about.
- `--mock` creates a virtual disk image file (`test_disk_1gb.img`) — the only
  risk-free way to try the application.

## What it does

1. **Drive Identification** — enumerate disks, read SMART and geometry.
2. **Initial Health Check** — SMART short self-test + baseline capture.
3. **Surface Validation** — destructive badblocks surface scan, resumable if
   interrupted.
4. **Final Health Check** — re-read SMART and compute deltas.
5. **Prepare / Partition / Format** — GPT + chosen filesystem.
6. **Report** — graded classification with a markdown report.

## Requirements

- Linux, Python 3.11+
- `root` privileges (SMART + badblocks require raw device access, escalated
  via `pkexec`)
- Bundled `tools/` (smartctl, badblocks, lsblk, blockdev, sgdisk, partprobe,
  mkfs.*) and `lib/` — no host dependencies needed when run from the bundle.

## Technologies

- **Python 3.11+**
- **Textual** — modern TUI framework (mouse + keyboard navigation)
- **Rich** — ANSI colors and terminal rendering
- **PyInstaller** — self-contained single-binary packaging
- **smartctl / badblocks / lsblk / blockdev / sgdisk / partprobe / mkfs.*** —
  underlying hardware-validation toolchain

## Disclaimer

This tool was created by **dmpmuniz for personal use**. It is provided
**without any warranty of any kind**, express or implied. Use it at your own
risk: any damage to drives, data, or hardware is the sole responsibility of
the user. Only run it on drives whose data you do not need — validation is
destructive.

## License

MIT — see [LICENSE](LICENSE).
