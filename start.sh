#!/bin/sh
# OldButGold launcher — used by OldButGold.desktop; fine to call directly too.
# Elevates via sudo (prompts in the terminal the desktop opens); no pkexec
# or polkit involved.
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -x "$DIR/OldButGold" ]; then
    exec sudo "$DIR/OldButGold"
fi
echo "OldButGold not found in $DIR"
exec sh
