# scopa-beam-race

A throwaway **learning sandbox** built alongside the finished [`scopa`](../scopa) game (which is left
untouched). It answers one question with real measurements: *can the Scopa card art be **ZX0-compressed**
and **decompressed on-draw**, tear-free, within the Spectrum's **beam-race** budget?*

**Answer:** yes for one animated sprite per frame (via a one-frame pipeline), no for full-board redraws —
and the decode is much heavier than a desk estimate suggested. Full write-up + numbers in
**[RESULTS.md](RESULTS.md)**; the design rationale and beam-timing analysis in **[DESIGN.md](DESIGN.md)**.

## Headline numbers
- Per-card ZX0: **52.9%** (8.3 KB vs 15.7 KB raw) — frees ~6.9 KB. (Shipped RLE managed only 94.6% on the
  dithered art.)
- Z80 decode: **byte-exact** (standard/turbo/mega), at **30k / 24k / 21k T-states per card** =
  **43% / 34% / 30% of a frame**.
- Tear-free decode-on-draw demonstrated live (MODE 4 riffle, MODE 5 slide).

## Quick start
```
tools/build_zx0.sh        # once: build official einar-saukas zx0/dzx0
python3 compress_deck.py  # deck.bin -> deck.zx0 + index
python3 build.py 5 2      # MODE 5 (slide) DEC 2 (mega) -> main.sna + main.tap
```
Load `main.sna` (emulator) or `main.tap` (real hardware / tape). The border colour bands (CYAN=blit,
RED=decode, BLACK=idle) are the timing visualisation — **visible on a real CRT**, flattened in headless
screenshots.

MODE: `2` verify-decode · `3` static board · `4` riffle (pipeline) · `5` slide (tear test).
DEC: `0` standard(68B) · `1` turbo(126B) · `2` mega(673B).

## Files
- `main.asm` — the demo (MODE/DEC selectable); includes the three official `dzx0_*` decoders verbatim.
- `dzx0_turbo.asm`, `dzx0_mega.asm` — verbatim official ZX0 decoders.
- `compress_deck.py`, `build.py`, `measure_all.py`, `verify_m2.py` — tooling.
- `tools/build_zx0.sh` — rebuilds the official zx0/dzx0 C tools.
- `deck.bin` — copied from scopa (the card art source; copyrighted real-deck-derived art is NOT here).

All code uses the official ZX0 tools/decoders (the PyPI `zx0` package was not byte-compatible with
`dzx0_standard`). Built autonomously; tear-free judgement on a real CRT is the user's call.
