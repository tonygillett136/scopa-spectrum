# scopa-beam-race / game — decode-on-draw port AUDIT

A full port of the finished `scopa` game to **ZX0 decompression-on-draw**: the card deck is stored
compressed, cards are decompressed on demand, and the freed RAM is reclaimed — **tear-free and smooth**,
verified as far as possible without a CRT. The original `scopa/` was never touched; this is a copy in
`game/` with surgical changes.

## What changed (surgical)
- **One chokepoint:** `CARDS` (0xC000) was read *only* by `BlitCard`. `BlitCard` now calls `DecodeCardA`
  to get the card's bitmap address instead of `CARDS + id*384`.
- **Deck stored compressed:** `deck.bin` (15,744 B resident) → `deck.zx0` + index (8,408 B) at 0xC000.
- **Decoder + cache** (`DecodeCardA`, 68-byte `dzx0_standard`, `SlotAddr`, `WarmBoard`, 18-slot cache)
  live in the freed region (0xE100+).
- **Pre-warms** at the four tear-critical *direct-to-screen* draws so they're guaranteed cache HITS:
  `DrawDealtCard` (deal), `SlideIn` (moving card), the opp reveal-in-place, `DrawPlayedCard`.

## The architecture (why it's both RAM-saving AND tear-free)
A small **persistent 18-slot card cache**. `DecodeCardA(id)`: cache hit → return the slot address (cost
~850 T, ≈ scopa's old `id*384` multiply); miss → decompress into a round-robin slot. Consequences:
- **Per-frame animation re-renders are cache HITS** (`RenderShadow`/`DrawZipCards` during the re-pack,
  the slide's per-frame moving-card blit). So they run at scopa's original speed and the tear-critical
  `BlitSlice`/blit is *byte-for-byte the same work as the original* → **tear-free by construction.**
- Only a **genuinely new on-screen card** costs a decode (off-beam, pre-warmed where tear-critical).
- The freed ~7 KB (0xE312–0xFFFF region, minus the transient cache) is available for **non-gameplay
  screens** (win/score images) that don't need the cards — the cache and those images time-share it.

## Memory
| | original | port |
|---|---|---|
| deck (resident) | 15,744 B @0xC000 | — |
| deck.zx0 + index | — | 8,408 B @0xC000 |
| decoder + cache code | — | 530 B @0xE100 |
| 18-slot card cache | — | 6,912 B @0xE312 (transient; free between gameplay) |
| **freed for win/score art** | — | **~7 KB at rest** |
| **tape (.tap)** | ~45,115 B | **38,448 B** (~6.7 KB smaller) |

## Verification (CRT-free) — a `CacheMiss` counter proves tear-freeness
Tear-freeness holds **by construction** *iff* every tear-critical draw is a cache hit. A `CacheMiss`
byte (0xE1CF) counts every decompression. If any animation decoded per-frame it would be in the
**thousands**; if every tear-critical draw is a hit it equals only the **distinct cards seen**. Measured:

| Scenario | CacheMiss | Meaning |
|---|---|---|
| Deal cascade (TESTMODE 44, integrity self-check = 0) | **8** | = 3 hand + 4 table + 1 back; each decoded once, off-beam |
| Drop onto 6-card table + re-pack (TESTMODE 12) | **7** | the per-frame whole-board RenderShadow is all HITS |
| Near-full self-play attract match (.sna, ~75 s) | **23** | bounded growth as new cards appear — not per-frame |
| Tape boot → attract self-play (.tap, ~62 s) | **15** | same, from the compressed-tape build |

Plus: every board render is **byte-identical** to resident art (ZX0 decode is byte-exact, and the draw
code is unchanged — only the source pointer moved). The deal integrity self-check passes (0 mismatches).
The attract demo plays full matches with correct rendering and **no crash/desync**.

## What still needs Tony's CRT (the genuinely un-headless-able part)
ZEsarUX flattens per-scanline timing, so the *actual* tear-freeness is a real-hardware call. Load
`game/scopa.tap` (or `scopa.sna`) and watch, during a match:
1. **Slides** (hand → table) — clean, no horizontal split?
2. **Re-pack** (cards settling after a capture) — smooth, no "blinds"?
3. **Deal cascade** (round start) — each card lands clean?
4. **Crowded-table captures** (opp reveal-in-place; your card flashing in-hand) — clean?
5. **The one accepted cost:** a brief **hitch** the *first* time a new card appears on a board (the
   off-beam decode). It should be a momentary pause on a board change, never a tear. Is it acceptable?

## Notes
- The `CacheMiss` counter (5 bytes, in freed RAM) is a verification aid — harmless, removable.
- Cache size 18 covers all realistic boards (worst real ~14 distinct cards); a pathological TableN>15
  could thrash — not reachable in normal Scopa, and the attract proof showed no thrash.
- Next phase (only after CRT sign-off): spruce the win/score screens with images in the freed region.
