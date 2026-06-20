#!/bin/sh
# Rebuild the official ZX0 compressor/decompressor (einar-saukas/ZX0) into ./tools.
# These are the GROUND TRUTH for the dzx0_standard.asm Z80 decoder (the PyPI `zx0`
# package was NOT byte-compatible with that decoder).
set -e
T=$(mktemp -d)
git clone --depth 1 https://github.com/einar-saukas/ZX0 "$T/ZX0"
cd "$T/ZX0"
cc -O2 -o zx0  src/zx0.c src/optimize.c src/compress.c src/memory.c
cc -O2 -o dzx0 src/dzx0.c src/memory.c
cd - >/dev/null
cp "$T/ZX0/zx0" "$T/ZX0/dzx0" "$(dirname "$0")/"
echo "built tools/zx0 + tools/dzx0"
