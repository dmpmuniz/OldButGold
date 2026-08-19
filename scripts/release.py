#!/usr/bin/env python3
"""Build and package OldButGold release."""
import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO))
from obg import __version__

BUILD_DIR = REPO / "build"
DIST_DIR = REPO / "dist"
RELEASE_DIR = REPO / "release"
RELEASE_NAME = f"OldButGold-v{__version__}"


def clean():
    for d in [BUILD_DIR, DIST_DIR]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
    release = RELEASE_DIR / RELEASE_NAME
    if release.exists():
        shutil.rmtree(release, ignore_errors=True)
    zip_path = RELEASE_DIR / f"{RELEASE_NAME}.zip"
    if zip_path.exists():
        zip_path.unlink()


def build_binary():
    print("--- Building binary via PyInstaller ---")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", str(REPO / "obg.spec")],
        cwd=REPO,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("PyInstaller build failed")
    print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)


def assemble():
    src = DIST_DIR / "OldButGold"
    if not src.exists():
        raise RuntimeError(f"Binary not found: {src}")

    dst = RELEASE_DIR / RELEASE_NAME
    dst.mkdir(parents=True, exist_ok=True)

    print("--- Assembling release directory ---")
    shutil.copy2(src, dst / "OldButGold")
    print(f"  + OldButGold ({src.stat().st_size / 1024 / 1024:.1f} MB)")

    for d in ["tools", "lib", "assets"]:
        src_dir = REPO / d
        dst_dir = dst / d
        if src_dir.exists():
            shutil.copytree(src_dir, dst_dir, symlinks=True)
            count = len(list(dst_dir.rglob("*")))
            size = sum(f.stat().st_size for f in dst_dir.rglob("*") if f.is_file())
            print(f"  + {d}/ ({count} items, {size / 1024 / 1024:.1f} MB)")

    for d in ["reports", "sessions"]:
        (dst / d).mkdir(exist_ok=True)
        print(f"  + {d}/")

    readme_src = REPO / "README.md"
    if readme_src.exists():
        shutil.copy2(readme_src, dst / "README.md")

    license_src = REPO / "LICENSE"
    if license_src.exists():
        shutil.copy2(license_src, dst / "LICENSE")

    (dst / "reports" / ".gitkeep").write_text("")
    (dst / "sessions" / ".gitkeep").write_text("")


def package():
    print("--- Creating ZIP archive ---")
    dst = RELEASE_DIR / RELEASE_NAME
    zip_path = RELEASE_DIR / f"{RELEASE_NAME}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(dst):
            for f in files:
                if f.endswith(".log"):
                    continue
                path = Path(root) / f
                arcname = str(path.relative_to(RELEASE_DIR))
                zf.write(path, arcname)
    print(f"  -> {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")


def main():
    # ponytail: root check skipped in container build environments

    clean()
    build_binary()
    assemble()
    package()
    print(f"\n=== Release {RELEASE_NAME} complete ===")
    print(f"  Dir:  {RELEASE_DIR / RELEASE_NAME}")
    print(f"  Zip:  {RELEASE_DIR / RELEASE_NAME}.zip")


if __name__ == "__main__":
    main()
