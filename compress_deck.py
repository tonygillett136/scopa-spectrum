#!/usr/bin/env python3
"""M1: compress deck.bin per-card with the OFFICIAL ZX0 compressor (einar-saukas/ZX0,
built into ./tools/zx0), emit deck.zx0 (concatenated independent streams) + deck_index.bin
(41 x uint16 LE start offsets) for random-access decode-on-draw.

Each card is an independent self-terminating ZX0 stream, so the official dzx0_standard Z80
decoder decodes it standalone. HOST ROUNDTRIP: every stream is decompressed with the official
./tools/dzx0 and checked byte-exact BEFORE we trust it on the Z80. (The PyPI `zx0` package
was NOT byte-compatible with dzx0_standard — hence the official C tools.)

Run: python3 compress_deck.py
"""
import os, subprocess, tempfile, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ZX0 = os.path.join(HERE, "tools", "zx0")
DZX0 = os.path.join(HERE, "tools", "dzx0")
CARD = 384

for t in (ZX0, DZX0):
    if not os.path.exists(t):
        sys.exit(f"missing {t} — run tools/build_zx0.sh first")

deck = open(os.path.join(HERE, "deck.bin"), "rb").read()
NCARD = len(deck) // CARD
assert len(deck) % CARD == 0

streams = []
tmp = tempfile.mkdtemp()
for c in range(NCARD):
    raw = deck[c*CARD:(c+1)*CARD]
    fin = os.path.join(tmp, f"c{c}.bin")
    fout = fin + ".zx0"
    open(fin, "wb").write(raw)
    subprocess.run([ZX0, "-f", fin, fout], check=True, capture_output=True)
    comp = open(fout, "rb").read()
    # ---- host roundtrip with the official decompressor (the oracle) ----
    fdec = fin + ".dec"
    subprocess.run([DZX0, fout, fdec], check=True, capture_output=True)
    back = open(fdec, "rb").read()
    assert back == raw, f"OFFICIAL dzx0 roundtrip FAILED on card {c}"
    streams.append(comp)

print(f"host roundtrip: all {NCARD} cards verified byte-exact with official ./tools/dzx0 ✓")

blob = bytearray(); offsets = []
for s in streams:
    offsets.append(len(blob)); blob += s
assert max(offsets) < 0x10000
index = bytearray()
for off in offsets:
    index += bytes([off & 0xFF, (off >> 8) & 0xFF])

open(os.path.join(HERE, "deck.zx0"), "wb").write(blob)
open(os.path.join(HERE, "deck_index.bin"), "wb").write(index)

# whole-deck reference (not random-accessible)
fwhole = os.path.join(tmp, "whole.bin"); open(fwhole, "wb").write(deck)
subprocess.run([ZX0, "-f", fwhole, fwhole + ".zx0"], check=True, capture_output=True)
whole = len(open(fwhole + ".zx0", "rb").read())

sizes = [len(s) for s in streams]
total = len(blob)
print(f"\nper-card ZX0 (official): {NCARD} cards x {CARD}B = {len(deck)}B raw")
print(f"  blob {total}B ({100*total/len(deck):.1f}%) + index {len(index)}B = {total+len(index)}B resident")
print(f"  per-card: min {min(sizes)}, median {sorted(sizes)[len(sizes)//2]}, max {max(sizes)} bytes")
print(f"  whole-deck ZX0 (not random-accessible): {whole}B ({100*whole/len(deck):.1f}%)")
print(f"  vs earlier: zlib 7548B (47.9%) | shipped SCOMPACT-RLE 14889B (94.6%)")
print(f"\nwrote deck.zx0 ({total}B) + deck_index.bin ({len(index)}B)")
print(f"decode-on-draw resident: {total+len(index)}B compressed + {CARD}B scratch"
      f"  => frees ~{len(deck)-(total+len(index)+CARD)}B vs raw deck")
