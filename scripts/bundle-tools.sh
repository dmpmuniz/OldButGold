#!/usr/bin/env bash
# bundle-tools.sh — Bundle required tools and their shared libraries
# into the release directory for true self-containment.
#
# Usage:  ./scripts/bundle-tools.sh [target-dir]
#         ./scripts/bundle-tools.sh --alpine [target-dir]   (Alpine Docker build)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-}"
ALPINE_FLAG=false

if [ "${1:-}" = "--alpine" ]; then
    ALPINE_FLAG=true
    shift
fi

# Auto-detect target
if [ -z "${1:-}" ]; then
    LATEST=$(ls -d "$SCRIPT_DIR/release/"OldButGold-* 2>/dev/null | sort -V | tail -1)
    [ -n "$LATEST" ] && TARGET="$LATEST"
else
    TARGET="$1"
fi
if [ -z "$TARGET" ]; then
    echo "Usage: $0 [--alpine] <release-dir>"
    echo "  --alpine  bundle from Alpine via Docker (requires Docker)"
    exit 1
fi

TOOLS_DIR="$TARGET/tools"
LIB_DIR="$TARGET/lib"
mkdir -p "$TOOLS_DIR" "$LIB_DIR"

# Tools required by TOOLCHAIN_SPECIFICATION §8
REQUIRED_TOOLS=(
    smartctl badblocks lsblk blockdev
    sgdisk partprobe mkfs.ext4 mkfs.ntfs mkfs.exfat mkfs.fat
)

# ---- Alpine Docker bundling ----
if $ALPINE_FLAG; then
    if ! command -v docker &>/dev/null; then
        echo "Docker required for Alpine mode. Install it or drop --alpine."
        exit 1
    fi
    echo "Building Alpine bundle via Docker..."
    echo "Target: $TARGET"
    docker run --rm -v "$TOOLS_DIR:/tools" -v "$LIB_DIR:/lib" alpine:3.20 sh <<'DOCKEREOF'
        apk add --no-cache smartmontools e2fsprogs e2fsprogs-extra lsblk \
            gptfdisk parted ntfs-3g-progs exfatprogs dosfstools

        # Copy each required tool
        for tool in smartctl badblocks lsblk sgdisk partprobe \
                    mkfs.ext4 mkfs.ntfs mkfs.exfat mkfs.fat; do
            path=$(which "$tool" 2>/dev/null || echo "")
            [ -n "$path" ] && cp -L "$path" /tools/ && echo "  copied $tool"
        done

        # Copy shared libraries
        for tool in /tools/*; do
            [ -f "$tool" ] || continue
            ldd "$tool" 2>/dev/null | grep '=> /' | awk '{print $3}' | while read -r lib; do
                [ -f "$lib" ] && cp -L "$lib" /lib/
            done
        done
        # Also copy ld-musl and libc
        cp -L /lib/ld-musl-x86_64.so.1 /lib/ 2>/dev/null || true
        cp -L /lib/libc.musl-x86_64.so.1 /lib/ 2>/dev/null || true
DOCKEREOF
    chmod +x "$TOOLS_DIR"/*
    ln -sf mkntfs "$TOOLS_DIR/mkfs.ntfs" 2>/dev/null || true
    echo "Alpine bundle complete."
    echo "  Tools: $(ls "$TOOLS_DIR" | wc -l)"
    echo "  Libs:  $(ls "$LIB_DIR" | wc -l)"
    exit 0
fi

# ---- Host-native bundling (default) ----
echo "Bundling tools from host system..."
echo "Target: $TARGET"

MISSING=0
for tool in "${REQUIRED_TOOLS[@]}"; do
    path=$(command -v "$tool" 2>/dev/null || true)
    if [ -z "$path" ]; then
        echo "  ❌ $tool not found on host"
        MISSING=$((MISSING + 1))
        continue
    fi
    # Resolve symlinks to real path
    real=$(readlink -f "$path" 2>/dev/null || echo "$path")
    cp -L "$real" "$TOOLS_DIR/"
    echo "  ✅ $tool ($real)"
done

echo ""
echo "Resolving shared library dependencies..."
for tool in "$TOOLS_DIR"/*; do
    [ -f "$tool" -a -x "$tool" ] || continue
    file "$tool" 2>/dev/null | grep -q ELF || continue
    ldd "$tool" 2>/dev/null | while read -r line; do
        if [[ "$line" =~ =\>\ (.+)\ \(0x ]]; then
            lib="${BASH_REMATCH[1]}"
            [ -f "$lib" ] && cp -L "$lib" "$LIB_DIR/" 2>/dev/null || true
        fi
    done 2>/dev/null || true
done

chmod +x "$TOOLS_DIR"/* 2>/dev/null || true

# Create expected aliases (some tools are multi-call binaries with symlinks)
(cd "$TOOLS_DIR" && ln -sf mkntfs mkfs.ntfs 2>/dev/null; ln -sf mkfs.fat mkfs.vfat 2>/dev/null; ln -sf mkfs.fat mkfs.msdos 2>/dev/null) || true

echo ""
echo "=== Bundle complete ==="
echo "  Tools: $(ls "$TOOLS_DIR" | wc -l) ($(du -sh "$TOOLS_DIR" | cut -f1))"
echo "  Libs:  $(ls "$LIB_DIR" | wc -l) ($(du -sh "$LIB_DIR" | cut -f1))"
echo ""

if [ $MISSING -gt 0 ]; then
    echo "WARNING: $MISSING tools missing."
fi
echo "Run: $TARGET/OldButGold"
