#!/usr/bin/env bash
# bundle-tools.sh — Bundle required tools and their shared libraries
# into the release directory (or source root) for self-containment.
#
# Usage:
#   ./scripts/bundle-tools.sh                     → auto-detect latest release dir
#   ./scripts/bundle-tools.sh <target-dir>        → bundle into target
#   ./scripts/bundle-tools.sh --source            → bundle into repo root (tools/ + lib/)
#   ./scripts/bundle-tools.sh --alpine [target]   → bundle from Alpine via Docker
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ALPINE_FLAG=false
SOURCE_FLAG=false
TARGET=""

for arg in "$@"; do
    case "$arg" in
        --alpine) ALPINE_FLAG=true ;;
        --source) SOURCE_FLAG=true ;;
        *)
            if [ -z "$TARGET" ]; then
                TARGET="$arg"
            fi
            ;;
    esac
done

if $SOURCE_FLAG && [ -z "$TARGET" ]; then
    TARGET="$SCRIPT_DIR"
elif [ -z "$TARGET" ]; then
    LATEST=$(ls -d "$SCRIPT_DIR/release/"OldButGold-* 2>/dev/null | sort -V | tail -1)
    if [ -n "$LATEST" ]; then
        TARGET="$LATEST"
    else
        echo "Usage: $0 [--alpine] [--source] [target-dir]"
        echo "  --source  bundle into repo root (tools/ + lib/)"
        echo "  --alpine  bundle from Alpine via Docker (requires Docker)"
        exit 1
    fi
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
    echo "=== Building Alpine bundle via Docker ==="
    echo "Target: $TARGET"
    docker run --rm -v "$TOOLS_DIR:/tools" -v "$LIB_DIR:/lib" alpine:3.20 sh <<'DOCKEREOF'
        apk add --no-cache smartmontools e2fsprogs e2fsprogs-extra \
            util-linux gptfdisk parted ntfs-3g-progs exfatprogs dosfstools

        for tool in smartctl badblocks lsblk blockdev \
                    sgdisk partprobe mkfs.ext4 mkfs.ntfs mkfs.exfat mkfs.fat; do
            path=$(which "$tool" 2>/dev/null || echo "")
            [ -n "$path" ] && cp -L "$path" /tools/ && echo "  copied $tool"
        done

        for tool in /tools/*; do
            [ -f "$tool" ] || continue
            ldd "$tool" 2>/dev/null | grep '/ld-musl\|/lib/' | awk '{print $3}' | \
            while read -r lib; do
                [ -f "$lib" ] && cp -nL "$lib" /lib/ 2>/dev/null || true
            done
        done
        cp -L /lib/ld-musl-x86_64.so.1 /lib/ 2>/dev/null || true
        cp -L /lib/libc.musl-x86_64.so.1 /lib/ 2>/dev/null || true
DOCKEREOF
    chmod +x "$TOOLS_DIR"/* 2>/dev/null || true
    (cd "$TOOLS_DIR" && ln -sf mke2fs mkfs.ext4 2>/dev/null; \
        ln -sf mkntfs mkfs.ntfs 2>/dev/null; \
        ln -sf mkfs.fat mkfs.vfat 2>/dev/null; \
        ln -sf mkfs.fat mkfs.msdos 2>/dev/null) || true
    echo "=== Alpine bundle complete ==="
    echo "  Tools: $(ls "$TOOLS_DIR" | wc -l) ($(du -sh "$TOOLS_DIR" | cut -f1))"
    echo "  Libs:  $(ls "$LIB_DIR" | wc -l) ($(du -sh "$LIB_DIR" | cut -f1))"
    exit 0
fi

# ---- Host-native bundling (default) ----
echo "=== Bundling tools from host system ==="
echo "Target: $TARGET"

MISSING=0
for tool in "${REQUIRED_TOOLS[@]}"; do
    path=$(command -v "$tool" 2>/dev/null || true)
    if [ -z "$path" ]; then
        echo "  .. $tool not found on host, will rely on bundled fallback"
        continue
    fi
    real=$(readlink -f "$path" 2>/dev/null || echo "$path")
    cp -L "$real" "$TOOLS_DIR/"
    echo "  +  $tool"
done

echo ""
echo "Resolving shared library dependencies..."
for tool in "$TOOLS_DIR"/*; do
    [ -f "$tool" ] || continue
    [ -x "$tool" ] || continue
    ldd "$tool" 2>/dev/null | awk '/=> \// {print $3}' | \
    while read -r lib; do
        [ -f "$lib" ] && cp -nL "$lib" "$LIB_DIR/" 2>/dev/null || true
    done
done

echo ""
echo "Bundling dynamic loader (ld-linux) for true self-containment..."
for loader in /lib64/ld-linux-x86-64.so.2 /lib/ld-linux-x86-64.so.2 \
             /usr/lib64/ld-linux-x86-64.so.2 /lib/ld-linux.so.2 \
             /usr/lib/ld-linux.so.2; do
    if [ -f "$loader" ]; then
        cp -nL "$loader" "$LIB_DIR/" 2>/dev/null || true
        echo "  +  $(basename "$loader")"
        break
    fi
done

chmod +x "$TOOLS_DIR"/* 2>/dev/null || true

(cd "$TOOLS_DIR" && ln -sf mke2fs mkfs.ext4 2>/dev/null; \
    ln -sf mkntfs mkfs.ntfs 2>/dev/null; \
    ln -sf mkfs.fat mkfs.vfat 2>/dev/null; \
    ln -sf mkfs.fat mkfs.msdos 2>/dev/null) || true

echo ""
echo "=== Bundle complete ==="
echo "  Tools: $(ls "$TOOLS_DIR" | wc -l) ($(du -sh "$TOOLS_DIR" | cut -f1))"
echo "  Libs:  $(ls "$LIB_DIR" | wc -l) ($(du -sh "$LIB_DIR" | cut -f1))"
echo ""

if [ $MISSING -gt 0 ]; then
    echo "NOTE: $MISSING tools not found on host."
    echo "For a complete bundle, use --alpine mode (requires Docker)."
fi
