# scopa-beam-race — RESULTS

An autonomous sandbox experiment (built 2026-06-19) to find out, with real measurements, whether
**ZX0 decompression-on-draw** of the Scopa card art could work within the **beam-race / tear-free**
budget on a 48K Spectrum. The finished `scopa/` game was never touched. Everything below is measured
on the Z80 in ZEsarUX (or host-verified), not estimated.

## TL;DR
- **Compression works well.** The dithered deck (15,744 B) packs to **8,326 B (52.9%)** as 41
  independent per-card ZX0 streams — vs the shipped SCOMPACT-RLE's **94.6%** (byte-RLE is useless on
  Bayer dither; LZ catches the repeating pattern). Decode-on-draw would free **~6.9 KB**.
- **The Z80 decode is correct.** All three official decoders (standard/turbo/mega) decompress every
  card **byte-exact** (verified vs `deck.bin`, 15,744 B).
- **But decode is FAR heavier than I'd guessed:** **~30,100 / 24,000 / 21,000 T-states per card**
  (standard/turbo/mega) = **43% / 34% / 30% of a whole frame**. My pre-experiment DESIGN.md estimate
  (8–12k T) was **2.5–3.7× too optimistic.**
- **Decode-on-draw is nonetheless feasible for one animated sprite per frame** — via a **one-frame
  pipeline** (blit the already-decoded card tear-free in the top border, decode the next during the
  frame's slack). Demonstrated live in MODE 4 (riffle) and MODE 5 (slide).
- **It does NOT scale to a full-board redraw** (re-decoding ~10 cards in one frame = ~210–300k T =
  3–4 frames → a visible hitch). That would need incremental rendering. Unchanged conclusion from the
  desk analysis, now with hard numbers.

## 1. Compression (official einar-saukas ZX0, per-card)
| | bytes | % of raw |
|---|---|---|
| raw deck (41 × 384) | 15,744 | 100% |
| **per-card ZX0 (random-accessible)** | **8,326 + 82 index** | **52.9%** |
| whole-deck ZX0 (NOT random-accessible) | 7,202 | 45.7% |
| zlib (reference upper bound) | 7,548 | 47.9% |
| shipped SCOMPACT-RLE | 14,889 | 94.6% |

Per-card: min 23 B (the BACK), median 213 B, max 264 B. Random-access per-card streams are what make
decode-on-draw possible; they cost ~1.1 KB of ratio vs whole-deck (no cross-card matches).
Host roundtrip with the official `dzx0` + Z80 byte-exact both **PASS**.

> Note: the PyPI `zx0` package's output was NOT byte-compatible with `dzx0_standard.asm` (the first
> literal-length Elias diverged). The official C `zx0`/`dzx0` (built by `tools/build_zx0.sh`) are the
> ground truth and were used throughout.

## 2. Decode cost (measured on the Z80, 250-frame round-robin)
| decoder | size | T-states/card | T/output-byte | fraction of a 69,888 T frame |
|---|---|---|---|---|
| standard | 68 B | 30,124 | 78.4 | **43%** |
| turbo | 126 B | 24,000 | 62.5 | 34% |
| mega | 673 B | 21,000 | 54.7 | 30% |

(Includes <~1% ROM-ISR overhead → a slight overestimate, i.e. budget-safe.) `BlitCard` itself is ~9.7k T.

## 3. The beam budget, with real numbers
Frame = 69,888 T; beam reaches display row 0 at ~14,336 T; 224 T/line; bottom-border/vblank ~12,544 T.

- **In-line decode before a top-of-screen blit is impossible.** The top-slide *ahead-of-beam* budget is
  ~4,500 T; even mega needs 21,000. It would tear catastrophically.
- **Even the bottom-border/vblank window (~26,900 T) can't hold the standard decoder (30k).** Turbo/mega
  just fit it; standard does not.
- **What works: the one-frame pipeline.** Blit the *already-decoded* card at the frame top in the
  ~14,336 T top border (tear-free, ~9.7k T), then decode the *next* card (21–30k T) during the rest of
  the frame. Crucially the decoder works in **uncontended upper RAM (0x8000–0xFFFF)**, so the beam
  doesn't slow it. Per-frame cost = blit (9.7k, tear-critical) + decode (21–30k, non-critical) =
  31–40k T < 69,888. Comfortable for **one** sprite/frame. (MODE 4 does exactly this.)
- For a sprite in the **table band** (row 12, beam @ ~35,840 T) you can even erase+blit *and* keep the
  decode after — MODE 5 slides a card there, redrawn every frame.

## 4. What to look for on a real CRT (the headless-blind part)
Tear-freeness and the per-scanline border colour are **live raster effects** — ZEsarUX screenshots
flatten the border to one colour, so they can't show them. On a real Spectrum (or an accurate CRT-mode
emulator) the **border timing markers** make the cost visible:
- **MODE 4** (riffle, top of screen): a thin **CYAN** band at the very top (the blit), then a **RED**
  band covering ~⅓–½ the screen height (the decode), then **BLACK**. The card should change cleanly each
  frame with **no horizontal tear**.
- **MODE 5** (slide, table band): **CYAN** while the card's erase+blit happens (should finish before the
  beam reaches the card), **RED** for the re-decode, **BLACK** idle. The sliding settebello should have
  **no torn/half-drawn** frames. *This is the headline test:* if the erase+blit is ever caught by the
  beam, you'll see a horizontal split in the moving card.

Build the demo for the CRT with: `python3 build.py 5 2` (slide, mega) → `main.tap` / `main.sna`.
Try `build.py 5 0` (standard decoder, 43%/frame) to see the bigger RED band and whether the tighter
budget still holds.

## 5. Verdict
The desk analysis was right in shape but wrong in magnitude. Decode-on-draw is **viable for the
animation hot path** (one sprite/frame) via the pipeline, and it would genuinely free ~6.9 KB — **but**
(a) the decode is a third-to-nearly-half of every frame, so it dominates the CPU budget, (b) a faster
decoder (mega) is worth its 673 bytes, and (c) full-board redraws still need incremental rendering to
avoid a multi-frame hitch. For the finished Scopa — which has no RAM pressure and a polished, tear-free
animation pipeline — it isn't worth it. As a **technique**, it's proven and measured: a useful tool for a
future, RAM-starved project where the art is dither-heavy.

## Milestones
- M0 scaffold · M1 ZX0 per-card compress + host roundtrip · M2 Z80 decode byte-exact (3 decoders) ·
  M2+ decode timing · M3 decode-on-draw static board · M4 beam-raced pipeline (riffle) · M5 slide tear test.

## How to build / run
```
tools/build_zx0.sh           # (once) build the official zx0/dzx0 compressor tools
python3 compress_deck.py     # deck.bin -> deck.zx0 + deck_index.bin (per-card ZX0)
python3 build.py 5 2         # assemble MODE=5 (slide) DEC=2 (mega) -> main.sna + main.tap
python3 measure_all.py       # verify byte-exact + time all three decoders
python3 verify_m2.py         # byte-exact decode check (MODE 2)
# MODE: 2=verify 3=board 4=riffle 5=slide ; DEC: 0=standard 1=turbo 2=mega
```
