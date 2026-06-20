# scopa-beam-race — a sandbox experiment

A **throwaway learning sandbox**, built alongside the finished `scopa/` game (which is a polished,
shipped masterpiece we do **not** touch). The goal here is purely to explore two techniques that came
up while discussing the finished game, and to find out *how far they actually go on real hardware*:

1. **LZ compression of the card art**, with **decompression-on-draw** (keep only the compressed deck +
   one sprite-sized scratch buffer resident — no 15.7 KB of decompressed cards).
2. **Beam racing** — drawing tear-free both **ahead of** and **behind** the raster beam, so the
   (relatively expensive) decode can be slotted into the frame without tearing.

Nothing here needs to ship. The value is the measurements and the lessons.

## Background analysis (the "why")

### The card art barely RLE-compresses, but LZ ~halves it
The deck (40 cards + back, 48×64 mono, 384 B each = 15,744 B) is built with **Bayer dithering**, which
produces alternating byte patterns (`…AA 55 AA 55…`). Simple byte-RLE (runs of ≥3 identical bytes) finds
almost nothing — measured **~5%** off with the game's SCOMPACT RLE. But a real **LZ** scheme catches the
*repeating dither pattern*: zlib measured **~48%**. Flat-plate screens (title/loading) RLE fine (~58%)
because they're mostly solid regions; the dithered sprites are the opposite.

### The tear-free budget (48K timings)
- Frame = **69,888 T**; beam reaches display row 0 at **~14,336 T**; **224 T per pixel-line**; display
  ends ~57,344 T; bottom border + vblank ~12,544 T.
- `BlitCard` (a 48×64 card) ≈ **~9.7k T** (8 char-rows × ~1,180 T). It draws ~152 T/pixel-line — *faster*
  than the beam's 224 — so once ahead it stays ahead; the binding constraint is the tightest single line.

### Two safe windows to write a region
- **Ahead of the beam:** finish before the beam arrives. Top region ≈ the ~14,336 T top border (tight).
- **Behind the beam:** write *after* the beam has scanned past; the new pixels appear **next** frame
  (1-frame latency, invisible for animation). The top region's behind-beam window runs from when the beam
  clears row 63 (~28,672 T) to the next frame's row 0 (~84,224 T) ≈ **~55,000 T** — or confine it to the
  uncontended bottom-border/vblank (~26,900 T). Much roomier.

### Why behind-the-beam unlocks decode-on-draw
An in-line decode (LZ ≈ 20–30 T/output byte → ~8–12k T per 384 B card) does **not** fit the ~4.5k T
top-of-screen *ahead*-of-beam slide budget → it would tear at the top. But: **decode while the beam scans
the (still-unchanged) old region, then blit behind the beam** in the ~55k T window. The decode goes into a
single scratch buffer, the blit is the normal fast `BlitCard` from that buffer → tear-free *and* RAM-saving.

The catch (not solved here, documented as a wall): a **full-board redraw** that re-decodes all ~N on-screen
cards in one frame blows the frame budget → would need **incremental** shadow rendering (re-decode only the
1–2 cards that changed). This sandbox focuses on the **one-animating-card-per-frame** case where it works.

## What this sandbox builds (milestones)
- **M1** Custom **LZSS** compressor (Python) — chosen over zx0/zx7 for autonomous implementation
  reliability (zx0's Elias-gamma bitstream is easy to get subtly wrong with no reference). zx0 would
  compress better; LZSS is enough to demonstrate the technique. Roundtrip-verified on host.
- **M2** Z80 LZSS decoder, **byte-exact verified** in ZEsarUX before any drawing.
- **M3** Decode-on-draw of a static board (single 384 B scratch buffer, no persistent cache).
- **M4** Beam-raced draw: ahead-of-beam for mid/low cards, **behind-the-beam** for the top region, with
  **border-colour timing markers** so the timing is visible on a real CRT.
- **M5** A single card **slide animated entirely via decode-on-draw**, + `RESULTS.md`.

## Verification honesty
Correctness (byte-exact decode, correct render, no crash) and cycle timing are verified headless in
ZEsarUX. **Tear-freeness is a live raster effect that can't be screenshotted headless** — the border
markers make it eyeball-able on a CRT, but the final "no tearing" judgement is a real-hardware call.

## Design decisions (made autonomously)
- Custom LZSS, not zx0/zx7 (reliability; note the ratio left on the table).
- Local git only; no remote pushed unprompted.
- Everything copied into this dir; `scopa/` untouched.
