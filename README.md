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

- Linux, Python 3.11+
- `root` privileges (SMART + badblocks require raw device access)
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

Esta ferramenta foi criada por **dmpmuniz para uso pessoal**. Ela é fornecida
**sem garantia de qualquer tipo**, expressa ou implícita. O uso é por conta e
risco do usuário: qualquer dano a discos, dados ou equipamento é de inteira
responsabilidade de quem a utilizar. Use apenas em drives dos quais você não
precisa dos dados — a validação é destrutiva.

## License

MIT — see [LICENSE](LICENSE).
