#!/bin/sh
# The one true build: assemble (ALWAYS with --sym: build_tap.py reads TapeFlag/dzx0/WinZX0 from
# scopa.sym, and plain `sjasmplus scopa.asm` does NOT rewrite it -> stale-sym mis-pokes), then
# pack the tape + TZX. Usage: ./build.sh  [from scopa/]
set -e
cd "$(dirname "$0")"
../mastery/tools/sjasmplus scopa.asm --sym=scopa.sym
python3 build_tap.py
python3 build_tzx.py
ls -l scopa.tap scopa.tzx scopa.sna
