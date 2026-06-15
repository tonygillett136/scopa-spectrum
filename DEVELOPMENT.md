# SCOPA for the 48K ZX Spectrum — Development Reference

A near-100% Z80 machine-code recreation of the Italian card game **Scopa**, built for
a real 48K ZX Spectrum. This document is the "resume cold" reference: architecture,
memory map, build process, key decisions and gotchas. For the chronological story see
`DEVLOG.md`; for the rule spec see the old web project at `/Volumes/SSD1/code/scopa_spectrum`.

> Context: recreating Angelo Colucci's lost Scopa (a friend's game from years ago, whose
> hand-drawn cards were superb). Goals: strong AI, simple elegant UI, and cards that look
> the best the hardware allows. Player vs CPU, match to 11.

---

## 1. What it is / current feature set

- Title + loading screens (vibrant colour close-ups of Napoletane card-tops, tricolore "SCOPA").
- Skill select: EASY / MEDIUM / HARD, plus an optional "Asso piglia tutto" rule toggle (key 4,
  default OFF) — when on, an ace takes the whole table (Scopa d'Assi: that sweep scores no scopa).
- Full 40-card Napoletane deck in **defined-monochrome** 48×64 art + a card back. The three
  **coppe figure cards** (Fante/Cavallo/Re) carry a small traced goblet pip top-left for suit
  clarity; denari/spade/bastoni unbadged (denari is then clear by elimination — Tony's call).
- Complete rules: single-card-capture priority, mandatory capture, subset-sum captures,
  scopa (sweep) with the last-play exception, last-capturer takes the table at round end.
- Scoring: carte, denari, settebello, primiera (needs all 4 suits), scope, **napola
  (Neapolitan)**. Match to 11; dealer/leader alternates each round.
- Feedback: shadow-buffered flicker-free render; captured cards flash; live pile counts;
  SCOPA! banner; big NEAPOLITAN screen + rising-scale jingle; beeper SFX; win/lose tunes.

---

## 2. Files

```
scopa/
  scopa.asm            THE game (Z80, sjasmplus). ~3850 lines. Builds scopa.sna + scopa_code.bin.
  deck.bin             40 cards + 1 back, 384 bitmap bytes each (15744 B). INCBIN @0xC000.
                       Coppe figures (cards 17/18/19) carry a cup pip (convert_deck.cup_badge).
  deck_v1_backup.bin   OLDER pre-figure-touch-up deck (md5 3aac…); NOT a per-round baseline. To
                       revert just the cup pips: drop the suit==1&value>=8 stamp in convert_deck
                       and re-run it (NOT cp deck_v1_backup, which also loses the figure touch-ups).
  title.scr / loading.scr  6912-byte SCR screens (from make_screens.py).
  scopa_code.bin       assembled code 0x8000..CodeEnd (for the tape; excludes title/deck).
  scopa.tap            the real-hardware tape (silent multi-part loader).
  build_tap.py         builds scopa.tap from scopa_code.bin + loading.scr + title.scr + deck.bin.
  tools/
    convert_deck.py    reference JPGs -> deck.bin (defined-mono). RUN FROM scopa/ (writes CWD-relative!).
    make_screens.py    reference JPGs -> title.scr + loading.scr (colour per-cell quantise).
    compare_figures.py figure-card conversion A/B montage (-> /tmp/figure_compare.png).
    mono_outline.py    helpers (fit, BAYER, png) used by convert_deck.py.
  DEVLOG.md            chronological build log.
  DEVELOPMENT.md       this file.
```

Spec source (DO NOT ship from here — reference only): `/Volumes/SSD1/code/scopa_spectrum/`
- `js/game/rules.js, scoring.js, ai.js` — the portable rules/scoring/AI spec.
- `reference_cards/01-40_*.jpg` — the 40 Napoletane card photos.

---

## 3. Memory map (48K)

```
0x4000-0x5AFF  ZX screen (bitmap 0x4000, attrs 0x5800)
0x6000-0x7245  title.rle (INCBIN, 4646 B SCOMPACT-packed) — DecompressScr expands it to
               0x4000 at boot, THEN this region is reused as the SHADOW BUFFER (transient)
0x6000-0x7AFF  SHADOW BUFFER (bitmap 0x6000, attrs 0x7800) — render here, then blit to 0x4000
0x8000-~0x9430 code (grows up; CodeEnd ~0x9430 now) — ceiling is the state block @0xB000
0xB000-~0xB104 state vars (ORG 0xB000)
0xBFF0         stack (SP set at Start)
0xC000-0xFD7F  deck.bin (INCBIN; card src for BlitCard)
0x5B00 area    printer buffer — the tape's 43-byte silent loader lives at 23296
```
Headroom note: the title screen NO LONGER occupies 0x9400 — it's SCOMPACT-compressed
(make_screens.py rle_compress → title.rle) and parked in the shadow region @0x6000, where
ShowTitle (DecompressScr) expands it to the screen at boot and the first gameplay frame
overwrites it. So code now grows freely 0x8000→0xB000 (~7 KB headroom). NEXT lever if even
that fills: compress deck.bin too (decompress-on-draw) — modest (~30 %, dither limits RLE).

Key state vars (offsets drift as vars are added — search the `ORG 0xB000` block):
Deck[40], Player[3], Opp[3], Table[16], TableN, DeckPos, Seed[2], PPile[40]/PPileN,
OPile[40]/OPileN, PScopa/OScopa, Who, FCval, CapSel[16], Played, Cursor, LastCap, Keys,
PMatch/OMatch, PRound/ORound, CatWin[5], Options[32]/OptionN, AI eval scratch (ScoreW,
BestScoreW...), TmpTable[16], Leader, Difficulty, Seen[5], ScrOfs, HumanTurn, Pnapola/Onapola.

---

## 4. Card data convention (CRITICAL)

`id = filenum-1` (0..39).  `value = id%10 + 1` (1..10; 8/9/10 = Fante/Cavallo/Re).
`suit = id//10`: **0 denari, 1 coppe, 2 spade, 3 bastoni**.  Settebello = id 6 (7 of denari).
Denari (coins) = ids 0..9. Card back = id 40.

⚠️ The JS spec uses a DIFFERENT suit order (DENARI=1 there). When porting JS that uses
literal ids (e.g. ai.js card-counting), translate to MY convention — don't copy ids.

---

## 5. Rendering architecture

**Shadow buffer (flicker-free).** `PaintAll` sets `ScrOfs=0x20`, clears + draws the whole
frame into 0x6000, then `Blit` LDIRs 6912 B to 0x4000 in one pass, then `ScrOfs=0`. The
live screen is never blanked, so no cyan-flash flicker. `ScrOfs` (0x00 screen / 0x20
shadow) is added to the high byte in BlitCard / PrintChar / HandAttrHL / FlashTableCard,
so the same routines target shadow (during PaintAll) or screen (overlays + cursor moves).
Overlays (ShowCapture flash, ShowScopa banner, PaintChoice) run AFTER PaintAll's blit and
draw straight to the live screen (ScrOfs=0). Cursor moves are attr-only (no repaint).

**Tearing / vblank (INTERRUPTS ON).** Game enables `im 1; ei` at Start (+`ld iy,0x5C3A`
for the ROM ISR). GOTCHA: `Shuffle` hijacks IY for its swap -> it's bracketed `di…ei` and
restores `iy=0x5C3A` on exit, else the next ROM ISR corrupts. A full-screen blit (~145 kT
≈ 2 frames) is ~10× too big for the ~14.3 kT blanking window, so it can NEVER be vsynced;
`Blit` just does `halt` first so a wholesale redraw's seam is STABLE not a shimmer. The
genuinely tear-free path is per-CARD: one 6×8 region (~430 B, ~10 kT) written top-to-bottom
after HALT finishes ahead of the raster (14.3 kT head start; we write ~1250 T/cell-row vs
the beam's 1792). Cursor/capture FLASHES are hardware (attr bit 7 = ULA flash) — never tear.

**SlideIn (tear-free, save-under).** `RenderShadow` ONCE = static board with the played
card removed; then per step: `halt` → `EraseCardRegion(prevcell)` (restore the 6×8 footprint
from shadow 0x6000→screen 0x4000) → `BlitCard(newcell)`. 8 cell-row steps (SlRowStep ±1) =
smooth 8 px travel; column interpolated 8.8 (`SlideDelta` = delta<<5 for 8 intervals); state
SlPrevCol/SlPrevRow track the cell to erase. No full blit per step -> tear-free + smooth.

**Table re-space zip (ZipCompact).** Whenever the table re-lays out, the cards slide to
their new columns instead of snapping. `ZipCompact` moves Table[0..TableN-1] from `ZipCur[]`
(current columns) toward `1+ZipStep*k`, 4 cols/frame, BIDIRECTIONAL (TableStep changes at
6↔7=5/4 and 7↔8=4/3, so survivors move left when the table shrinks and right when it widens).
`HideTable=1` makes RenderShadow skip its table loop; `DrawZipCards` draws the cards at
`ZipCur` (skips cols ≥27). CAPTURE: `CaptureZipOld` records survivors' old cols → CompactTable
→ ZipCompact. DROP: `FillZipCols` records existing cols + the slide's landing col → add card
→ ZipCompact; if TableN≥7 the laid card is `FlashTableCard`-flashed + paused so it's clear on
a crowded row. (>=10 cards still overflow the single 32-col row — fundamental layout limit.)

**BlitCard** A=cardid, D=col(cell), E=row(cell): src = CARDS + id*384; copies 64 rows × 6
bytes with the next-row-down idiom; sets the 6×8 attr block to 0x78 (white card). Layout:
opp backs row 0, table row 8 (step from `TableStep` = 5/4/3 by TableN), hand row 16.

**Cursor**: HighlightCursor flashes the selected hand card with 0xF8 — only when `HumanTurn=1`
(set in PlayerTurn, cleared in OppTurn / on play), and not on an empty slot.

**Capture flash**: FlashTableCard flashes only a card's VISIBLE width (= step for an
overlapped card, 6 for the last/played) so it doesn't bleed onto the card drawn on top.

**Played card during capture-choice (card-in-hand)**: the multi-capture choice runs *before* the
card leaves the hand. `PlayerTurn` keeps the card in `Player[]`, calls `findAllCaptures`, and (if
≥2 options) runs `PlayerChooseCapture` while the card is still in the hand — only then removes it,
slides, and resolves (`ResolvePlay` uses the pre-chosen `ChoiceMade`/`ChoiceVal` instead of
re-prompting). `PaintChoice` therefore `HighlightCursor`s the in-hand card (flash) — it is NOT
drawn on the table, so it can't overlap a table card on a crowded table (Ange's bug). The candidate
table cards flash in sync with the hand card. `DrawPlayedCard` (draw `Played` at the post-table slot
col 1+step*TableN clamped 26, row 8) is still used by `ShowCapture` to show the card landing + taking
its catch *after* the choice is confirmed.

**Text**: PrintChar copies ROM font (0x3D00). PrintBig* does a 2× blow-up (DoubleNib LUT +
ScreenDown) for the NEAPOLITAN banner. FillAttrRow colours a whole char-row.

---

## 6. Game flow

Start → border black, seed PRNG (R+FRAMES), hold loading screen ≥3 s, ShowTitle
(DecompressScr expands title.rle@0x6000 → 0x4000, wait SPACE), SelectDifficulty
(keys 1/2/3) → RunMatch. Match end → ShowWinYou/ShowWinOpp (big title + FINAL SCORE +
"PRESS SPACE TO PLAY AGAIN"; player win = WaitWinner tricolore border shimmer) → loop.
RunMatch: NewMatch (border cyan, Leader=0) → loop: NewRound (shuffle+deal+mark Seen) →
PlayRound → ScoreRound → (if napola) ShowNeapolitan → ShowResults → toggle Leader →
check 11 → ShowWin*/loop.
PlayRound: leader plays then follower (Leader chooses order), redeal 3 each when both
hands empty, SweepToLast at deck-empty.
PlayerTurn: O/P move cursor (attr-only), SPACE plays. On SPACE the card stays IN the hand while
findAllCaptures runs; if ≥2 capture options → PlayerChooseCapture (O/P cycle, candidate table
cards flash in sync with the flashing in-hand card, SPACE confirm) → ChoiceMade/ChoiceVal; only
THEN remove from hand, slide, ResolvePlay. So the played card never overlaps the table during the
choice. OppTurn: aiSelectPlay → ResolvePlay.
SelectDifficulty (the pre-game skill screen): 1/2/3 pick Easy/Medium/Hard; key 4 toggles the
optional "ASSO PIGLIA TUTTO" rule OFF↔ON (white/green; default OFF, reset each time the menu shows).

---

## 7. Rules engine

`findAllCaptures(A=value)` → `Options[]` (table-index bitmasks) + `OptionN`. Singles take
priority (if any single matches, only singles listed); else all subset-sum combinations.
`ResolvePlay(A=cardid, C=who)`: MarkSeen; findAllCaptures; player uses the pre-chosen
ChoiceMade/ChoiceVal (else PlayerChooseCapture) / AI uses AIOpt / single auto; ShowCapture;
move captured + played to pile; CompactTable; scopa if table swept and not the last play
(IsLastPlay = handP+handO+deckleft ≤ 1) and not an ace-sweep (AceSweepOpt).

**Optional rule — "asso piglia tutto" (`AceRule`, default OFF, toggle on the skill screen).**
When on, `findAllCaptures` for a played ace (value 1) with NO ace on the table and a non-empty
table returns a single option = the full-table mask (capture everything) and sets `AceSweepOpt`.
The other cases are already standard engine behaviour: an ace *with* an ace on the table takes
that ace by single-card match; an ace on an empty table just drops. We implement the **Scopa
d'Assi** reading — sweeping with an ace is NOT a scopa — so ResolvePlay skips the scopa award when
`AceSweepOpt`. The AI needs no special-casing: it scores candidate plays through `findAllCaptures`,
so it sees the ace-sweep capturing the whole table and values it.
Helper `addHLA` (HL+=A, preserves BC/DE) is used for ALL base+index addressing — hand-rolled
`ld bc,BASE; add hl,bc` clobbers loop counters (a bug class hit early on).

**Scoring** (ScoreRound): carte/denari (most; tie=0), settebello (id6), primiera (PRIME
scale 7=21,6=18,A=16,5=15,4=14,3=13,2=12,fig=10; best per suit; **0 unless all 4 suits**),
scope (sweeps), **napola** (Napola: needs coins A,2,3 = ids 0,1,2 → 3 pts, +1 per further
consecutive coin id 3,4,5… up to 10 "Napoleone"; else 0). Each player's napola added to
their round total; ShowNeapolitan triggers if either > 0.

---

## 8. AI (aiSelectPlay)

Evaluates EVERY (card × capture option) and each drop, scores with the ai.js weight table
(signed 16-bit ScoreW): sweep +50, settebello-capture +35, 7/6/ace primiera, denari +5,
card-count ×2; drop penalties settebello −40, 7 −12, 6 −6, denari −4, +3 face; sweep-risk
−20 (table sum ≤10), easy-capture −2 per matchable value. Picks the max (ConsiderBest;
first play always taken to dodge the −32768 signed-overflow trap).
Difficulty: EASY skips sweep-avoidance (EvalSafety gated off); MEDIUM = full; HARD adds
CardCount (late-game aggression once <16 unseen) using the Seen[5] 40-bit tracker (marked
at deal: table+opp hand; and each play: the played card).
Asso-piglia-tutto accuracy: EvalCapture does NOT add the +50 scopa for an ace-sweep (AceSweepOpt
set) — Scopa d'Assi. EvalSafety penalises leaving an ace-LESS table when AceRule is on (the opponent
could ace-sweep it): −1/leftover card, −25 if the settebello is exposed; sweep-proof if an ace is on
the leftover table. (Both no-ops when the rule is off.) Verify via TESTMODE 18/19 reading BestScoreW
(`sjasmplus --sym=` dumps state addresses; BestScoreW currently 0xB0E4 but RE-DUMP, it shifts).
NOTE — the weights are **hand-tuned heuristics ported from ai.js, not optimised**; the priorities are
right but the exact integers are guesses. To optimise: build a host-side (Python) simulator of the
rules + the linear evaluator, run self-play tournaments (coordinate-ascent / small GA: candidate
weights vs current) maximising win-rate, bake the tuned small-int weights back into the Z80 tables.
The evaluator is 1-ply greedy — a bigger gain than weight-tuning would be shallow (2-ply) lookahead.

---

## 9. Card art & screens pipeline

**Deck** (convert_deck.py, RUN FROM scopa/): defined-mono = grayscale fit + FIND_EDGES
outlines + Bayer dither fills + frame. 48×64 (6×8 cells), attrs constant 0x78. Pips (value
1-7) darkthr=42/gamma=1.5; FIGURES (value 8-10) lighter darkthr=58/gamma=2.4 to de-blob.
**Coppe suit pip**: `cup_badge()` traces the 2-of-coppe goblet's silhouette BOUNDARY (= hollow
line-art, the only style that reads at ~12 px — a filled silhouette goes "mushroom", a dither
goes "cloud"); `stamp_badge()` stamps it 12×15 top-left at (2,2) with a 1px white moat (moat
starts at (1,1) so it never clips the card frame at row/col 0), applied only when suit==1 &
value>=8. Touches ONLY cards 17/18/19; verify with a byte-diff vs a no-stamp rebuild.
**Title/loading** (make_screens.py): colour per-cell 2-colour quantise of cropped card-tops
(saturation-boosted), fanned; tricolore SCOPA wordmark; black text bands; outputs SCR
(interleaved bitmap + attrs). img_to_scr / scr_to_png for encode/preview.

---

## 10. Tape (the "Bytes:" gotcha)

Multi-part `LOAD ""CODE` prints "Bytes:" over the artwork. Fix = SILENT ML LOADER:
BASIC shows SCREEN$ (art→0x4000), POKEs a 43-byte loader to the printer buffer (23296),
RANDOMIZE USR runs it: 3× ROM LD-BYTES (0x0556) of HEADERLESS blocks (code→0x8000,
title.rle→0x6000, deck→0xC000), jp 0x8000. No messages over the art; art shows throughout.
⚠️ ZEsarUX headless smartload can't instaload headerless blocks (no headers to place them)
→ tape load is only verifiable on real HW / an accurate emulator. The `.sna` (INCBIN
title+deck) is the headless test path. build_tap.py validates structure + checksums.

---

## 11. Build & test

Toolchain: `mastery/tools/sjasmplus`; ZEsarUX 13.0 + `mastery/tools/zx_shot.py` (ZRCP, port
10000); venv `zxspectrum/.venv-zx/bin/python`. ALWAYS `pkill -9 -f zesarux` after a run.

```
# regenerate art (only if references/params change):
python tools/convert_deck.py      # -> deck.bin   (RUN FROM scopa/)
python tools/make_screens.py      # -> title.scr, loading.scr
# build:
sjasmplus scopa.asm               # -> scopa.sna (test) + scopa_code.bin (tape)
python build_tap.py               # -> scopa.tap
```
`TESTMODE` builds run a scripted scenario instead of the game, for headless verify via
read_mem / screenshot. NOTE the define syntax is `-DTESTMODE=N` (the `--define=…` long form
errors "missing define value"):
- 1 scoring (ScoreRound+ShowResults)  2 last-play-no-scopa  3 capture enumeration
- 4 AI picks sweep  5 AI protects settebello  6 napola=5 + Neapolitan screen
- 7 play-card-id guard  8 full-table ShowCapture  9 slide+play guard  10 winner inspector
- 11 capture-leftmost zip (underflow case)  12 drop 6→7 + laid-card flash  13 C-major scale
- 14 second-to-last-card scopa (counts)  15 capture-choice render (played card stays in hand)
- 16 asso-piglia-tutto ace-sweep (table clears, no scopa)  17 ChoiceMade applies the chosen option
Headless input note: keys_string is lossy during AI-turn windows (the keyboard isn't
polled then) — can't auto-drive a full round. CRT is ground truth.

---

## 12. Decisions & gotchas (hard-won)

- addHLA everywhere for base+index (don't `ld bc,BASE; add hl,bc` — clobbers counters).
- ConsiderBest first-play-always-taken (signed sbc overflows vs the −32768 sentinel).
- SAVESNA filename must match the INCBIN you changed (stale .sna boots to BASIC = "black").
- convert_deck.py writes deck.bin CWD-relative — RUN FROM scopa/.
- ZEsarUX cpu-step prompt is `command@cpu-step>`; screenshot renders SCR from RAM read
  (deterministic) — reads can catch a mid-PaintAll frame (white card-shaped blocks = harmless).
- Shadow vs screen briefly differ during attr-only cursor moves — reconciled next PaintAll.

---

## 13. Open / next

- CRT play-test (Tony) = ground truth for: slide feel/smoothness, tear-free-ness, the new
  match-end screen, the compressed title, napola / palle del cane.
- DONE this session: "le palle del cane"; SCOMPACT title compression (~7 KB headroom);
  match-end screen; card-slide animation; tear-free vblank-synced save-under slide; table
  re-space zip (captures + drops) + crowded-laid-card flash; crowded-table step shrink;
  capture-flash clamp fix; **title music** (2-voice beeper, Funiculi Funicula — engine
  verified, MELODY/tempo pending Tony's ear; FunicTune + NoteInc + PlayTune/PlaySamples,
  TESTMODE 13 = scale). N/M crowded-table scroll = still deferred.
- Next memory lever if code refills: compress deck.bin (decompress-on-draw, ~30 % — dither
  limits RLE). Code now 10215 B → 2073 B free below state@0xB000.
- DONE since: title dedication + how-to-play + event jingles; scoring audit (pagat.com;
  fixed last-play scopa off-by-one); © glyph + attr-clash fix; border-after-jingle fix
  (BorderC); TrueType SCOPA!/NEAPOLITAN banners; results screen tricolore flag header +
  green winners; **coppe cup pip**; capture-choice now runs with the card **in hand**
  (no table overlap); optional **"asso piglia tutto"** rule (Scopa d'Assi, toggle, default OFF).
- Git: PRIVATE repo github.com/tonygillett136/scopa-spectrum (pushed once; not auto-synced —
  push new rounds when Tony asks).
- CRT play-test of: silent-loader tape, cursor-flash, capture-flash precision, napola,
  the three skill levels, the cup pips, the capture-choice fix.
- Deferred: N/M crowded-table scroll; border-during-jingle blip (flicker-free); raster
  Italian-flag border (blind build-and-tune, border not visible in any headless tool).
```
