#!/usr/bin/env python3
"""Pure measurement: how well does the game's SCOMPACT RLE compress deck.bin / screens?
No game-code changes — just a sizing experiment. (Tony's hunch: deck.bin packs better
than my earlier ~30% guess.)
Run: python tools/rle_test.py
"""
import os, zlib

# --- rle_compress: copied VERBATIM from tools/make_screens.py (the scheme the Z80 decoder reads) ---
def rle_compress(data):
    out = bytearray(); i = 0; n = len(data)
    while i < n:
        run = 1
        while i+run < n and data[i+run] == data[i] and run < 127: run += 1
        if run >= 3:
            out.append(0x80 | run); out.append(data[i]); i += run
        else:
            start = i
            while i < n:
                r = 1
                while i+r < n and data[i+r] == data[i] and r < 127: r += 1
                if r >= 3: break
                i += 1
                if i-start == 127: break
            out.append(i-start); out += data[start:i]
    return bytes(out)

def rle_decompress(comp):
    """Matching decoder: high-bit control = run of next byte; else literal of c bytes."""
    out = bytearray(); i = 0
    while i < len(comp):
        c = comp[i]; i += 1
        if c & 0x80:
            out += bytes([comp[i]]) * (c & 0x7F); i += 1
        else:
            out += comp[i:i+c]; i += c
    return bytes(out)

def report(name, data):
    comp = rle_compress(data)
    assert rle_decompress(comp) == data, f"ROUNDTRIP FAILED for {name}"
    z = len(zlib.compress(data, 9))
    pct = 100*len(comp)/len(data)
    print(f"  {name:28} {len(data):6} -> {len(comp):6}  ({pct:4.1f}%, saves {len(data)-len(comp):5})"
          f"   [zlib upper-bound: {z}]")
    return comp

print("=" * 78)
print("SCOMPACT RLE sizing test (roundtrip-verified). %, and bytes saved.")
print("=" * 78)

deck = open("deck.bin", "rb").read()
print("\n-- deck.bin as ONE blob --")
whole = report("deck.bin (whole)", deck)

print("\n-- deck.bin per-card (41 x 384B) -- realistic for decompress-on-draw --")
NCARD = len(deck)//384
per = [rle_compress(deck[c*384:(c+1)*384]) for c in range(NCARD)]
per_total = sum(len(p) for p in per)
idx = NCARD*2   # 2-byte offset table for random access
assert all(rle_decompress(p) == deck[c*384:(c+1)*384] for c,p in enumerate(per))
print(f"  41 cards summed           {len(deck):6} -> {per_total:6}  ({100*per_total/len(deck):.1f}%)"
      f"   + {idx}B offset index = {per_total+idx} total")
sizes = sorted(len(p) for p in per)
print(f"  per-card packed size: min {sizes[0]}, median {sizes[len(sizes)//2]}, max {sizes[-1]} (of 384)")

print("\n-- the title screens (already shipped, raw screen = 6912B) for reference --")
for f in ("title.rle", "title2.rle"):
    if os.path.exists(f):
        c = open(f, "rb").read()
        print(f"  {f:28} shipped {len(c)}B  = {100*len(c)/6912:.1f}% of a 6912B screen")

print("\n" + "=" * 78)
print("WHAT IT WOULD FREE (deck.bin currently 0xC000..0xFD80, only 640B spare above):")
print("=" * 78)
print(f"  whole-blob:  {len(deck)} -> {len(whole)}  => frees ~{len(deck)-len(whole)} bytes of the 0xC000 region")
print(f"  per-card+idx:{len(deck)} -> {per_total+idx}  => frees ~{len(deck)-(per_total+idx)} bytes")
print("  (decompress-on-draw also needs a ~384B scratch buffer to expand one card into.)")
