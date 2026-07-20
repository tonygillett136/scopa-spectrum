# Scopa for ZX Spectrum (48K, real hardware) — DEVLOG

Recreating Angelo's lost Scopa. Decisions (Tony, 2026-06-13): colour cards
(prototype-then-decide), 48K, strictly-faithful cards (no rank indices),
1-player vs strong AI to 11. Reuse old project as SPEC only:
/Volumes/SSD1/code/scopa_spectrum (rules.js/scoring/ai.js = portable spec;
reference_cards/*.jpg = the 40 Napoletane card art references).

## M0 card-art prototype (2026-06-13)
Built tools/card_art.py + proto_build.py: card = 5x7 cells (40x56px), per-pixel
ink bitmap + per-cell attr (paper,ink,bright), exact-Spectrum-colour PNG preview,
blob export (315B/card = 280 bitmap + 35 attr). Z80 card blitter (harness_proto.asm,
BlitCard: bitmap row-walk + attr cell-copy).
KEY FINDING — colour works, design cell-aware:
- Coins (denari): yellow-on-white = poor contrast (proven). WINNER = "goldtile":
  yellow PAPER + black INK sun engraving = gold medallion, high contrast, faithful.
  Big ornate coin for the ace (3x3 cells) looks great.
- Cups (coppe): red ink on white = good contrast, clean.
- Swords/clubs: blue/green on white = fine.
- Figures (8/9/10): auto-trace SOLID fill = muddy/amateurish; WOODCUT style (flat
  colour from cell PAPER + black INK outlines only, white bg, colour only for
  strong-majority cells) reads as a clear figure. Still needs hand-finish + DITHER
  (Tony's tip: checkerboard ink for mid-tones/shading) to hit "the very best".
Rendered settebello + ace + 3-cups + Re-di-spade on the actual Spectrum
(/tmp/scopa_proto.png) on a green felt table (dither demo, currently vertical
stripes from constant byte/row — refine to checker). Pip cards crisp + faithful;
figure small-but-readable. SHOWN to Tony for the art-bar call before M1.
Tools/blob/harness in scopa/. Card size 5x7 -> 4-6 across the table, fits layout.

## M0 v2 — proper converter (the quality fix, 2026-06-13)
Tony's verdict on v1: not the bar; Ange's were "the best you could squeeze out of
the hardware, faithful"; king "barely recognisable"; wanted LARGER cards; green
felt "too in-your-face". PIVOT: replaced crude hand-trace with tools/img2spec.py =
proper per-cell best-2-colour optimiser + 8x8 Bayer ORDERED DITHER (Tony's
checkerboard tip, systematised) -> captures shading/detail = faithful. Bigger
cards 8x12 cells (64x96). + light pre-blur + aggressive white-snap (min(rgb)>175
-> pure white) to kill grey halos + reduce speckle. + frame_card() = white card,
thin black rounded border. Background -> muted NAVY (paper blue non-bright 0x08),
no stripes. Result (q4): king/knight/ace-cup clearly recognisable + faithful;
settebello coins via dither. General 8-wide BlitCard (harness_q.asm). Rendered on
real Spectrum (/tmp/scopa_q4.png) — reads as a hand of real cards. Awaiting Tony's
art-bar verdict. NB layout: at 64x96, 4 cards fill width/1 row -> can't show
opp-hand+table+player-hand all full-size; layout design needed (smaller table
cards / overlap / opp as backs). q_cards.bin = 4 cards x 864B.

## M0 v3 — STYLE LOCKED: defined monochrome (2026-06-13)
Long art-direction loop. Tony's calls: colour dither = "weak"; hand-drawn king =
clean but UNFAITHFUL (generic, not THE Re di Spade) — faithfulness to the specific
reference is paramount; light mono line-art = "lost definition" (too faint);
colour-woodcut = blocky/too-black. WINNER = DEFINED MONOCHROME (tools: defined_mono
/ convert2 settings: darkthr=42, edgethr=80 FIND_EDGES outlines, blur=0.6,
gamma=1.5, Bayer dither fills, white card + black rounded frame). Tony: "the
earlier monochrome iteration is the best I've seen so far." Renders on real Spectrum
(scopa_dm2.png): king/settebello/3-swords/ace-cup all defined + faithful + crisp.
Bug fixed: sed left SAVESNA writing harness_q.sna -> harness_dm.sna stale -> booted
to BASIC (looked black). Now correct. STYLE LOCKED = defined mono, 64x96 (8x12),
white paper/black ink (attr 0x78), trace-based (faithful) NOT hand-drawn.
NEXT: convert all 40 in this style (figures may get light hand-touch-up); then engine.

## M1 DONE + M2 started (2026-06-13)
Full deck converted (convert_deck.py): all 40 cards + lattice back, defined-mono
48x64 (6x8), deck.bin 15744B @0xC000. Pip cards crisp/countable, all 12 figures
recognisable (densest = touch-up candidates). Rendering engine BlitCard (6x8,
cardid->screen, sets white-card attrs). Layout mock (harness_game) then
STATE-DRIVEN: harness_deal.asm = InitDeck + Fisher-Yates Shuffle (ROM-walk PRNG
seeded from FRAMES) + DealRound (3/3/4) + Paint(from state). Verified on real
Spectrum: random deal renders correctly (scopa_deal.png), state @0xB000.
Cyan field (paper 0x28). NEXT M2: rules engine (findCaptures) + scoring; then M3
turn loop + input + AI + match-to-11. Memory: [[scopa-spectrum-game]].

## M2 + M3 DONE — PLAYABLE (2026-06-13)
Single source scopa.asm (~1460 lines). VERIFIED in ZEsarUX:
- M2 rules: findCaptures = single-priority then subset-sum (2^TableN masks),
  ResolvePlay capture/drop, CompactTable, scopa on sweep. Test: table[3,4]+play7
  -> captures both (subset) -> scopa, pile=[2,3,6]. Bug fixed: ld bc,BASE clobbered
  loop counters -> addHLA helper (preserves BC/DE) + Who state byte.
- M2 scoring: ScoreRound carte/denari/settebello/primiera(PRIME tbl, best-per-suit)/
  scope; match accumulate. Test 6-0 sweep; results screen renders all categories.
- M3 loop: PlayRound (player+opp alternate, redeal at hands-empty, sweep-to-last at
  deck-empty), input O/P/SPACE (drain held keys), AI v0 (capture-first else drop-low),
  match-to-11 + tie->extra round, title/results/winner screens (ROM-font printer).
- scopa.tap autostart tape (BASIC + CODE@0x8000 + deck@0xC000) loads + boots to title
  in emulator. build_tap.py. Real-HW = ground truth, pending.
NEXT: strengthen AI to "strong" (ai.js heuristics: settebello protection, best-capture,
sweep avoidance, card counting); player multi-capture choice; >6-card table layout;
figure touch-ups; beeper SFX. Memory: [[scopa-spectrum-game]].

## Phase 1 — rules correctness DONE (2026-06-13)
Validated JS spec vs real Scopa first (Tony: "don't assume the JS is correct"):
rules/scoring sound; KEY TRAP = JS suit convention (DENARI=1) differs from my deck
(DENARI=0) — port AI with MY convention, not literal JS ids.
Fixes (all verified in ZEsarUX via TESTMODE builds):
- 1a last-play exception: IsLastPlay (handP+handO+deckleft<=1) gates scopa. T2: final
  sweep captures (PPileN=3) but PScopa stays 0.
- 1b primiera needs all 4 suits else 0. T1: O pile missing a suit -> Oprim=0 (was
  wrongly >0); round 4-0, primiera correctly to P.
- 1c capture CHOICE: findCaptures -> findAllCaptures enumerates all options as
  table-index masks (Options[]/OptionN), singles take priority. T3: table 1,2,3,4 +
  play 5 -> 2 options {2,3}=mask6, {1,4}=mask9. Player picks via PlayerChooseCapture
  (O/P cycle, candidate cards flash, SPACE confirm); single option auto-applies;
  AI takes option 0 for now. CanCapture wrapper for AI scan.
Game rebuilt + scopa.tap (18692B). NEXT: Phase 2 capture feedback.

## Phases 2-4 DONE (2026-06-13, autonomous run)
PH2 capture feedback: played card lands on table + flashes with the cards it takes,
~1s pause, then sweeps to pile; live "CPU nn"/"YOU nn" pile counts; SCOPA! banner.
Removed played card from hand BEFORE ResolvePlay for clean feedback. Delay recalibrated
(~0.5s/unit): capture pause b=2, AI b=1, scopa banner b=3.
PH3 strong AI: ported ai.js aiSelectPlay -- evaluates EVERY (card x capture-option) and
each drop with the weight table (sweep+50, settebello-cap+35, 7/6/ace, denari+5,
card-count*2; settebello-drop -40, drop-7/-6/denari, sweep-risk -20, easy-capture -2),
sweep-avoidance always on (= ai.js medium). Signed-16 ScoreW. ResolvePlay .aipick uses
AIOpt. BUG FIXED: ConsiderBest sbc overflowed vs -32768 sentinel -> first play always
taken, then bounded compares. VERIFIED: T4 picks the sweep (score 81), T5 protects the
settebello (drops coppe-2 not the 7). Live 20-play game: AI out-captured 7-2, no crash.
PH4: beeper SFX (CaptureBeep on take, ScopaBeep two-tone on sweep), border kept cyan.
Final scopa.tap = 19424B, boots to title from tape; all TESTMODE 1-5 assemble.
REMAINING finesse: difficulty select (easy mistakes / hard card-counting), table layout
wrap >6 cards, dealer alternation, figure-card touch-ups. Memory: [[scopa-spectrum-game]].

## Polish round 2 (2026-06-13): bug fixes + colour art screens
BUG1 flicker on L/R: PlayerTurn repainted whole screen per cursor move -> now
attr-only (Unhighlight old / Highlight new); full PaintAll once per turn.
BUG2 flash-left-behind: after a play, cursor pointed at the now-empty slot and
HighlightCursor flashed an empty rectangle -> HighlightCursor skips empty slots +
FixCursor before post-play repaint. Verified via attr reads (empty slot=0x28 not 0xF8).
LOADING + TITLE screens: tools/make_screens.py -> COLOUR close-ups of 3 Napoletane
card-tops, fanned (per-cell 2-colour quantize of the colour reference JPGs; vivid
green/red/blue/yellow map onto bright Spectrum -> Italian feel). Tricolore SCOPA
wordmark (SC green / O white / PA red). Title: knight-cups/king-swords/ace-swords +
"PRESS SPACE TO START". Loading: king-coins/knight-swords/ace-cups + "LOADING...".
Clean black bands top+bottom for text. title.scr INCBIN @0x9200 (LDIR->0x4000 in
ShowTitle); loading.scr = tape SCREEN$ block ->0x4000, held >=3s (ld b,6 Delay) at
startup so even the instant .tap shows it. Black border for art, cyan for game
(NewMatch). scopa.tap now 5 blocks (33358B), structurally validated (all checksums OK).
NEXT finesse: difficulty select, table-wrap >6, dealer alternation, figure touch-ups.

## Polish round 3 (2026-06-13, overnight autonomous): flicker fix + finesse
FLICKER FIX (user: "whole screen cleared+redrawn, flickers a lot"): SHADOW BUFFER.
PaintAll now renders the whole frame into an off-screen buffer at 0x6000 (bitmap
0x6000-0x77FF, attrs 0x7800-0x7AFF; 0x2000-aligned so screen-interleave addressing
works by high-byte +0x20), then LDIR-copies 6912B to the live screen in one pass.
The screen never goes blank -> no cyan-flash flicker. Mechanism: ScrOfs byte (0x00
screen / 0x20 shadow) added to the high byte in BlitCard/PrintChar/HandAttrHL/
FlashTableCard; PaintAll sets 0x20 + Blit + resets 0; overlays (capture flash, scopa
banner, choice) draw straight to the now-current screen (ScrOfs=0) after the blit.
0x6000-0x7AFF is free (below code, above BASIC area). Note: LDIR blit ~2-3 frames so
a faint venetian-blind refresh remains (not a flash); fully tear-free would need
delta/HALT-sync (deferred). Verified: game renders identically, all TESTMODE 1-5 pass.
DEALER ALTERNATION: Leader byte, toggled each round in RunMatch; PlayRound leads with
player or opp accordingly. NewMatch inits Leader=0.
TABLE WRAP: PaintAll table step shrinks 5->4->3 as TableN grows (>6/==7/>=8) so big
tables stay on-screen.
DIFFICULTY: SelectDifficulty menu after title (keys 1/2/3, tricolore-coloured: cyan
title, green/white/red options). EASY=skip sweep-avoidance (EvalSafety gated off).
MEDIUM=current strong AI. HARD=+card-counting (CardCount: late-game aggression once
<16 unseen). Seen[5] 40-bit tracker (MarkSeen/ClearSeen/CountUnseen); marked at deal
(table+opp hand) + each play (ResolvePlay MarkSeen Played). Verified EASY/MEDIUM/HARD
all play without crash. scopa.tap = 33816B, 10 blocks, checksums OK.
DONE (Tony's 2 asks fully): flicker fixed; loading+title art (colour close-ups).
Remaining (note only): figure-card touch-ups; perfectly tear-free blit; difficulty
screen could be prettier. Memory: [[scopa-spectrum-game]].

## Polish round 4 (2026-06-14): loading-screen gotcha + screen polish + figures
LOADING "Bytes:" FIX (Tony: ROM overwrites art LH side on multi-part load). Pro fix =
SILENT ML LOADER. build_tap.py now: BASIC shows SCREEN$ (art@0x4000), POKEs a 43-byte
loader to the printer buffer (23296), RANDOMIZE USR runs it: 3x ROM LD-BYTES (0x0556)
of HEADERLESS blocks (code@0x8000, title@0x9200, deck@0xC000) -> NO "Bytes:" messages
over the art, then jp 0x8000. tap=34294B, structure validated (BASIC+SCREEN$ headered +
3 headerless data, all checksums OK). NOTE: ZEsarUX headless smartload can't instaload
headerless blocks (no headers to place them) -> can't auto-verify the load; standard
LD-BYTES technique, real-HW/accurate-emu only. .sna unchanged (INCBIN) for testing.
SCREEN POLISH (all verified via screenshot): difficulty menu gains gold "SCOPA" header
+ tricolore colours (cyan title/green EASY/white MEDIUM/red HARD); results screen
coloured (gold SCOPA, cyan YOU/CPU + ROUND, gold MATCH); winner screens coloured
(green YOU-WIN / red CPU-WINS) + WinJingle (ascending beeper fanfare) / LoseSound.
FIGURE TOUCH-UPS: convert_deck.py now uses lighter params (darkthr=58,gamma=2.4) for
FIGURE cards only (value>=8: ids %10 in {7,8,9}) -> breaks up the black-blob bodies of
the Re/Cavallo/Fante; the 28 pip cards + back are BYTE-IDENTICAL to the approved deck.
Backup at deck_v1_backup.bin (revertible). Comparison: tools/compare_figures.py ->
/tmp/figure_compare.png. GOTCHA: convert_deck.py writes deck.bin CWD-relative -> must
run from scopa/ (python tools/convert_deck.py), not from tools/.
Remaining note-only: perfectly tear-free blit (delta/HALT). Memory: [[scopa-spectrum-game]].

## Polish round 5 (2026-06-14): UX fixes + Neapolitan rule + dev reference
- Cursor flashes ONLY on the human's turn: HumanTurn flag (set PlayerTurn, cleared
  OppTurn/on-play); HighlightCursor early-returns if HumanTurn=0.
- Capture-flash precision: TableStep helper shared by PaintAll + FlashTableCard;
  FlashTableCard now flashes only a card's VISIBLE width (step for overlapped, 6 for
  last/played) so it never bleeds onto the card drawn on top. Fixed an old bug where
  FlashTableCard used hardcoded step 5 while PaintAll used dynamic 5/4/3.
- NEAPOLITAN (napola) rule: Napola()/NapHas() — coins A,2,3 (ids 0,1,2)=3pts, +1 per
  further consecutive coin (ids 3..9) up to 10. Added to round+match totals; results
  screen has a NEAPOLITAN line; ShowNeapolitan = big 2x "NEAPOLITAN" (PrintBig: DoubleNib
  LUT + ScreenDown) + NeapolitanSound (9-note rising scale) when either side scores it.
  Verified T6: napola=5 for coins A-5; screen renders.
- Code reached 0x91FF (1 byte under title@0x9200!) -> moved TitleScr to 0x9400 (+513B
  headroom); build_tap.py loader updated to LD-BYTES title->0x9400.
- Wrote DEVELOPMENT.md (architecture/memory-map/flow/build/gotchas — the "resume cold" ref).
- "Le palle del cane": NOT in it.wikipedia/standard sources (regional) -> asked Tony for
  the exact rule. Card-movement animation: assessed feasible (save-under sprite slide).
scopa.tap = 34723B. All TESTMODE 1-6 pass. Memory: [[scopa-spectrum-game]].

## BUGFIX + le palle del cane (2026-06-14)
CRITICAL BUG (Tony, real HW): playing a card made an ACE appear on the table instead.
Cause: the new "stop cursor flashing" line in PlayerTurn .play used `xor a` to zero
HumanTurn -- which CLOBBERED A (the card id) right before `call ResolvePlay`, so it
played id 0 (ace of denari). Fix: push af / pop af around the HumanTurn write. Verified
deterministically (TESTMODE 7): play id 23 -> table=[8,23] (was [8,0] with the bug).
LESSON: A holds the card id through .play -> never clobber it before ResolvePlay.
LE PALLE DEL CANE (en.wikipedia: all four 7s in a hand = +1 on top of primiera):
PalleDelCane() checks ids 6,16,26,36 in a pile; +1 to that player's round; "PALLE CANE"
line on the results screen. Verified T1 (P holds all four 7s -> palle=1, round 5).
scopa.tap=34826B. TESTMODE 7 = play-path card-id regression guard. Memory: [[scopa-spectrum-game]].

## Loading screen v2 + ShowCapture step fix (2026-06-14)
NEW LOADING SCREEN (Tony): full-bleed close-up of 09_Nove_di_denari (knight of coins
holding the sun-disc), NOT framed as a card, + elegant bright-yellow Bodoni "SCOPA" on a
black plate with tricolore underline. make_screens.py horseman_loading(): crop top ~50%,
saturation 1.28, fill screen. ATTR CLEANUP (per Tony's pixel notes): despeckle() conforms
isolated anomalous cells to neighbour-mode (fixes 3 bright squares on horse head + yellow
eye cell, preserves white bg + turban); fix_mane_specks() kills isolated bright-white specks
in the mane (bw<3 neighbours); fix_white_bright() forces title "PRESS SPACE" all bright white.
SCOPA fill = (255,255,0) bright yellow.
BUG (Tony): on a full table the played card "seems underneath". Root cause: ShowCapture
computed the played-card column with hardcoded step 5 while the table + FlashTableCard use
the dynamic TableStep (5/4/3) -> on a full table the played card was drawn at one place but
its FLASH highlighted a different (table) cell. Fixed: ShowCapture now uses TableStep. The
deeper crammed-full-table presentation -> to be improved with the slide animation.
TESTMODE 8 = full-table ShowCapture inspector. scopa.tap=34830B, all T1-8 pass.
NEXT: card-slide animation (also reworks the full-table capture presentation). Memory: [[scopa-spectrum-game]].

## Card-slide animation (2026-06-14)
Split PaintAll -> RenderShadow (build frame in shadow, no blit) + Blit, so the slide can
reuse the render. SlideIn: slides (Played) from its hand slot to its table slot -- row
steps +-2 per frame (player 16->8, CPU 0->8), column interpolated in 8.8 fixed point
(Delta6 = delta<<6 = 1/4 per step). Each step: RenderShadow + BlitCard(moving card) + Blit
-> the card travels over the live board (~5 frames, brisk). Helpers HandCol (6+7*slot),
TableSlotCol (1+TableStep*idx clamped). Hooked in PlayerTurn .play + OppTurn before
ResolvePlay; capture path then aligns (ShowCapture draws the played card at the SAME table
slot the slide ends on -> no jump). For a CPU play the back-faced card slides down and
reveals its face. VERIFIED: T9 (slide+play -> table=[8,23], resolves correctly), all
TESTMODE 1-9 pass, live game stable (SP healthy, no crash). Visual motion = CRT-only
(temporal + lossy headless input). Speed tunable (row step / frame count) per Tony's feel.
CODE NOW 4914B, ceiling = title @0x9400 (5120B) -> ~200B headroom. Next sizeable feature
needs a memory reshuffle (relocate state below the stack to lift the title). TESTMODE 9 =
slide+play guard. scopa.tap=35029B. Memory: [[scopa-spectrum-game]].

## Slide 2x faster + SCOMPACT title compression + match-end screen (2026-06-14 pm)
SLIDE: row step +-2 -> +-4 (5 frames -> 3: player 16,12,8 / CPU 0,4,8); column interp
shift <<6 -> <<7 (Delta6 renamed SlideDelta, half the travel per step since 2 intervals
now). ~1.7x faster. T9 still lands table=[8,23].

SCOMPACT TITLE COMPRESSION (Angelo's RLE technique): make_screens.py rle_compress
(control byte: bit7=run of (c&7F) of next byte, else literal of c bytes; expands to
exactly 6912). title.scr 6912 -> title.rle 4646 (67%). Z80 DecompressScr (HL=src ->
0x4000, stops when DE hits 0x5B00). KEY TRICK: title.rle is INCBIN'd at 0x6000 -- INSIDE
the shadow-buffer region. ShowTitle expands it to the screen at boot; the first gameplay
RenderShadow then reuses 0x6000 as the shadow (the compressed title is transient, consumed
once). So the title VANISHES from 0x9400 -> code now grows freely to the state block
@0xB000. HEADROOM ~200B -> ~7.1KB. No state move, no BlitCard change. Verified: title
decompresses pixel-clean, gameplay board renders clean over the consumed region, SP healthy.
build_tap.py ships title.rle to 0x6000. tap 35029 -> 33012B.

MATCH-END SCREEN (Tony request "more exciting + press space to play again"): rewrote
ShowWinYou/ShowWinOpp. Big 2x title (PrintBigStr "YOU WIN" green / "CPU WINS" red),
subtitle (- CAMPIONE! - gold / BETTER LUCK NEXT TIME), shared ShowScoreAndPrompt (FINAL
SCORE + YOU n CPU n + "PRESS SPACE TO PLAY AGAIN"). Player win gets WaitWinner = tricolore
border shimmer (green/white/red, TriCol tbl, ~0.2s/step) until SPACE; loss gets plain
WaitSpace. (Space already looped to RunMatch; now signposted.) TESTMODE 10 = winner-screen
inspector. Both screens verified in ALE/ZEsarUX. Memory: [[scopa-spectrum-game]].

## Tear-free vblank-synced slide + save-under (2026-06-14 eve)
GOAL (Tony): no tearing during the animated bits; fold in slide smoothness.
FINDINGS: cursor + capture "flashes" use HARDWARE FLASH (attr bit7, 0xF8) -- already
tear-free; the visible tearing was always the full-screen Blit (2 frames @ 21T/byte =
~145kT, ~10x too big for the ~14.3kT blanking window -> can't ever vsync a full blit).
A SINGLE card region (~430B, ~10kT) DOES fit and, written top-to-bottom after HALT,
finishes ahead of the raster (14.3kT head start + we write ~1250T/cell-row vs the beam's
1792T/cell-row, so we stay ahead) -> genuinely tear-free.

INTERRUPTS: game ran with IRQs OFF (di at Start) so HALT would hang. Enabled im1/ei at
Start + ld iy,0x5C3A (ROM ISR needs it). GOTCHA: Shuffle hijacks IY for the Fisher-Yates
swap -> bracketed it di...ei AND restored iy=0x5C3A on exit (else the next ROM ISR
corrupts). ROM ISR (~2-3kT keyboard scan) eats into the head start but margin holds.

CHANGES: (1) Blit: HALT first -> wholesale redraws (PaintAll/ShowCapture/PaintChoice)
start at frame top = STABLE seam not a shimmer. (2) SlideIn rewritten: RenderShadow ONCE
(static board, card removed), then per step HALT + EraseCardRegion(prevcell) [restore
6x8 footprint from shadow 0x6000->screen 0x4000] + BlitCard(newcell). 8 cell-row steps
(SlRowStep +-1, was +-4) = smooth 8px travel; SlideDelta <<5 (was <<7) for 8 col
intervals. New state SlPrevCol/SlPrevRow. (3) New routine EraseCardRegion (mirrors
BlitCard addressing, copies shadow->screen). VERIFIED: all modes build, T9 table=[8,23],
live game FRAMES counting (IRQs firing) + SP healthy + clean board post-play, no crash.
Tear-free + smoothness = CRT-confirm. code 5315B (~7KB headroom). tap 33165B.
Memory: [[scopa-spectrum-game]].

## Table re-space zip (captures + drops) + crowded-laid-card clarity (2026-06-14 late)
Tony: (a) after a capture, zip the survivors to their compacted slots; (b) on a FULL table
the laid card is "obscured" / unclear.
ROOT of (b): heavy overlap (step 3-4) + TableStep changing at 6<->7 (5/4) and 7<->8 (4/3)
made the whole row SNAP to new columns when a card was added, and the laid card just merged
into the dense strip with no cue.

UNIFIED FIX (one routine animates every table re-layout):
- ZipCompact: slides Table[0..TableN-1] from ZipCur[] (current columns) to 1+newstep*k, a
  few columns/frame. BIDIRECTIONAL (cards move LEFT when the table shrinks AND RIGHT when a
  smaller count widens the step). HideTable flag makes RenderShadow skip its own table loop;
  DrawZipCards draws the cards at ZipCur instead (skips cols >=27, matching RenderShadow).
  Each frame = HideTable render + DrawZipCards + Blit(halt). Speed 4 col/frame.
- CAPTURE path: CaptureZipOld records survivors' OLD columns (CapSel==0) -> CompactTable ->
  ZipCompact. Survivors slide into the gaps.
- DROP path rewritten: FillZipCols records existing cards' columns + ZipCur[oldN] = the
  slide's landing column, add card, ZipCompact -> existing cards make room and the new one
  settles (no snap). If TableN>=7 after the drop, FlashTableCard the laid card + brief Delay
  so it's unmistakable on a crowded table. (Covers the CPU's drops too -> you see its card.)
New state: ZipCur[16], ZipStep, HideTable. New routines: CaptureZipOld, ZipCompact,
DrawZipCards, FillZipCols. TESTMODE 11 (capture-middle zip -> [0,2,3]), 12 (drop 6->7 + flash
-> [4..9,0]). VERIFIED: all 13 modes build, T11/T12 resolve correctly, live game stable
(SP ok, FRAMES counting), clean board. NOTE: >=10 cards still exceed the 32-col row (cols
>=27 not drawn) -- a fundamental 1-row layout limit, same as before, rare. zip motion = CRT.
code 5591B (~6.7KB headroom). tap 33441B. Memory: [[scopa-spectrum-game]].

## BUGFIX: ZipCompact underflow hang (2026-06-14, Tony CRT report)
Symptom: after a capture the game HUNG and "a card was randomly moving around the
background". Cause: in ZipCompact's move-left branch, `sub 4` on a card already within 4
columns of a small target (e.g. col 2/3 heading to col 1) UNDERFLOWED to ~254; the
following `cp d` then read the wrapped value as ">= target" and set it -> the card never
settled, swept right-to-left across the screen (drawn whenever its column dropped < 27),
and looped forever. Triggered by capturing a LEFT-side table card (a survivor zips to
col 1). FIX: compute the DISTANCE first (sub target / sub cur), snap to target when within
one step (<5), else move 4 -- never underflows. Plus a safety FRAME CAP (ZipFrames, exits
after 48 frames) so a stuck zip can never hard-hang again. VERIFIED: T11 changed to capture
the LEFTMOST card (the exact bug case) -> settles in 2 frames (not the cap), Table=[1,2,3],
no sweeper; live game ran 24 turns (deckpos 22, multiple redeals) with no hang. tap rebuilt.

## Crowded-table shrink + capture-flash alignment fix (2026-06-14 night)
(1) FLASH BUG (Tony "rare, over in a flash"): on a crowded table the played card's column
1+step*TableN exceeds 26, so ShowCapture CLAMPS the drawn card to col 26 -- but
FlashTableCard recomputed the column WITHOUT the clamp (e.g. 29) then clipped the width, so
the flash landed on a 3-col sliver at the card's right edge, off the card. Fix: FlashTableCard
clamps col to 26 too. Verified via attr-row read (T8): played card now flashes cols 26-31
(full), captured card 9-12. (2) CROWDED SHRINK (Tony approved over the N/M scroll, for now):
TableStep gains tiers -> <=6:5, 7:4, 8-9:3, >=10:2, so all cards stay visible up to ~13.
The full N/M scroll (off-screen cards stacked + arrows + hint) is DEFERRED -- revisit only if
a real game overflows ~13. tap rebuilt. NEXT: title-screen music (Funiculi Funicula).

## Title-screen music: 2-channel beeper, Funiculi Funicula (2026-06-15)
Tony: "make it sound awesome, wow factor." Built a 2-voice phase-accumulator beeper engine:
melody acc/inc in the MAIN HL/BC, bass in the ALTERNATE HL'/BC' (exx), duration in DE; per
sample add both, XOR the two top bits -> speaker bit4. Loop = exactly 94 T -> 37234 Hz sample
rate; inc = freq*65536/37234 (~freq*1.76). So C4(inc 460)=261 Hz by construction. NoteInc
table idx0=rest,1=C3..37=C6. PlayTune sequencer: frames of (melodyIdx,bassIdx,ticks,...0xFF),
tick=1800 samples ~48ms; sets Inc1/Inc2 per note, accs persist (no clicks), polls SPACE each
tick to skip. PlayTitleMusic: di -> play -> speaker low -> drain SPACE -> ei. Hooked in
ShowTitle after DecompressScr; A=1 skipped (-> game) / 0 finished (-> WaitSpace).
INTERRUPTS OFF during play (timing) is the key gotcha -> ei MUST restore them or the game
hangs at the next Blit halt. VERIFIED: (engine) captured aofile + zero-crossing analysis ->
clean ASCENDING scale (TESTMODE 13, pure tones); (integration) FRAMES frozen during music then
advancing after BOTH skip and natural-finish paths -> interrupts restored, board renders, game
plays, SP healthy, no hang. CAN'T audition headless -> MELODY NOTES (reconstruction, not web-
sourceable) + TEMPO + timbre are for Tony's ear; all trivially editable (FunicTune data /
tick size / inc multiplier for octave). TESTMODE 13 = scale pitch-check. code 6012B (~6.3KB
headroom). tap 33862B. Memory: [[scopa-spectrum-game]].

## Title music v3: 2-voice time-division bass (2026-06-15)
Tony: v2 single voice "sounds quite good" -> add a bass for richness. Method = TIME-DIVISION
(not XOR): each sample loop outputs the melody bit THEN the bass bit to the speaker -> two
PURE square waves interleaved, no intermodulation/dial-tone. Melody main HL/BC, bass alt
HL'/BC'. Loop 124T -> 28226 Hz/voice; NoteInc recomputed *2.3219 (C4 inc=608); tick 5500->3150
to keep the v2 tempo. Bass line was already in FunicTune (C3/G3 oom-pah). Integration verified
(FRAMES advancing after the music, no hang). REVERT path noted in PlaySamples comment (single
voice: drop the exx/bass half = 71T, NoteInc *1.3294, tick 5500). Sound = Tony's ear. tap 33869B.

## Title music v3 APPROVED (2026-06-15)
Tony: "That's awesome! Let's stick with that." -> 2-voice time-division title music LOCKED.
The game is now feature-complete and heavily polished. Remaining = full CRT play-test +
optional finishing touches (how-to-play/controls screen; a dedication/credit to Angelo as the
original creator; final card-art faithfulness pass). Deferred: N/M crowded-table scroll.

## Title dedication + how-to-play + event jingles + SCORING AUDIT (2026-06-15)
- TITLE: smaller card fan -> bottom credits block "Based on an original ZX Spectrum game by
  Angelo Colucci / (C) Tony Gillett 2026 / SPACE = START   H = HOW TO PLAY" (make_screens.py).
- HOW-TO-PLAY: H key (polled during the music AND the title wait, PlayTune returns 2) ->
  ShowHowToPlay (rules + controls, PrintLines table) -> SPACE back. title.rle 4773B@0x6000.
- JINGLES: PlayJingle (di/play/ei, reuses PlayTune+the 2-voice engine). ScopaJingle (rising
  arpeggio), CaptureJingle (2-note), WinTune (fanfare), LoseTune (chromatic sag). Replaced
  CaptureBeep/ScopaBeep/WinJingle/LoseSound calls. Verified live: no hang (IRQs restored).
- SCORING AUDIT (Tony: "be 100% correct"; researched INDEPENDENTLY via pagat.com, NOT the JS):
  VERIFIED CORRECT: carte/denari/settebello (1pt, ties=0), primiera (7=21 6=18 A=16 5=15 4=14
  3=13 2=12 face=10; needs all 4 suits; best-per-suit sum; tie=0), scope (1 each), single-card
  capture priority, end-of-deal sweep to last-capturer (not a scopa), match to 11.
  *** BUG FOUND + FIXED: last-play scopa exception off-by-one. *** Pagat: a scopa is void ONLY
  on the very last card of the deal (nothing left after). My IsLastPlay used `cp 2` (total-after
  < 2) which ALSO voided a clear on the SECOND-to-last card (opponent still holds one) -- a
  VALID scopa. Root: ported only JS isLastPlay()=(total<=1), dropped its `&& oppHand==0 &&
  deck==0`. Fix: void only when total-after==0. TESTMODE 2 (last card->no scopa, was masking
  the bug via card-not-removed setup) FIXED + new TESTMODE 14 (2nd-to-last->scopa): both pass
  (T2 PScopa=0, T14 PScopa=1). code ~6.7KB. tap rebuilt. Memory: [[scopa-spectrum-game]].

## Project complete (2026-06-15)
Scopa for the 48K ZX Spectrum is feature-complete, polished, and scoring-audited against
authoritative sources. Built in ~a day of collaborative sessions (Tony + Claude). Title
dedication to Angelo Colucci + (C) Tony Gillett 2026. Remaining: Tony's full CRT play-test.
Wrote ARTICLE.md — a Medium piece on how the game was made (retro + AI audience).

## Title polish + border fix + bigger SCOPA banner (2026-06-15)
- TITLE: (C) -> real © glyph; credit lines re-laid so the GREY block (rows 18-21) and the
  WHITE key line (rows 22-23) never share an 8px colour cell (no attribute clash).
- BORDER BUG (Tony: "border goes black after the first turn"): the music/jingle speaker
  writes to port 254 zero the border bits (black) and left it black. Fix: BorderC byte tracks
  the current border (0 boot/title/win, 5 cyan gameplay -- set at the existing out 254 sites);
  PlayJingle + PlayTitleMusic restore (BorderC) instead of black. (Border still blips black
  DURING a jingle's samples -> noted; flicker-free would need the border in the sample loop.)
- BIG SCOPA BANNER (Tony: bigger, TrueType not ROM font): make_screens.scopa_banner() renders
  "SCOPA!" in Arial Black 26px -> scopa_banner.bin (1024 bitmap + 128 attr, gold on black).
  BlitBanner stamps it over char-rows 9-12. ShowScopa now blits the banner (was ROM PrintStr).
  Verified in-game via T14 -> bold gold SCOPA!.
- NAPOLA vs SCOPA (Tony saw NEAPOLITAN when CPU took last table card): NOT a bug -- end-of-deal
  sweep to last-capturer is correctly NOT a scopa (pagat); the NEAPOLITAN is the separate napola
  bonus (CPU held A-2-3 coins), scored at round end. Explained.
code 7833B (~4.5KB headroom). tap rebuilt.

## NEAPOLITAN banner matches SCOPA (2026-06-15)
Refactored make_screens scopa_banner -> generic make_banner(name,text,fontsize); generates
scopa_banner.bin (SCOPA! 26px) + neapolitan_banner.bin (NEAPOLITAN auto-fit font 34), both gold
Arial Black on black. BlitBanner now takes HL=source. ShowNeapolitan blits NeapolitanBanner
(was PrintBigStr doubled-ROM). StrNapola kept (still the results-screen label). T6 verified.
code 8967B (~3.3KB headroom). tap 36710B.

## Results screen glow-up (2026-06-15)
BlitBanner now takes A=top char-row (computes screen+attr addr). ShowResults: SCOPA! banner
header at row 0 (was spaced ROM "S C O P A"). HighlightWinners + SetCellAttr: per category
(CatWin 0..4, rows 6/8/10/12/14) the winning side number -> bright green; ties stay white.
Kept ROM font for the dense body (small TrueType quantises worse). Tony agreed.
PENDING (Tony want): ITALIAN FLAG BORDER on results = multicolour-border raster (vertical
green/white/red needs mid-scanline OUT 254 + contention timing) -> classic but timing-critical
AND I cannot see the border in any headless tool -> build-and-tune-on-hardware effort. Offered.

## Italian tricolore on the scores screen (2026-06-15)
Tony chose option B (verifiable flag) over the blind raster border. make_banner gains flag=True
-> per-cell paper green(0x60)/white(0x78)/red(0x50) thirds, BLACK ink -> "SCOPA" letters over an
Italian flag band. scopa_flag.bin (no "!"), INCBIN. ShowResults header now uses ScopaFlag at row 0
(in-game scopa event keeps the gold scopa_banner). Verified via T1 screenshot -- green|white|red
band + black SCOPA + green winner numbers. (Aside: --vofile DOES dump video but format = grayscale
power-of-2-padded raster that doesnt decode cleanly -> still cannot see the BORDER headless, which
is why the raster flag-border was declined.) code ~9.1KB. tap rebuilt.

## Coppe suit pip on figure cards (2026-06-15)
Problem: figure cards (Fante/Cavallo/Re) don't clearly show suit -- esp. coppe (cups) & denari
(coins); swords/bastoni read fine (figure holds the weapon/club). FIRST attempt (crude geometric
cup/coin/sword/club icons) REJECTED by Tony as "primitive, spoil the aesthetic". Pivoted to
extracting the REAL reference symbols. Tony's elimination insight: if swords+bastoni+cups are each
identifiable, an unclear figure can ONLY be denari -> so badge COPPE ONLY, leave denari as-is.
Solution (convert_deck.py): cup_badge() traces the two-handled goblet OUTLINE from 12_Due_di_coppe
(silhouette boundary = hollow line-art so the open bowl/handles/stem/foot read; a FILLED silhouette
went "mushroom", a dithered one went "cloud/bush" -- at 48x64 a corner pip is ~12px so detail must
be LINE not fill/dither). 12x15, stamped top-left at (2,2) with 1px white moat (moat starts at (1,1)
so the card frame at row/col 0 is never touched). stamp_badge() applied only when suit==1 & value>=8.
Verified byte-diff: ONLY cards 17/18/19 changed vs no-stamp deck; back + all else identical.
deck.bin 15744B (size unchanged). tap 37953B rebuilt. deck_v1_backup.bin still the revertible
original. PENDING Tony CRT test.

## Played card invisible during capture-choice -- FIXED (2026-06-15)
Tony (CRT): played a 7 onto two table 7s, got the choose-which-to-take prompt, but his played
card "wasn't visible -- not on the table or in hand." CONFIRMED real (visual only; capture logic
was always correct). Cause: PlayerTurn removes the played card from the hand (scopa.asm:569) and
SlideIn slides it to the table slot, but a CAPTURING card is never added to Table[] (it goes
straight to the pile with what it takes) -> during PlayerChooseCapture, PaintChoice->PaintAll
repaints purely from game state and the card is in NEITHER hand NOR Table[] -> it vanishes until
ShowCapture redraws it after SPACE. FIX: factored the played-card draw out of ShowCapture into
DrawPlayedCard (draws Played at col 1+step*TableN clamped 26, row 8 -- exactly where the slide
left it AND where ShowCapture uses it) and called it from PaintChoice too, so the card stays put
& steady slide->choose->capture. The flashing candidates are the table 7s; the played card sits
solid alongside. Net +7 bytes (refactor ~neutral). VERIFIED headless: new regression TESTMODE 15
(two 7s + a spare on table, play a 7, render the choice) -> screenshot shows all 4 cards incl. the
played 7 of spade at the 4th slot (was absent before). TESTMODE 15 is conditional-asm = 0 bytes in
ship build. code 10215B (2073B free). tap 37960B.

## Asso piglia tutto (optional rule) + card-in-hand capture choice (2026-06-15)
Ange (with Tony) raised two things. Researched the variation independently (pagat.com authoritative):
**"Asso piglia tutto"** = an ace captures the WHOLE table, UNLESS an ace is already on the table
(then it takes only that ace); an ace on an empty table just drops. Two scoring sub-variants:
asso-piglia-tutto (sweep = scopa) vs **Scopa d'Assi (sweep is NOT a scopa)**. Tony/Ange chose
**Scopa d'Assi**, default OFF, toggle on the skill screen.
(1) RULE: new state AceRule (0 off, boot-init off). findAllCaptures: if AceRule & played value==1 &
no ace on the table & table non-empty -> single option = full-table mask (all bits) + set AceSweepOpt.
ResolvePlay scopa block: if AceSweepOpt, skip the scopa (Scopa d'Assi). The "ace present -> takes the
ace" and "empty -> drop" cases need NO new code (already the engine's behaviour). AI is automatic (it
scores plays via findAllCaptures, so it values the sweep). TESTMODE 16 verifies: ace sweeps 3 non-ace
cards -> TableN=0, PPileN=4, PScopa=0. UI: SelectDifficulty gains key 4 toggling "ASSO PIGLIA TUTTO
OFF/ON" (white/green) + subtitle "(ACE TAKES WHOLE TABLE)"; debounced; AceRule reset OFF each menu.
Screenshotted OFF+ON.
(2) CAPTURE CHOICE NOW HAPPENS WITH THE CARD IN HAND (Ange: on a full table the played card, drawn at
the clamped table slot, overlapped a table card you were studying). Reordered PlayerTurn .play: keep
the card in the hand, findAllCaptures, and if multi-option run PlayerChooseCapture BEFORE removing/
sliding -> store ChoiceVal + ChoiceMade=1; only THEN remove from hand + slide + ResolvePlay (which uses
ChoiceMade/ChoiceVal instead of re-prompting). PaintChoice now HighlightCursor (flash the in-hand card)
instead of DrawPlayedCard -> the played card sits in the HAND row, structurally can't overlap the table
row; candidate table cards flash in sync with the hand card. DrawPlayedCard kept for ShowCapture
(post-confirm). TESTMODE 15 repurposed (card-in-hand render, screenshot verified); TESTMODE 17 verifies
the ChoiceMade path captures the CHOSEN option (pick option 1 of two 7s -> 7 coppe taken, 7 denari
left). code 10501B (1787B free). tap 38244B. PENDING Tony+Ange CRT test.

## AI accuracy under asso piglia tutto (2026-06-15)
Tony+Ange asked to tighten the two AI rough edges flagged for the ace-takes-all rule (and asked
whether the weights are optimal -- they're hand-tuned heuristics ported from ai.js, NOT optimised;
discussed self-play tuning as the route to optimise them).
FIX #1 (offence): EvalCapture credited +50 SWEEP whenever the table cleared -- including an ace-sweep,
which under Scopa d'Assi is NOT a scopa. Now: if AceSweepOpt set, skip the +50 (the sweep still scores
the whole table's card/coin/primiera value, just no scopa). TESTMODE 18 (ace sweeps 5d/7c/10d ->
BestScoreW=44, was 94) PASS.
FIX #2 (defence): EvalSafety now penalises leaving an ace-LESS table when AceRule on (the opponent
could ace-sweep it): -1 per leftover card, -25 extra if the settebello is exposed; skipped if an ace
is already on the leftover table (sweep-proof). Applies on MEDIUM/HARD (EASY skips all safety).
TESTMODE 19 (capture leaving [settebello,7c] -> BestScoreW=-20, the -27 ace-guard applied) PASS.
Both only affect play when AceRule is ON (off = default = unchanged). code 10564B (1724B free).
tap 38308B. PENDING Tony+Ange CRT test.

## AI weight self-play tuning + 2-ply experiment (2026-06-15)
Tony+Ange asked to optimise the (hand-tuned, ported-from-ai.js) weights and to "shoot for" 2-ply.
Built tools/ai_tune.py: a faithful host-side Python sim of the rules+scoring + the EXACT 1-ply
evaluator (validated: reproduces the Z80 TESTMODE 18/19 scores precisely; W0-vs-W0 mirror = 0.485).
OPTIMISER = coordinate ascent with common-random-numbers (paired decks per candidate) + re-baselining
(iterated hill-climb), candidate-vs-current over hundreds of matches/eval. Ran twice with independent
seeds; kept ONLY the changes that reproduced in BOTH runs (signal vs noise) -> CONSENSUS, 6 changes:
  card_count 2->3, seven 15->12, drop_7 -12->-5, drop_6 -6->-5, leave_sweep_risk -20->-9,
  leave_easy_capture -2->-5.
(Discarded noisy per-run picks: six->-2 [run2 said 7], sweep->26, settebello->51, ace, drop_face.)
VALIDATION (12k matches): consensus vs current = 0.541; vs random 0.889 (current 0.878) -> genuinely
+ generally stronger, not overfit. The consensus matches the noisy full set in strength (run1-vs-
consensus 0.503) but is simpler/justified. BAKED into scopa.asm (card_count now *3 via add a,a/add a,c;
the four ld de constants); TESTMODE 18 now 45 (was 44), 19 now -21 (was -20) -- both re-verified PASS,
Z80 == Python.
2-PLY: implemented a "paranoid" lookahead (immediate gain minus discount*opponent's best reply to the
resulting table). Result: with OLD weights marginal (0.522 at discount 0.3, worse above); with the
TUNED weights it adds ~NOTHING (0.50-0.507, within noise) AND is ~4x slower/move. Conclusion: a
well-tuned 1-ply reactive heuristic already captures the cheap-lookahead value; worst-case lookahead is
too pessimistic under hidden info. NOT implemented on the Z80 (a proper Monte-Carlo lookahead might do
better but is far too heavy for 3.5MHz). code 10565B (1723B free); tap 38309B. PENDING Tony+Ange CRT.

## TZX tape (2026-06-16)
Tony asked for a .tzx. build_tzx.py wraps scopa.tap into a TZX (ZXTape! v1.20): each TAP block ->
a Standard-Speed Data Block (ID 0x10) with byte-identical [flag][data][checksum] (loads exactly as
the .tap on real HW), plus an Archive Info block (ID 0x32): title "Scopa", author "Tony Gillett",
year 2026, type "Card game", comment crediting Angelo. Verified: parse round-trips, the 7 data blocks
are byte-identical to the tap. scopa.tzx 38489B (tap 38309B + ~180B TZX/metadata overhead). Like the
tap, headerless-block instaload isn't headless-verifiable -> CRT/accurate-emu test (equivalent to the
already-trusted tap by block-equality).

## Denari figure coins — clearly-round medallions (2026-06-16)
Tony/Ange feedback: the three denari FIGURE cards (Fante/Cavallo/Re = ids 7/8/9) didn't read as
the coin suit. Root cause: placed faithfully the held coin renders only ~7px across and the Bayer
dither mushes it into the body. Iterated with Tony on prototypes (NOT baked until approved):
  1. shrunk corner suit-pip badge  -> rejected (looked like a redaction box);
  2. in-place hollow ring redraw    -> rejected ("worse");
  3. faithful enlarge-in-place      -> Tony: "better", chose 1.5x;
  4. clearly-ROUND checker medallion (clean outline + checker interior + centre boss + 1px white
     gap to the figure) at 1.5x     -> APPROVED (V2).
The Cavallo's reference pose crowds the coin against the head, so we also RELOCATE its coin up-and-
out (dx,dy in source px) to match the traditional "held aloft" composition before drawing the
medallion. convert_deck.py: COIN{} table (per-figure cx,cy,r,scale,dx,dy), place_coin() (moves/
enlarges the coin disc in the SOURCE, circular mask, neighbours untouched), medallion() (draws the
clean round coin onto the final bitmap), and dm() refactored to accept a path OR a PIL image +
return the fit transform so the coin lands exactly. deck.bin regenerated (md5 d1ddb99…); CODE
UNCHANGED (10565B) — art lives entirely in deck.bin. Coppe cup-pip + all other cards untouched.
Verified in the real engine via new TESTMODE 20 (denari-figure gallery -> PaintAll): all three coins
read as clean round medallions on the cyan table (ZEsarUX). tap 38309B / tzx 38489B rebuilt. PENDING
Tony CRT.

## Web showcase site + Cloudflare Pages (2026-06-16)
Built a static showcase site (site/) and deployed to Cloudflare Pages project "scopa-spectrum"
(https://scopa-spectrum.pages.dev). Stunning Italian/Neapolitan theme (tricolore + cyan felt +
Cinzel headings, self-hosted). Sections: hero (loading screen), in-browser PLAY, screenshots
(title/gameplay/results/howto - captured from ZEsarUX via the new matrix-input method, see
[[zesarux-live-keyboard-input]]), faithful-deck showcase (hero strip + 40-card grid rendered from
deck.bin), features, downloads (.tzx + .tap), story. In-browser emulator = JSSpeccy 3.2 (GPL, vendored
in emu/), loads scopa.sna via openUrl (snapshot = instant title, no tape-loader risk).
KEY GOTCHA: JSSpeccy needs SharedArrayBuffer -> the site MUST send COOP:same-origin + COEP:require-corp
(site/_headers) or the emulator core silently won't run (blank screen). require-corp then blocks
cross-origin Google Fonts -> SELF-HOSTED Cinzel (fonts/). Verified on the live site: COOP/COEP present
on all responses, .wasm = application/wasm, crossOriginIsolated=true. CAVEAT: JSSpeccy renders to a
WebGL canvas that headless Chromium can't screenshot (reads back all-black) -> could NOT visually verify
the in-browser game headlessly; needs a real-browser play-test (Tony). Custom domain
scopa-spectrum.gillett-projects.com NOT yet set (wrangler has no pages-domain command -> dashboard or API).

## Two rotating title screens (2026-06-17)
Tony found the 3-card-fan title weak; loved the loading screen. Built five new title concepts
(title_prototypes/), he picked ACE OF SWORDS, then asked for a 2-screen random rotation (Ace of
Swords + Ace of Coins eagle). make_screens.py now renders TWO full-bleed card-hero titles (Bodoni-
yellow SCOPA + tricolore + the full Angelo dedication + SPACE/H line) through img_to_scr: title_sword()
(SCOPA top, gold crowned hilt hero, dedication bottom) -> title.rle 4061B; title_eagle() (full wings,
SCOPA inside the coin the eagle frames, dedication bottom) -> title2.rle 3949B. Both parked at 0x6000
(TitleRle 0x6000, Title2Rle 0x6FDD, ends 0x7F4A < 0x8000 -- the region doubles as the gameplay shadow
buffer so it's free at the title; combined 8010B of the 8192B budget). scopa.asm: new CurTitle word +
PickTitle (entropy = Seed^Seed+1^R, one bit) -> ShowTitle picks one at boot, stores CurTitle, the H/help
path redraws CurTitle (same screen). build_tap.py loads BOTH title.rle and title2.rle (the .sna had both
via full-RAM save, but the tape needed the extra ldbytes/block). VERIFIED in ZEsarUX: both titles render
pixel-clean (forced each via and-0/and-1), H->how-to->SPACE returns to the same title. code 10590B
(1698B free). tap 41930B / tzx 42113B (8 blocks). PENDING Tony CRT. (Note: in-browser JSSpeccy still
shows grey -- separate issue, .z80 route next.)

## In-browser emulator -> .z80 snapshots (2026-06-17)
JSSpeccy showed a blank/grey screen for BOTH the .sna and the tape (.tzx) in real browsers (Tony
confirmed). The .sna's screen RAM is blank at load, so JSSpeccy had to RUN our boot code to draw the
title -- and something in that path doesn't replay (the custom silent multi-stage tape loader likewise
doesn't trap-load cleanly). FIX: ship ZEsarUX-exported **.z80 snapshots captured AT the title** -- the
title is already in screen RAM, so JSSpeccy displays it the instant it restores (no reliance on our boot
code). Two snapshots (scopa.z80 = eagle, scopa2.z80 = sword, forced via PickTitle and-0/and-1) keep the
title rotation in-browser via `openUrl: Math.random()<0.5 ? 'scopa.z80' : 'scopa2.z80'`. site/_headers
COOP/COEP still required (SharedArrayBuffer). The .tzx/.tap downloads remain for real hardware. CAVEAT:
a snapshot freezes the boot RNG seed -> the first deal repeats per page-load (minor, web-demo only).
HEADLESS-VERIFY LIMIT: after the play-button click JSSpeccy's WebGL canvas reads back transparent in
headless Chromium -> can't self-verify post-click; relying on the in-RAM-title guarantee + Tony's test.

## In-browser keyboard fixed -> emulator fully working (2026-06-17, Tony-confirmed)
Two layers: (1) JSSpeccy listens for keys on its own injected <div tabindex=0>, not the document
-> the page re-focuses it on click (host mouseup/touchend -> querySelector('[tabindex]').focus();
verified document.activeElement lands on it, and keydowns are defaultPrevented = handled). (2) The
.z80 snapshots had been captured MID-TITLE-MUSIC (a tight interrupts-off loop that never acts on the
matrix) -> recaptured both at the post-music WaitSpace key-poll loop (PC at ROM ISR 0x38 = interrupts
on). Verified end-to-end in ZEsarUX from the captured state: SPACE->difficulty->'3' deals a hand
(TableN 0->4). Diagnosed despite JSSpeccy's WebGL canvas being unscreenshottable in headless Chromium
by checking each layer independently (DOM focus + keydown defaultPrevented; emulated state via ZEsarUX
read_mem). Trade-off: no title music in the browser build (plays before the capture point; intact on
the real-hardware tape/sna). Full reusable write-up in the JSSpeccy-embed reference memory. SITE DONE.

## Hidden SHIFT+SPACE -> title menu (2026-06-17)
At the end-of-match "PRESS SPACE TO PLAY AGAIN" prompt, holding CAPS SHIFT while pressing SPACE now
returns to the title menu (re-pick difficulty / asso-piglia-tutto), instead of replaying at the same
settings. Undocumented in the UI (Tony's call). Impl: the two win paths (.maybe opp-win + WaitSpace,
.pwon player-win + WaitWinner) read the CAPS-SHIFT half-row (ld a,0xFE / in a,(0xFE) / bit 0,a; 0=pressed)
right after the wait returns; if held -> jp NewGameFromTitle (black border -> ShowTitle -> SelectDifficulty
-> RunMatch; the boot now shares this entry). Safe because ReadKeys only scans O/P/SPACE, so holding SHIFT
never blocks the waits. TESTMODE 22 verifies both paths in ZEsarUX: plain SPACE stays (play again),
SHIFT+SPACE -> title. code 10617B (1671B free); tap 41958B / tzx 42141B. .z80 site snapshots recaptured
from this build so the in-browser version has it too.

## FIX: SHIFT+SPACE-to-menu crash on real hardware (2026-06-17)
Tony on CRT: SHIFT+SPACE at end-of-match -> fully corrupted screen, needed a reset. CAUSE: the
hidden return jumped to ShowTitle, which DecompressScr's the title from its RLE parking area at
0x6000 -- but 0x6000 doubles as the gameplay shadow buffer and is overwritten during play, so after
a match it's garbage; decompressing garbage RLE corrupts the screen (and overruns). TESTMODE 22
missed it because it never played a round (0x6000 still held the title). FIX: SHIFT+SPACE now jumps
to NewGame -> SelectDifficulty directly (the skill/rules menu, which draws itself: "SCOPA / SELECT
SKILL LEVEL", no title data needed). ShowTitle is called ONCE at boot (0x6000 intact). TESTMODE 22
updated to trash 0x6000 first (reproduce the real condition) -> verified the menu renders clean.
code 10617B; tap 41958B/tzx 42141B; .z80s + downloads rebuilt from the fixed build.

## Colour-attribute tearing in the card slide (2026-06-17)
Tony (CRT): the flicker-free card slide is solid on pixels, but the COLOUR tears -- the attributes
lag the bitmap. CAUSE: BlitCard and EraseCardRegion each wrote the card footprint in TWO passes --
all 64 pixel lines (8 char-rows) first, then all 8 colour rows. So a char-row's colour wasn't written
until after the pixels of the char-rows BELOW it; the raster (top->bottom) could reach a char-row in
the window where its pixels were new but its colour old -> colour tearing. FIX: INTERLEAVE per char-row
-- write each char-row's 8 pixel lines immediately followed by that row's 6 colour cells, top to bottom,
so colour stays locked to the pixels ahead of the beam. EraseCardRegion: recompute-per-char-row loop
(both passes are shadow->screen ldir). BlitCard: keep the existing 64-line bitmap loop but carry the
attr address in IX and fill the row's colour at each char-row boundary; IX is push/pop-preserved because
RenderShadow holds the Table pointer in IX across BlitCard calls. Same total work (just reordered) ->
no timing-budget hit. VERIFIED in ZEsarUX: static board (TESTMODE 20) pixel-perfect, slide (TESTMODE 9)
lands clean -- no garbage from the restructured addressing. code 10615B (1675B free); tap 41956B. CRT
confirm of the tear-free colour = Tony.

## Attract / demo mode + sound on/off + dead-code trim (2026-06-17)
Tony approved: (1) 45s title idle, (2) "make it like the normal game", (3) a subtle on-screen
"press SPACE to play"; plus a Sound on/off menu option (default on; demo silent); and "clean up the
dead code". Implemented as af668cc.

DEMO is the REAL match loop with the AI driving both sides -- not a separate renderer, so it can never
drift from the live game:
- EnterDemo sets Difficulty=Hard, AceRule=on, DemoMode=1, then jp RunMatch. The match loops through the
  normal result + final-score screens (~10s holds) forever until SPACE.
- DemoPlayerTurn: PlayerTurn gets a one-line guard at the top (DemoMode -> jp DemoPlayerTurn) so the AI
  also plays the player's hand. aiSelectPlay now reads its hand via a new HandPtr word (was a hard-coded
  ld hl,Opp); OppTurn sets HandPtr=Opp, DemoPlayerTurn sets HandPtr=Player and routes through the player's
  normal play path (ChoiceVal=AIOpt, ChoiceMade=1) so capture/slide/scoring are identical to a human move.
- DemoCheckSpace (reads 0x7FFE bit0; on SPACE: ld sp,0xBFF0 / DemoMode=0 / jp NewGame) is polled from the
  TOP of Delay and inside the SlideIn HALT loop -> SPACE during any pause/slide bails to SelectDifficulty.
  Clobbers only A (safe at both sites).
- WaitSpaceOrDemo replaces WaitSpace at the per-round + opp-win waits; in demo it is a timed 10s hold (zero
  FRAMES, spin 500 frames calling DemoCheckSpace) then returns; outside demo it is jp WaitSpace. WaitWinner
  gets a demo guard at its top (jp nz,WaitSpaceOrDemo) so the player-win shimmer does not block.
- DemoOverlay (called at the end of RenderShadow, drawn into the shadow so Blit carries it): a thin row-0
  banner -- attr strip cols 4..27 = 0x47 (bright white on black) + centred "PRESS SPACE TO PLAY".
  ShowResults shows the same prompt at row 21 (gated ret z when not demo); the final-score screen already
  shows "PRESS SPACE TO PLAY AGAIN". (Cards are 64px = 8 char-rows and the three bands tile the full screen
  height, so there is no spare felt strip mid-board -- the prompt is a HUD banner over the decorative
  face-down opp card tops.)
- Idle timer in ShowTitle: at .startwait (post-music; re-entered after the help screen) zero FRAMES; in
  .wait, idle >= 2250 frames (45s @ 50Hz) with no key -> EnterDemo. Music runs interrupts-off so the 45s
  correctly begins after it.

SOUND: new SoundOn byte (boot=1). SoundEnabled helper returns Z (silent) if DemoMode OR !SoundOn; gates
NeapolitanSound, PlayTitleMusic, PlayJingle (call SoundEnabled; ret z). SelectDifficulty re-laid out (SCOPA
r2, SKILL r6, EASY/MED/HARD r9/11/13, asso r16 + sub r18, "5 SOUND ON/OFF" r21); key 4 = asso, key 5 = sound
(debounced); OFF red 0x42 / ON green 0x44. SelectDifficulty resets AceRule=0 on entry but PRESERVES SoundOn,
so the demo's hard+asso settings never leak into the human's next game while the user's sound choice persists.

DEAD CODE REMOVED (0 callers): CaptureBeep, ScopaBeep, WinJingle, LoseSound (Beep kept -- NeapolitanSound
uses it).

TESTMODE 23 = drop straight into self-play (skip the idle wait); 24 = render ShowResults in demo mode.
VERIFIED in ZEsarUX: banner on the live board + results grid + final-score screen; SPACE exits the demo to
SelectDifficulty (DemoMode 1->0, AceRule reset, SoundON preserved); 45s idle -> demo (real-time, DemoMode
0->1 + TableN->4 at ~58s = ~13s music + 45s); menu key-5 toggles SoundOn 1<->0 (red/green); the normal game
is unaffected (no banner, human plays + scores). Sound silencing is logic-only (no headless audio) -> Tony's
real-hardware ear.

.z80 RECAPTURE: capture at the post-music .wait (interrupts on) and poke FRAMES (0x5C78)=0 before
snapshot-save so the in-browser copy gets a fresh ~45s before auto-demo. PickTitle is deterministic from a
snapshot boot, so every capture picked the same title (coins) -- temporarily forced PickTitle (and 1 ->
and 0 = TitleRle) to capture the sword scopa.z80, then reverted and rebuilt production. Site: refreshed
tap/tzx/sna + both .z80s, added the Sound key + an "It plays itself" feature card + a title tip to
index.html, redeployed to Cloudflare; verified live (root 200 + COOP/COEP, new copy, downloads byte-match).
code CodeEnd=0xAACF (~1329B free); tap 42300B / tzx 42483B. PENDING Tony CRT play-test of the demo + sound.

## Opponent card-slide start position (2026-06-17)
Tony (CRT + in-browser, in regular play AND the demo): the CPU's played card often started its
slide from the wrong place -- a card visibly on the left would animate in from the right. CAUSE: the
CPU's face-down BACKS were drawn PACKED left-to-right by count (RenderShadow drew CountOpp identical
backs at cols 6,13,20), but OppTurn started the slide from the played card's logical SLOT column
(HandCol(slot)). With a full hand those coincide; once the hand had a GAP (a card already played) they
diverged -- the slide began at an empty column. The player's face-up hand never had this: it is drawn
at real slot columns (gaps preserved) and slides from the slot column.

Tony's design choice (mirror the player's hand, gaps and all -- not "shrink from the right"): FIX =
(1) RenderShadow's opponent loop rewritten to mirror the player loop -- ld ix,Opp / ld b,3 / ld d,6,
skip 0xFF, draw a BACK at col d, advance d every slot -> a back at each occupied slot's REAL column
(6 + 7*slot), so a played card leaves a gap exactly where it was (the old CountOpp packed-draw and its
.notop early-skip are gone). (2) OppTurn reverted to slide from the played card's true slot column
(push the slot / HandCol(slot)), which now matches where the back was drawn. LESSON: the render and the
animation must agree on positions -- drawing N identical items packed-by-count while animating from
logical slot indices is consistent only when there are no gaps; drive both off the same model.

TESTMODE 25 = CPU-hand-position regression (deal a round, punch a gap at slot 1 -> backs at cols 6 and
20 with a hole at 13; the AI plays slot 0 or 2 -> SlHandCol == that slot's real column). VERIFIED in
ZEsarUX: the gapped fan renders with the hole in the right place, the slide start matches, and the
normal game + self-play demo are both clean. code CodeEnd=0xAAD7 (~1321B free); tap 42308B / tzx 42491B;
both title .z80 snapshots recaptured and the site redeployed (live downloads byte-match).

## Tear-free card slides at the top of the screen (2026-06-17)
Tony (CRT): card animations sometimes showed the Spectrum "horizontal blinds" tear. Cycle-counting the
two slide routines: each slide frame does EraseCardRegion + BlitCard ~= 33,000 T (~47% of a 69,888 T
frame). After the frame interrupt the raster reaches the TOP of the display in only ~14,336 T (top
border), so for the CPU's hand (rows 0-7, top of screen) the erase+draw couldn't finish before the beam
arrived -> tear. The player's hand / table (rows 8-23) were already tear-free (beam gets there later),
which is why it was only "sometimes" -- the CPU's plays. (Headless can't see tearing, and ZEsarUX ZRCP
breakpoints don't halt under --vo null -- the "break" action wants a menu the headless build can't open
-- so the T-state figure is a hand cycle-count, not an auto-measure.)

Fix: rewrote the inner copy loops of BOTH BlitCard and EraseCardRegion. Each char-row's 8 pixel lines are
now unrolled with LDI (no inner counter, no per-line boundary test or bc-save); the char-row count lives
in a memory byte (BlitCrow) because LDI clobbers BC. ~40% faster -> a slide frame drops to ~20,000 T: the
erase now finishes before the beam starts and the draw (faster per char-row than the raster) stays ahead
row-by-row -> tear-free even at the top. The per-char-row bitmap+colour interleave (the earlier colour-tear
fix) is preserved. GOTCHA: the DUP-8 unroll makes the loop body >127 bytes, so the loop-back is jp, not jr.
VERIFIED: BlitCard render pixel-identical to the prior build (TESTMODE 20 gallery, PIL diff empty);
EraseCardRegion restores the background byte-exact (new TESTMODE 27 compares screen vs shadow over the whole
6x8 card = 432/432 bytes); self-play board clean during slides. Tear-free-ness itself = Tony's CRT. code +278B.

## Opening-deal leader: random first match, then alternate (2026-06-17)
Tony noticed the demo's "human" (bottom) side usually wins, and asked if that applies to the real game.
Both demo sides are Hard (Difficulty is one global) and DemoPlayerTurn feeds the AI's chosen capture through
the same path as OppTurn -- a fair mirror. The lean was structural: NewMatch always set Leader=0, so the
player led the OPENING deal of every match (real game AND demo). Host-sim (tools/ai_tune.py, 20k Hard-vs-Hard
matches): the side that leads the opening deal wins ~52.5% with asso piglia tutto on, ~50.9% (nil) with it
off. Small but real, and the human always had it. Fix (Tony's spec): a session-persistent OpenLeader byte,
randomised once at boot (ld a,r / xor (23672) / and 1); NewMatch copies it to Leader then flips it -> match 1
opens with a random leader and successive matches alternate. Per-deal alternation within a match is unchanged.
(.sna/.z80 freeze the boot RNG, so the web build's first opening leader is fixed-arbitrary then alternates;
real tape gets entropy.) TESTMODE 28 logs Leader over 6 NewMatch calls -> [0,1,0,1,0,1]. code CodeEnd 0xAC00
(1024 B free); tap 42586B / tzx 42769B. Both fixes rebuilt tap/tzx/sna + recaptured both title .z80s + site redeployed.

## Tear-free board redraws: delta blit (2026-06-17)
Tony (CRT): the blinds tear also shows when cards are drawn/removed -- a different mechanism from the
slide. Every board change ran the whole-screen Blit (LDIR of all 6912 bytes = ~145,147 T = 2.08 frames),
far too big to fit ahead of the beam, so the raster always crosses it mid-copy. Speed can't fix it -- a
memory->memory copy is ~21 T per 2 bytes either way.

Fix: DeltaBlit copies only the character cells that changed. Pass 1 diffs the shadow buffer against the
screen (reads only -> invisible, runs BEFORE the HALT) and marks dirty cells in a 768-byte map in the
unused shadow tail (DirtyArr @ 0x7B00; RenderShadow only uses 0x6000-0x7AFF). Pass 2, after HALT + di,
copies just the dirty cells in raster order (row outer, col inner), bitmap 8-lines + attr together per
cell -> small enough to stay ahead of the beam -> tear-free even at the top, colour locked to pixels. The
key idea: all the slow work (the diff) is in the invisible pre-HALT phase; the post-HALT visible copy is
tiny and raster-ordered. PaintAll now uses DeltaBlit; the per-frame zip re-pack animation keeps the full
Blit for now (a per-frame full diff would crawl) -> the re-pack can still tear (separate follow-up).
Overlays drawn to the screen after PaintAll (capture flash) self-heal -- the next delta restores them.

VERIFIED: from a stale screen DeltaBlit reproduces the full board pixel-identical to the old Blit
(TESTMODE 20 gallery, PIL diff empty); the invariant "screen == shadow everywhere after a delta update"
holds byte-exact across an A->B board change (new TESTMODE 29: 0/6144 bitmap + 0/768 attr mismatches);
self-play demo and a normal human game stay clean through many board changes. Tear-free-ness = Tony's CRT.
Perf: full diff ~217k T/PaintAll (~17% slower than the old Blit, absorbed by inter-turn pauses; a felt-skip
on rows 2-21 could make it a net win if needed). code CodeEnd 0xACFF (769 B free); tap 42849B / tzx 43032B.

## Slide ease-out (2026-06-17)
Tony: slides feel better with a touch of deceleration as the card reaches its destination. The
slide is character-cell (8px) aligned on both axes -- that alignment keeps the card's colour clean,
and moving sub-cell vertically would cause attribute-clash fringing (a white sliver above/below the
white-on-cyan card as it crosses cell boundaries). So the ease is in the TIME domain, not sub-pixel:
keep the clean 8px steps, hold the later ones a touch longer. SlideIn carries a step counter and
reads SlEaseTab (extra hold-frames per step = [0,0,0,0,0,1,1,2]); the first 5 steps whoosh at
8px/frame, the last 3 decelerate (2,2,3 frames) and the card settles. Held frames still poll
DemoCheckSpace so the demo SPACE-exit stays responsive; both axes hold together so the whole diagonal
eases. Curve is one defb -> trivially tunable. VERIFIED: timed one SlideIn via FRAMES (TESTMODE 30) =
13 with the table zeroed, 17 with the curve -> ease adds exactly sum(SlEaseTab)=4; slides still land
clean (the ease only adds HALTs at the drawn position, final position unchanged). Feel = Tony's CRT.
code 733 B free; tap 42871B / tzx 43054B.

## Tear-free table re-pack: band-limited delta blit (2026-06-17)
Tony (CRT) confirmed the blinds still showed when the table cards re-settle after a capture -- the
ZipCompact re-pack still used the full-screen Blit. DeltaBlit now takes a char-row band [DBstart,DBend):
PaintAll uses 0..24 (full, unchanged), the zip uses 8..16 (the table band only). Restricting the copy
to the band is the slack needed -- the band copy starts at the top of the frame and finishes before the
beam reaches the bottom of the table -> tear-free re-pack. Bonus: the band diff+copy (~72k T) is less
than the old full Blit (145k), so the re-pack is also snappier. VERIFIED: full-screen invariant still
byte-exact (TESTMODE 29); band path yields screen==shadow everywhere after a table change (TESTMODE 31);
demo re-packs 7- and 9-card tables cleanly. code 638 B free; tap 42907B / tzx 43090B.

## Crowded-table captures shown in place (2026-06-17)
Tony: on a full table the slide lands the played card on top of the existing cards. Extend the
multi-capture "card stays in your hand, flashing" idea to ALL captures once the table is crowded, for
both sides. When it's a CAPTURE and TableN >= 6 (where the slide starts clamping onto another card):
your turn keeps the card FLASHING IN YOUR HAND (HighlightCursor) while the cards it takes flash, brief
pause, sweep to pile -- no slide. The opponent, instead of sliding its back down, turns the card FACE-UP
IN PLACE at its hand slot (BlitCard + FlashCardRegion) and flashes there so you see what it played, then
sweeps to the CPU pile. Drops still slide; below the threshold captures slide as before. New flag
RevealInPlace makes ResolvePlay skip its on-table ShowCapture (the caller already showed it); shared
helpers FlashCaptured / FlashCardRegion. VERIFIED: forced full-table captures both resolve correctly --
opp (TESTMODE 32) OPileN 2 / TableN 5 face-up at the slot; player (TESTMODE 33, SPACE-driven) PPileN 2 /
TableN 5 flashing in hand; non-crowded play still slides. Threshold (cp 6) is one tunable byte. code 382 B
free; tap 42935B / tzx 43118B.

## Re-pack band-delta reverted (regression) + demo in-place + bias proof (2026-06-17)
The R34 band-limited delta blit for the table re-pack was a regression: the per-cell copy is ~400 T/cell
(I'd estimated ~180), so copying the whole table band per frame can't stay ahead of the beam -> it tore
WORSE than the plain blit, and the extra per-frame diff made it slower. Reverted ZipCompact to the full
Blit (original behaviour/speed). DeltaBlit stays for PaintAll's discrete redraws (few cells -> fast +
tear-free, its good case). FUNDAMENTAL: the table band is in the middle of the screen, beam reaches it
~28,672 T after frame start; in that window the Z80 can copy ~1,365 bytes but the band is ~2,048 -- so a
whole-band change can't be fully drawn before the beam arrives. A smooth re-pack re-changes the whole band
every frame -> can't be tear-free with a simple copy.

Demo in-place (Tony): DemoPlayerTurn now keeps the card flashing in-hand on a full-table capture (mirrors
the human PlayerTurn); the opponent already reveals face-up in place via OppTurn. TESTMODE 34: PPileN 2 /
TableN 5, demo clean.

Bias (Tony flagged 3x): AI verified byte-for-byte symmetric (every eval term table/card-based, no fixed
side; DemoPlayerTurn == OppTurn decision) + opening leader alternates (R31). Host-sim 40,000 matches at the
demo config = 49.95% player win rate -> fair within noise. Variance, not a bug. code 282 B free.

## Hybrid table re-pack: smooth slice when it fits, snap when crowded (2026-06-17)
Tony's "best of both worlds": at the start of a re-pack, ZipMoveSpan measures the moving block's width
(leftmost..rightmost column any shifting card touches = max+6 - min). If <=18 cols, the smooth slide
repaints ONLY that moving slice each frame (BlitSlice: per-char-row LDIR of cols c0..c0+W over the table
band rows 8..15) -- small enough (~189W+1183 T/char-row, < the ~5152 T/row beam budget) to finish ahead
of the beam -> tear-free smooth motion. If wider (the rare leftmost-of-a-full-table capture), ZipSnap
jumps the survivors to their targets and one full Blit shows it -- a single brief blink, not sustained
tearing. VERIFIED: TESTMODE 35 (W=13) smooth -> cards on 1,6,11; TESTMODE 36 (W=31) snap -> 1,6,11,16,21;
slice render correct; demo re-packs clean. Threshold (cp 19) one tunable byte. code 47 B free (TIGHT).

## AI depth audit: mid-game heuristic is at its 1-ply ceiling (2026-06-18)
Tony watched the demo throw a king from [two kings, empty table, one the Re di denari] and
questioned the whole AI. Investigated hard: faithful host-mirror (tools/ai_audit.py +
tools/ai_prime.py over ai_tune.py) with the ACTUAL shipped weights (ai_tune's W0 is the
pre-tuning baseline). Findings: (1) the play is CORRECT — the AI keeps the coin king, throws
the non-coin one (DROP_DENARI −4 tips it; both kings equal for primiera at prime-10), confirmed
by independent strategy research; the CRT read was likely the visually-similar non-coin king.
(2) Strength: 0.837 vs random, mirror 0.498 (no side bias), 75% of deals contain a scopa,
denari draws 21%. (3) Every cheap improvement was prototyped and FAILS: re-tune from shipped =
0.507 (noise, local optimum); naive 2-ply = 0.46–0.48 (worse); primiera/suit-completion
awareness = 0.476–0.498 (worse — and it won primiera 47.8% vs 47.7%, i.e. NO better, while
losing denari); paired-lead = noise. The insight: the comparative points (primiera/denari/carte)
are EMERGENT over the whole deal, so 1-ply local greed can't steer them — it only distorts the
locally-correct choices the heuristic already makes. Conclusion: the heuristic is at its
architectural ceiling; the only real lever (search) is already deployed where it's exact and
cheap (the deck-empty Esperto minimax). DECISION (Tony): accept the verdict, leave the AI as is.
Full write-up in AI_ANALYSIS.md. No code change. Diagnostic scripts kept in tools/.

## Decode-on-draw card art becomes the canonical game (2026-06-19 → 06-20)
A throwaway sandbox (`scopa-beam-race/`) was built to test whether the 40-card deck could be stored
ZX0-compressed and decompressed ON DRAW, freeing the ~7 KB of resident card art. Measured on the real
Z80: per-card ZX0 = 52.9% (8,408 B + index vs 15,744 B raw); a standard `dzx0` decode is ~30,124 T/card
(turbo 24k, mega 21k) -- 2.5-3.7x heavier than my desk estimate. A naive decode-per-frame blows the
frame budget, so the architecture is a small **persistent card CACHE** (10 slots, keyed by id) keyed off
the one chokepoint (`BlitCard` -> `DecodeCardA`): per-frame re-renders become cache HITS (cycle-≈ the old
id*384 multiply) -> tear-free + original speed BY CONSTRUCTION; only a genuinely new on-screen card costs
a decode. The four tear-critical direct draws pre-warm the card off-beam before the HALT. Verified
CRT-free via a CacheMiss counter (deal=8, re-pack=7, full match=23 = distinct cards, never per-frame).
The whole game was ported to this and **Tony CRT-confirmed "perfect"**. Then CONSOLIDATED (commit 373abd6)
into a single tree: `scopa/` root = the canonical decode-on-draw game; `scopa/legacy-v1/` = the original
resident-deck build (archived); `scopa/research/` = the sandbox proofs. `scopa-beam-race/` deleted.
LESSON: beam tricks fix TEARING (timing); the multi-card-per-frame re-render is a THROUGHPUT problem ->
the fix is a cache, not fancier beam-racing. Frees ~7 KB; .tap dropped ~45 KB -> ~38 KB.

## VINCITORE win screen (2026-06-19)
The ~7 KB freed by decode-on-draw funds a proper win screen. `ShowWinYou` ZX0-decompresses a VINCITORE
image (Re di denari on a gold sunburst, tricolore Rockwell wordmark) straight to 0x4000 + a victory
jingle, on a PLAYER win only (the opponent-win path keeps the scoreboard -- Tony's call). Memory crunch:
both win+lose (6.3 KB) won't fit with a smooth cache, so the card cache was trimmed 18 -> 10 slots (still
above the ~8 smooth floor) to free 0xC000-0xFFFF for `win.zx0` (3,142 B @ 0xF20A, time-shared with the
cache -- cards animate during play, the image uses the region at match end). Art generator
`research/art/win_v3.py` (per-cell optimal 2-colour + Bayer + a `stamp_banner` direct-cell text pass +
Rockwell slab serif). Tony-approved after an art-direction loop (dropped wordmarks for visible faces,
fixed blue specks, traditional font).

## Tear-free ace sweep: remove cards one per frame (2026-06-19 → 06-20)
A 5+ card removal (an ace sweeping the table) dirties the whole table band at once; the ahead-of-beam
delta-blit can't keep pace and tears ~3/4 down ("horizontal blinds"). First fix `ClearTableBehind` cleared
the band BEHIND the beam via a calibrated raster delay -- but that delay isn't honoured by a real ULA, so
it STILL tore on Tony's Harlequin. Replaced (commit 62aff22) by `RemoveCascade` (Tony's idea): erase each
taken card ONE PER FRAME ahead of the beam -- the R41 deal cascade in reverse, every frame a single
tear-free EraseCardRegion, NO hardware-specific timing. A non-crowded sweep also erases the played-card
slot. Threshold lowered 5 -> 3 (commit 7d234ba) after Tony's CRT saw a 4-card ace-take still tear at >=5
(the delta overruns the beam from ~3 cards up). **Tony CRT-confirmed clean.**

## Harlequin real-hardware fixes: col-31 flash bleed + clamp ripples (2026-06-20)
Tony's Harlequin (faithful ULA clone) showed a 1px-wide, full-card-height black line flashing at the FAR
LEFT whenever the RIGHTMOST card flashed. Not a bug: col 0's attr is CLEAN in RAM -- it's the ULA latching
col-31's attribute and bleeding it to the left edge of following lines (emulator-invisible). FIX (c51a199):
clamp the rightmost card column 26 -> 25 so col 31 stays felt -> bleed invisible. That clamp then rippled
into three more geometry sites that had to match: the re-pack slide-START (CaptureZipOld/FillZipCols, the
"rightmost card nudges right then settles" report, 3aa2ddf), the crowded-capture FLASH WIDTH (it flashed
`step` cols onto the obscured left strip of the clamped neighbour, b5108dc), and -- found in review -- the
smooth-glide TARGET (ZipCompact `.zsmooth` + ZipMoveSpan computed 26 unclamped, ffb902d). LAW: a
draw-position clamp must be mirrored EVERYWHERE the geometry is recomputed -- draw, slide-target,
slide-START, and flash-width.

## ZX0 titles + loading-screen pop-in (2026-06-20)
Both rotating title screens were SCOMPACT byte-RLE (~58%); re-packed as ZX0 (~40%): `DecompressScr` is now
a thin trampoline to the already-resident `dzx0_standard` -- titles decode pixel-identical (-2.4 KB tape).
The loading screen was an uncompressed 6912 B `LOAD ""SCREEN$` that built up line-by-line; now ZX0-packed
(6912 -> 3056 B) and decoded by the loader (load the decoder block first, stream `loading.zx0` to a scratch
buffer, `call dzx0` -> a clean POP-IN). The decoder is also re-rendered into `tools/render_deck.py`-style
montages. Tape 39 KB -> 36 KB.

## Tape/TZX loader: never pause mid-load, longer leaders (2026-06-20)
The first loading-screen attempt held the popped-in screen ~2 s MID-LOAD -- which DESYNCED the tape: a
continuously-playing TZXDuino streams the next block past the Spectrum while it holds, so "the block after
the loading screen isn't recognised" (Tony, on his TZXDuino). FIXES: (1) the loader never pauses -- it
streams every block back-to-back, always in LD-BYTES, and sets a `TapeFlag` so the GAME does the
min-display hold only on a snapshot/DivMMC load (tape skips it). (2) `build_tzx.py` switched from
Standard-Speed blocks to **Turbo blocks (ID 0x11)** with a 5000-pulse pilot (vs the standard 3223) so the
TZXDuino reliably catches each leader even when the Spectrum is briefly busy (Tony's "leader too short").
**Tony confirmed the .tzx loads on his TZXDuino.** Lesson: ZEsarUX fast-loads a .tap so only real hardware
tests tape timing.

## Repo consolidation, RULES.md, site refresh (2026-06-20)
Consolidated to one tree (above). Wrote `RULES.md` -- the rules & scoring AS IMPLEMENTED (capture/sweep
rules, the four classic categories, Primiera prime table 7=21/6=18/A=16, the Napola consecutive-coin-run
rule with the note on where it diverges from Wikipedia's contradictory Scopone trentino text, Palle del
cane, play-to-11, the four AI tiers). Site: deployed the enhanced build (downloads + recaptured in-browser
.z80s + new gameplay/Vincitore screenshots); regenerated the deck montages from the crowned `deck.bin`
(`tools/render_deck.py`) so all four kings show the R42 crown; updated the controls to the 4th skill tier
(1-4 = Easy/Medium/Hard/Esperto, asso->5, sound->6) and fixed an invisible white `<em>` on the cream
controls card. Site is direct-upload Cloudflare Pages -- deploy with `npx wrangler pages deploy site`
(a git push alone does NOT deploy).

## Code review: IsLastPlay count bug + re-pack clamp + cleanup (2026-06-20)
A careful review (two parallel audit agents + traces) found two real bugs. (1) `IsLastPlay` did
`CountPlayer / ld b,a / CountOpp / add a,b` -- but `CountHand` ends in `djnz` so it returns B=0, dropping
the player term: it computed `deck+opp` not `deck+player+opp`, wrongly SUPPRESSING a valid scopa when the
opponent clears on its last card while the player still holds one (the mirror of the only tested case).
Fixed via `push af`/`pop bc`; new TESTMODE 55 verifies the mirror. (2) The unclamped re-pack glide target
(above). Plus cleanup: 5 stale comments, 8 dead labels (CanCapture, ZipSnap, 6 orphan strings) removed.
All committed ffb902d / f605ba2.

## In-browser keyboard: autoStart + clean snapshots (2026-06-20)
"Keyboard dead again" on the JSSpeccy embed. Two real defects in the FILES: the .z80 snapshots were
captured mid-ROM-interrupt (PC=0x0038, IFF=0 -- fragile to resume) and `autoStart:false` left the emulator
PAUSED, where JSSpeccy DETACHES its keyboard handler. FIXES: recapture at a clean key-wait state (poll PC,
save only when 0x8000<=PC<0xC000 and the SAVED file verifies IFF1=1 -- retry until clean, since the keywait
loop HALTs and mostly samples in the ISR); set `autoStart:true`. Also: JSSpeccy picks its loader by file
EXTENSION so a `?v=` cache-buster breaks it -- bump the FILENAME (play-a.z80 / play-b.z80) to defeat a
stale cached snapshot. NB the JSSpeccy CPU worker doesn't step under headless Playwright, so the keyboard
can only be confirmed in a real browser.

## Scores prompt + 60s idle->demo + soft-reset combo (2026-06-21)
Three small UX tweaks. (1) The round-scores screen now prints "PRESS SPACE TO CONTINUE" (row 21, bright
white); the demo keeps "PRESS SPACE TO PLAY". (2) The match-END screens (win and lose) fall into the
attract demo after 60 s with no SPACE -- `WaitWinner` + new `WaitEndOrDemo` reset 23672 and `jp EnterDemo`
at 3000 frames (`ei` so the timer ticks); the between-rounds scores screen keeps the no-timeout wait. (3)
CAPS SHIFT + SYMBOL SHIFT + SPACE held during a game resets to the skill menu -- new `CheckSoftReset`
polled from ReadKeys + Delay, resets SP and `jp NewGame`. Verified: the combo on the win screen jumps to
SELECT SKILL LEVEL.

## Steady cyan border during jingles -- no capture flash (2026-06-21, Tony-confirmed)
Port 254 carries the speaker (bit 4) AND the border (bits 0-2) in one byte, so the `PlaySamples` sound
loop was driving the border BLACK (0x00/0x10) for a jingle's duration -- flashing the game's cyan border on
every capture. Fix (branch steady-border, merged 241edfd): `OR` the LIVE `BorderC` into the speaker byte
before each OUT, via a self-modified `or n` immediate patched once per note (a memory read in the 138 T hot
loop would be too slow) -> border held steady (cyan in-game, still black on the title/win screens where
BorderC=0). The two `or`s add 14 T (124 T -> 138 T loop), so `NoteInc` was recalibrated x138/124 to keep
the pitch. Verified the operands patch to 0x05 (TESTMODE 56; the border itself can't be screenshotted --
ZEsarUX flattens it). **Tony: "Looks and sounds great."**

## Pretty banners + Napola-at-achievement (2026-06-22, branch pretty-banners, merged + deployed)
Prototyped first (`tools/banner_proto.py` -> animated GIFs of three shimmer variants; Tony picked C). The
SCOPA!/NEAPOLITAN celebration banners + the scores header are re-rendered in **Rockwell** (gold) via
`tools/emit_banners.py`, and get a **golden light-sweep**: `SweepBanner` rolls a bright-white 3-cell band
left->right across the banner attrs (HALT-paced ~0.7 s/pass; letters rest bright gold). Scopa = one quick
pass, Napola = two. The **Napola now fires the instant a side completes the ace+2+3 of coins** (in
`ResolvePlay .done` -> `ShowNeapolitan`, gated once/round by `NapShown`, reset in `NewRound`), as a board
OVERLAY (was a black interstitial at round end); the points still tally on the scores screen. The scores
header changed from black-on-tricolore to gold Rockwell SCOPA. State ORG slid 0xB700->0xB800.

## Ace-sweep peel: respect the card overlap (2026-06-22)
Tony (CRT): a 5+ card sweep looked like each removed card took part of its overlapping neighbour. Root
cause: the cascade restored each taken card's footprint from the shadow (the FINAL board = felt), so the
overlap region could never show the neighbour. v1 (repaint the whole present fan to the shadow + DeltaBlit)
fixed the look in-emulator but on real hardware the per-frame copy overran the beam -> TORE, and was
laboured. v2 (shipped): keep the proven single-card `EraseCardRegion` (one card's 6x8 from the shadow after
a HALT), and if the peeled card's LEFT neighbour is ALSO a taken card, redraw just that neighbour (one
BlitCard, pre-warmed via DecodeCardA before the HALT so it's a cache hit). Erase + redraw ~17k T, finishing
in the top border ahead of the raster. Right-to-left; survivors need no redraw (the shadow holds them). Fast
(1 card/frame). Needs the swept ids (gone from Table[] before the cascade) -> stashed in RmTab[]/RmN.

## Tear-free CPU in-place reveal (2026-06-22)
The crowded-table capture flips the CPU's card face-up at the very TOP of the screen (rows 0-7, ~14k T of
ahead-of-beam slack); that reveal `BlitCard` had no frame sync, so on a cache miss the ~21k T decode could
drift it into the beam. Added a `halt` after the pre-warm, before the reveal -> the cache-hit draw lands in
the top border, tear-free. The removal afterwards was already synced (PaintAll/DeltaBlit).

## Merge + deploy (2026-06-22)
Merged pretty-banners -> main (becf912), pushed. Refreshed `site/` to the enhanced build: rebuilt
tap/tzx/sna downloads + recaptured play-a/play-b.z80 at the HOW TO PLAY keywait (IFF1=1, clean PC; new
`tools/capz80.py` drives there via the active-low key matrix and retries snapshot-save until the saved file
verifies). Deployed via `npx wrangler pages deploy site`; both scopa-spectrum.pages.dev and the custom
domain serve tap 36221 B / play-a.z80 33394 B. Open: the scores-header tricolore band was dropped for the
gold look (revert on request); banner shimmer feel + the peel + CPU reveal pending Tony's CRT sign-off.

## Ace-sweep: stop the capture flash before the peel (2026-06-22)
Tony (CRT): the taken cards were still showing the hardware FLASH bit (set by FlashCaptured) as the
progressive sweep removed them. RemoveCascade now clears bit 7 across the whole table band
(0x5900..0x59FF) and holds a brief beat before peeling, so the cards go SOLID, then sweep.

## In-browser keyboard, properly fixed + browser-verified (2026-06-22)
Recurring "keyboard dead" on the JSSpeccy embed. Root cause finally pinned with Playwright (local
COOP/COEP server + live site): JSSpeccy binds keydown/keyup to its appContainer (the only [tabindex]
element, appended INTO our host) and maps by e.keyCode, but the element only receives keys while
FOCUSED, and focus drifts to <body> after any click. Its public API exposes NO setKeyboardEventRoot
(my earlier "fix" was a no-op that also DELETED the working forwarder -> the "no difference" report).
The verified fix: a window capture-phase forwarder that re-dispatches every key INTO the appContainer
preserving keyCode, plus keep it focused on load/pointer-down. PROOF (live, focus forced to <body>):
press 'o' -> forwarder fires (fwdSeen=1) -> reaches the emulator element (reachedApp=1) -> JSSpeccy
processes it (defaultPrevented, processedApp=1). Diagnosed via a probe + the fact that JSSpeccy's
handler calls preventDefault on every non-meta key. New tools/capz80.py recaptures the snapshots.

## Deploy (2026-06-22, second wave)
Pushed the flash-stop (f8f7567) and the site fix (b406111); redeployed. Both domains serve the
flash-change downloads (tap 36236) + recaptured play-a2/play-b2.z80 + the keyboard-fixed index.html
+ the gold-header results.png. Live keyboard verified end-to-end in a real browser.

## VINCITORE attribute-shimmer (2026-06-22, branch win-shimmer -> merged + deployed)
The win screen now shimmers, attribute-only (bitmap untouched -> tear-free, the rays/banner/stars
recoloured gold<->white). Prototyped host-side first (tools/win_shimmer_proto.py -> win_proto/ GIFs;
Tony chose radial rays + VINCITORE banner light-sweep + star twinkle + a one-time ray-ring BURST then
a slow/stately SETTLE). At win-screen entry BuildShimmer backs the 768 win attrs up to the FREE shadow
buffer at 0x6000 (NOT the deck at 0xC000 -- needed for play-again) and builds a per-cell descriptor
table at 0x6300 (kind: RAY by radial ring-index via dx^2+dy^2 [SQTab] + isqrt / BANNER by column /
STAR by phase / static). ShimmerStep runs the timeline; ApplyShimmer paints. State ORG slid
0xB800->0xBA00 (~490 B). Lives in WaitWinner (replaced the old border-tricolore cycle; border now
steady black). The demo's victory shimmers too (.demo branch, ~8s timeout). CAPS+SYM+W cheat
(CheckWinCheat) jumps straight to the win screen, from the menu + in-game. Match-end idle->demo bumped
60s -> 5 min.

THE REAL-HARDWARE BUG (Tony CRT: "looked like a crash, attributes all over the place"). TWO bugs the
emulator hid: (1) ClassifyCell clobbered HL (the build loop's base pointer) + B (cx) -> every cell
after the first misclassified -> random cells lit (SH table static=593/ray=72, impossible rings
26-63). Fixed with push/pop hl+bc around the call -> ray=253/banner=123/star=15, rings 9-18. (2)
ApplyShimmer wrote all 768 attrs straight to the live 0x5800 over >1 frame, so the CRT beam read a
half-updated buffer EVERY frame = churn. ZEsarUX reads memory as a clean per-frame snapshot, so it
NEVER showed either bug -- both only visible on real hardware. Fix: build the frame OFF-SCREEN at
0x6600, then BlitAttrs LDIRs it to 0x5800 right after a HALT, chasing ahead of the raster (672 T/row
vs 1792 T/row) -> tear-free. LESSON: ZEsarUX screenshots = a memory snapshot, so they hide BOTH
beam-tearing AND register-clobber-driven garbage that "happens to look shimmery"; full-screen attr
animation MUST be double-buffered + beam-chased, and a clobbered classifier needs the SH table
dumped+counted to catch (don't trust the screenshot). Tony: "Looks awesome!" -> merged/pushed/deployed
(both domains serve tap 36814 + recaptured snapshots; in-browser visitors can CAPS+SYM+W to see it).

## In-browser emulator -> gameplay GIFs + download (2026-06-23)
The JSSpeccy in-browser keyboard could not be made reliable for Tony's real browser (verified the
wiring is correct -- forwarder delivers keys, JSSpeccy's handler runs -- but the game never responded,
and I couldn't reproduce headlessly because JSSpeccy runs the CPU in a Web Worker that doesn't step
under Playwright). Tried Qaop/JS (reliable window-level keyboard, main-thread/verifiable) but it's a
full SPA that hijacks the URL + needs its whole app mirrored -- research preserved on branch qaop-emu
+ the memory note. DECISION (Tony): option B -- replace the embed with two looping 256x192->512 GIFs
(img/gameplay.gif = attract demo, img/shimmer.gif = the VINCITORE shimmer; tools/capture_gif.py grabs
N ZEsarUX frames into a GIF; TM60 shimmer, new TM61 = jp EnterDemo) shown crisp via
image-rendering:pixelated, plus a 'Download the tape' CTA; kept the controls card. Removed JSSpeccy
(script, emu/ core, all play-*.z80/scopa*.z80). Live + verified (both GIFs load, 0 jsspeccy refs).
The tape downloads are unchanged and flawless on real hardware -- the actual deliverable.

## In-browser emulator on Qaop/JS + bug fix + win reveal + ZX0/synced banners + PALLE (2026-06-24)
A big session. Six things:

1. **In-browser emulator -> Qaop/JS (the keyboard finally works).** JSSpeccy's keyboard could never
   be made to work reliably (Web-Worker CPU, key-root focus, unverifiable headless). Switched to
   **Qaop/JS** (Jan Bobrowski), which binds keys to `window` and runs the CPU on the MAIN THREAD ->
   no COOP/COEP, and **verifiable in Playwright**. Mirrored Qaop's full app under `site/qaop/` (it
   hardcodes base `/qaop/`): index.html (canonical skeleton + `window.play={slug:"scopa.sna",...}`
   so it auto-loads our snapshot from `/qaop/bin/`), qaop.js, the 114716 B ROM blob at `/qaop/roms`,
   a no-op `sw.js` (avoid stale caching), trimmed manifest, icon/icon-mono/keyboard, and a `scr/scopa`
   thumbnail (kills the only console 404). Kept the `<a rel=author>`/torinak attribution (Qaop's soft
   licence check reads it). Added a "<- SCOPA" back-link. Linked from the main page (hero + play
   section: "Play in your browser" -> `qaop/`). **Verified in a real browser via Playwright**: boots
   our snapshot to the title, SPACE -> SELECT SKILL menu, 1 -> a live game with the cursor. (The
   earlier "dead keyboard" in tests was Playwright's *sub-frame* synthetic press being missed by the
   once-per-frame poll; a held key works -- a real human is fine.) Full notes in the memory note.

2. **Longer gameplay GIF.** site/img/gameplay.gif: 8 frames/2.9s -> 56 frames/~17s (tools capture).

3. **BUG FIX: rare far-left card flash in demo.** `MakeRoom` (pack-shift for a drop) tail-called
   `ZipCompact` without resetting `Removed`; a stale `Removed>=3` from the PREVIOUS capture made
   ZipCompact run `RemoveCascade` over the previous capture's `RmTab[]` positions -> cards blinked at
   stale slots (incl. slot 0, far left) for a frame before the re-pack corrected them. Trigger = a
   >=3-card capture immediately followed by a drop onto a non-empty table (rare). Fix: `Removed=0` in
   MakeRoom (a make-room is a drop -> nothing removed), matching what ResolvePlay's drop path already
   does before its own re-pack. Deterministic; TM-verified clean boot.

4. **Win screen: attribute reveal (no horizontal-blinds draw).** `ShowWinYou` used to dzx0 straight
   to the screen -> you watched the VINCITORE bitmap paint in. Now it decodes OFF-screen (0x6000),
   blanks the live attrs to black (bitmap copy is then invisible), copies the bitmap, then flips the
   real attributes on in ONE HALT-synced 768 B LDIR -> a clean pop-in (same tear-free path as the
   shimmer's BlitAttrs). TM10 verified the image renders correctly.

5. **ZX0-compressed banners + vblank-synced BlitBanner.** All four banners (SCOPA!, NEAPOLITAN,
   PALLE, the SCOPA scores header) are now stored ZX0 (4608 B raw -> ~1.3 KB) and decoded on show by
   `DecodeBanner` -> 0x6000; freed ~2 KB of the near-full 0x8000 code region (headroom 33 B -> ~2 KB).
   `BlitBanner` is now **vblank-synced**: black out the 4 banner rows' attrs (HALT), paint the bitmap
   under them invisibly, then reveal the gold attrs in one HALT-synced 128 B write -> no blinds, for
   ANY row (incl. row 0, the scores header). TM57/58/59 verified all three celebration banners.

6. **PALLE DEL CANE banner.** New celebration, parallel to napola: fires the instant a side completes
   all four 7s (`PalleDelCane`). `ShowPalleIfDone` in ResolvePlay's `.done` + `ShowPalle` (overlay +
   2-pass golden sweep) + `PalleShown` per-round flag (reset in NewRound). TM59 verified the banner.

tap 34.8 KB (smaller -- the ZX0 banners more than paid for the new code), tzx 35.2 KB. All TM-verified
in ZEsarUX (boot, tape load, win, 3 banners) + Qaop browser keyboard. CRT-pending: the synced reveals
(blinds-free) on real hardware, and PALLE firing in a live game.

## All screen transitions vblank-synced (2026-06-24)
Generalized the win/banner reveal to EVERY screen so nothing paints in as horizontal-blinds. Tony's
model: wipe the OLD screen to black (vblank-synced), draw the new screen INVISIBLY (black attrs), then
reveal the attributes vblank-synced. Helpers: `WipeBlackSync` (HALT + 768 B black-attr LDIR),
`RevealAttrsSync` (HALT + 0x7800->0x5800 LDIR), `FlipShadowSync` (shadow bitmap 0x6000->screen +
RevealAttrsSync; for the board scene-cut + win image). New **AttrOfs** var (like ScrOfs but attrs
only): text screens set AttrOfs=0x20 so FillAttrRow/ClsBlack/SetCellAttr build their colours in the
0x7800 buffer while PrintStr draws the bitmap live (invisible under the black-wiped attrs); one
RevealAttrsSync pops the whole screen in. The 0x7800 buffer is free even at title-time (beyond the
title ZX0 sources at 0x6000-0x75EE), so how-to never clobbers the title source. BlitBannerBitmap
factored out so the scores header joins the buffered reveal (bitmap live + gold rows in the buffer).
Converted: title (WipeBlackSync + invisible decode -- its source lives in 0x6000 so it can't use the
shadow; only the compact attr tail of the ZX0 stream is un-synced), skill menu, felt scene-cut
(RenderShadow + FlipShadowSync), scores (+ SetCellAttr/HighlightWinners buffer-aware), lose, how-to,
win (refactored to FlipShadowSync). GOTCHA: `DecompressScr` had to push/pop HL across WipeBlackSync
(the wipe clobbers HL = the decoder source) -- else the title decoded garbage (showed the ROM screen).
Interrupts are on by ShowTitle (Start does im1+ei), so the HALTs are safe. Verified every screen
renders (TM1 scores / TM10 win / TM57-59 banners / new TM62 lose / driven menu+how-to+real-game) + a
70s demo with no transition hang; return-from-how-to re-decodes the title cleanly. tap 35.0KB.
CRT-pending: blinds-free on real hardware. Technique -> animation note section 11.


## Software capture/cursor flash rework + v-synced loader + removal tear fixes -- SHIPPED (2026-06-25)
A long CRT-feedback iteration with Tony to replace the hardware-FLASH (0xF8 attribute-invert) capture
and cursor highlights with a software flash, plus several real-hardware tear fixes the rework surfaced.
End result: a clean cursor-style **bright(0x78) <-> dim(0x38) WHITE pulse** everywhere -- no yellow.

**The flash saga (capture animation).** Iterated: hardware FLASH (0xF8) -> solid gold (0x70) -> a
staggered gold WAVE (a gold band sweeping down each captured card, card k delayed WAVE_STAG behind k-1,
a left->right ripple) -> Tony's idea of a **45-deg "/" diagonal gold/white STRIPE glint** (a global
scrolling stripe field masked to the captured cards, with a subtle sine-"wavey" scroll speed via a
precomputed PhaseWaveLUT) -> Tony "looks out of place" -> **FINAL**: a simple synchronized bright-white
<-> dim-white pulse like the cursor, toggling every 5 frames (~40% faster than the earlier 2x-cursor
8-frame rate), 4 cycles ending on white, then the cards vanish. `FlashCaptureWave` loops WaveF
0..WAVE_FLASH=45, sets `WaveFlashCol` per frame (WaveF mod 10 < 5 -> bright else dim); `SweepCardCol`
is now a plain card-fill. DELETED all the dead diagonal machinery (WaveLocalC, FillCardWhite,
PhaseWaveLUT, FlashCardRegion, the WAVE_SWEEP/STAG/PAUSE/BAND consts) -- ~110 lines + the LUT.

**Killed gold everywhere.** Two spots still flashed gold after the wave went white: (a) the
CROWDED-TABLE played card -- on a full table it's shown in place (opp: revealed at its top slot;
player: left in hand) and was flashed solid gold (HighlightCursor / FlashCardRegion) separate from the
white wave. Folded INTO `FlashCaptureWave` via `WaveTopCol`/`WaveTopHi` (+ `WaveRowHi`, which retargets
SweepCardCol's attr-row high byte to 0x58 opp-top / 0x5A player-hand / 0x59 table band) so it pulses
white in step. (b) the MULTI-CAPTURE CHOICE -- `PulseChoice` now pulses the candidates + in-hand card
white, and `PaintChoice`'s preview + `HighlightCursor`'s resting highlight went gold(0x70) ->
dim-white(0x38), so there's no yellow even during the key-release wait.

**Cursor.** Glow is a white 0x78<->0x38 pulse (`PulseCursor`), 16-frame toggle (50% slower than the
first try, on Tony's call). The cursor MOVE (.left/.right) was tearing -- it un/re-highlighted the
bottom-of-screen hand attrs straight after the key-release busy-wait (mid-frame); added a HALT so the
move is vblank-synced like the pulse.

**Two removal tear fixes (Tony's CRT):** (1) LONE "BLINK BEFORE THE WAVE" -- the slide leaves the
played card only on the LIVE screen, so ShowCapture's PaintAll (renders from the shadow, felt at that
slot) ERASED then DrawPlayedCard re-drew it = a one-frame blink of just the played card. Fix: draw the
played card INTO the shadow before the delta (RenderShadow leaves ScrOfs=0x20) so the blit is a no-op
there. (2) CROWDED OPP CAPTURE, "BLINDS" ON REMOVAL -- the played card is revealed at the very TOP
(rows 0-7) where the per-cell DeltaBlit can't keep ahead of the beam, so the final PaintAll's removal
tore. The reveal already dodges this with a direct HALT+BlitCard; the removal now matches --
RenderShadow (gap at the played slot) + HALT + direct EraseCardRegion restores the top slot ahead of
the beam, PaintAll then finalizes. Tony's framing: "blinds" are specifically an ATTRIBUTE tear (the
ULA latches attrs per scanline), so setting the cells to felt tear-free (EraseCardRegion does attr +
bitmap in one pass) avoids them.

**Loading screen v-synced (build_tap.py loader).** It already blanked attrs to black + decoded the
bitmap invisibly, but the colours appeared as the TAIL of the ZX0 stream (not beam-locked). Now the ML
loader decodes the screen to a SHADOW @0xC000 (free until the deck loads there), LDIRs the bitmap ->
0x4000 under the still-black attrs, then `ei:halt:di` (the loader runs di'd) + LDIRs the 768 attrs in
one beam-locked flip. Loader 147 B (fits the printer buffer @23296). The emulator fast-loads so the
brief reveal can't be sampled visually -- verified the tape boots end-to-end to the correct title;
relied on Tony's TZXDuino for the actual tear-free reveal.

**Shipped.** Worked on branch `software-flash` (kept for rollback), merged to main when Tony said "All
looks great"; redeployed both domains (scopa-spectrum.pages.dev + the custom domain) + the in-browser
Qaop snapshot (`qaop/bin/scopa.sna`); refreshed the gameplay GIF to a current-build attract-demo
montage (built from the TESTMODE=61 demo build, then restored the normal build + reconfirmed root sna
== shipped sna). tap 35.6 KB / tzx 35.9 KB / sna 49179 B; all verified live byte-for-byte vs local.
CRT-signed-off by Tony across the rounds. Techniques -> animation note + tape-loader note + hw-laws.

**Follow-up (2026-06-26): crowded-capture removal ORDER.** Tony's CRT: on a crowded-table capture the
played card vanished LAST -- after the captured table cards were removed AND the survivors had re-zipped
(backwards: it should leave with the cards it captured, then the survivors close the gaps). Reordered all
3 crowded paths (OppTurn top / PlayerTurn + DemoPlayerTurn hand) so the tear-free played-card removal
runs BEFORE ResolvePlay: flash -> the played card + the captured table cards vanish together ->
ResolvePlay re-zips the survivors. KEPT the tear-free attr+bitmap restore (Tony: "don't regress that") --
HALT + direct EraseCardRegion, never a per-cell PaintAll delta (which 'blinds' at the top). OppTurn's
shadow already held the gap (the reveal + flash only touched the LIVE screen); the two hand paths
RenderShadow AFTER setting the slot 0xFF so the shadow has the gap there. Verified clean build + 36s demo
(opp-top + player-hand crowded captures) no hang, board coherent, no gold. SHIPPED + redeployed both
domains.

**Follow-up (2026-06-26): choose-capture option-move tear + full tear audit + dead-code cull.** Tony's
CRT: cycling between multiple capture options (O/P) tore the option highlight. PaintChoice did its board
redraw via the HALT-synced PaintAll but then wrote the option highlights (HighlightCursor + the
FlashTableCard candidate loop) MID-FRAME straight after, so the highlight attrs changed as the beam came
down -> tear. Fix: compute MaskToCapSel (no screen writes) then HALT, so the highlight writes land at the
frame top ahead of the beam (the steady .cw PulseChoice pulse was already fine -- it HALTs first; only the
per-move repaint tore). THEN audited EVERY direct-write call site in the file for any other tear: the
scores (PrintNum/PrintStr -> PrintChar adds ScrOfs, so even the top-left CPU count renders to the SHADOW,
never the live screen), DemoOverlay, the deal cascade, the zip/re-pack, the banners/transitions -- all
either shadow-then-DeltaBlit, HALT-before-direct-write, or vblank-synced. VERDICT: no other tear-prone
writes; the choose-capture highlight was the last gap. Loose end culled: FlashCaptured (gold 0x70 + the
hardware-FLASH bit, no HALT) was the LAST hardware-FLASH code left, dead in the release (only caller was
IF TESTMODE==51, a col-0 wrap probe) -> deleted it + the testmode (-32 lines, 7333 lines now). The whole
codebase is now uniformly "shadow-then-synced-copy, or HALT-before-direct-write". tap 35.6KB. CRT-signed
off by Tony; SHIPPED + redeployed both domains.

**Follow-up (2026-06-26): full-table ace-capture top-card tear + sharper re-audit + RemoveCascade tidy.**
Tony's CRT: a full table, CPU captures with an ace -> the ace (revealed at the opp's top hand slot, rows
0-7) tore DURING the capture flash. FlashCaptureWave did one HALT per frame then flashed the table-band
cards (.cwc loop, rows 8-15) and the top played card (.cwtop, rows 0-7) LAST. The beam draws rows 0-7
FIRST, so on a FULL table the band loop ate enough of the ~14.3kT top-border budget that the ace's attr
write landed after the beam had started it -> attribute tear. Fix: flash the top card FIRST, right after
the HALT, before the band loop (.cwplayed now jumps straight to .cwd; the old trailing .cwtop is gone).
Pure reorder -- same colour (white), same "all cards pulse together" look, tear-free. THEN re-ran the
tear audit with a SHARPER criterion: not just "is there a HALT before the writes" but the within-frame
WRITE ORDER vs the beam arrival on WORST-CASE data (max TableN=16). Verdict: the .cwtop-after-loop was the
UNIQUE "loop-then-top-of-screen-write" shape in the whole file; every other HALT-synced path is either
one-card-per-frame at the top (pre-warmed, the R30 path), band/bottom-only with ample budget, or a
raster-order vblank attr flip -> NO other within-frame ordering risk. The original audit checked
HALT-presence (necessary) but not write-order-vs-budget-on-worst-case-data (the missing sufficiency).
TIDY (fork-flagged): removed RemoveCascade's now-dead `res 7` band un-flash loop -- it cleared the
hardware-FLASH bit across the table band before the sweep, but the software flash sets no FLASH bit so
the cards are already solid white (0x78) -> it was a per-frame value-preserving no-op. Verified clean
build, ace sweep still clears (TM50 -> table band 100% felt), no hang. tap 35.6KB. CRT-signed off by
Tony; SHIPPED + redeployed both domains.

**Follow-up (2026-06-27): napola/PALLE banners on a last-hand SWEEP completion + scopa last-card rule
confirmed.** Tony asked whether NEAPOLITAN fires if the napola is achieved on the very last hand, and
whether scopa has a last-card caveat. Checked authoritative sources (Pagat + Wikipedia): SCOPA (the
sweep) NEVER counts on the final card of a deal -- and the code already does this correctly (ShowScopa +
the scope point are both gated behind IsLastPlay). But NAPOLA and PALLE DEL CANE are PILE-COMPOSITION
bonuses (which cards you end up with), not timing/act bonuses, so they count regardless of WHEN the cards
are captured -- INCLUDING the leftover cards swept to the last capturer at round end (SweepToLast). Their
banners, though, only fired from ResolvePlay's .done (a capture-completion): a trio / four-7s completed by
the final sweep scored the points (ScoreRound tallies the final pile) but showed NO banner. Fix:
extracted the napola check into ShowNapolaIfDone (mirroring ShowPalleIfDone) and call both after
SweepToLast in the round-end path (.end). Now a napola/PALLE completed by the final sweep celebrates too,
consistent with the scoring. KEY DISTINCTION: scopa = an ACT (clearing the table) -> last-card exception;
napola/palle/settebello/primiera/carte/denari = PILE COMPOSITION -> no timing exception. Verified: 80s
demo runs the .end re-check at every round-end, no crash, coherent board. Removed two never-reachable
napola test blocks (TM-number collisions; the standalone harness can't render ShowNeapolitan, which needs
full game context -- the demo is the real test). tap 35.6KB. SHIPPED + redeployed both domains.

**Follow-up (2026-06-28): napola-aware AI eval -- modelled, proven strength-neutral, shipped for OPTICS.**
Tony's CRT: in the demo the AI grabbed a 7 instead of the coin that would COMPLETE a 3-point napola.
Diagnosis confirmed: EvalCapture values 7s (+12), the settebello (+35), coins (+5) but had NO napola
term -- Napola/PalleDelCane were only ever called from ScoreRound (round-end), never the eval -- so the
napola coin read as a generic +5 coin and lost to the +12 seven. MODELLED it first (tools/ai_napola.py,
the ai_prime.py pile-aware pattern, faithful host-mirror): a napola-gain term (delta of the pile's
consecutive-coin run, priced ~35/point like the settebello). RESULT over 24k matches = 0.502 -- WITHIN
NOISE: it does NOT make the AI stronger (the napola is rare ~14% of deals, the AI already completes most,
and grabbing the coin gives up the 7 which is also valuable -> net wash). BUT it is SAFE (no point
cannibalisation: denari/primiera/carte unchanged -- unlike the rejected primiera-awareness which HURT)
and it fixes the visibly-dumb play. Decision (Tony): ship for the optics -- the AI plays as smart as it
is in the watched demo -- accepting it's polish not strength. Z80 impl: NapolaBonus in EvalCapture
(+ BuildNapMask/NapRun/OrCoinBit) -- a coin bitmask of the AI pile built once per aiSelectPlay
(OPile/PPile by HandPtr), then per candidate capture adds (run(pile+captured)-run(pile))*35. Verified:
TM65 unit test = the AI takes the napola coin (BestSlot 0) in Tony's exact position; 70s demo no crash,
coherent board. Code FITS at the original state ORG 0xBA00 (CodeEnd 0xB4CE, 1330 B free) -- an initial
state-slide to 0xBB00 was reverted once a fresh sym showed the slide was unnecessary. **BUILD GOTCHA
found + worked around: plain `sjasmplus scopa.asm` does NOT rewrite scopa.sym (it was stale since
Jun 22); build_tap.py reads scopa.sym for dzx0/TapeFlag, so the build must be
`sjasmplus scopa.asm --sym=scopa.sym` -- benign until now only because dzx0 sits at a fixed ORG, but a
moved TapeFlag would mis-poke the loader.** tap 35.7KB. SHIPPED + redeployed both domains. Lesson +
experiment recorded in AI_ANALYSIS.md.

**Follow-up (2026-06-28): website review + improvements + a copy pass.** Playwright-previewed the live
site (desktop + mobile). The design holds up, but two issues surfaced: the "What's inside" feature cards
were near-invisible (a 5% cream wash on the felt), and the two gameplay GIFs were 582 KB (oversized at
1024x768 / 512x384). FIXES (origin/main=116c092): feature cards -> a solid teal gradient like the download
cards (now readable); the GIFs -> downscaled to 512x384 LOSSLESS animated WebP via `<picture>` (gameplay
260->10.5 KB, shimmer 322->14 KB; reduced-motion users get a static poster, WCAG 2.2.2). WebP beat video
here BECAUSE it's pixel art -- lossless AND smaller than even an MP4 (the generic "GIF->video" advice is
wrong for sharp few-colour frames: H.264/VP9 add chroma-bleed + ringing). Added "Read how it was built" /
GitHub / RULES links to the story + footer. COPY PASS (origin/main=5b3498d): the page never told a
newcomer what Scopa IS -> the "Play it now" intro now opens by teaching it (capture by value, sweep for a
scopa, the scoring, first to 11); the dedication "In memory of a friend's lost game" -> "A recreation
of..." (Angelo is alive and well); the lede leads with the hook + an honest AI line ("a genuinely strong
opponent that plays fair -- it never sees your hand"); the "Authentic art" feature re-angled (48x64
legibility + the crowns) to stop repeating the deck section; ARTICLE got a ZX0 coda; misc tightening. Both
shipped + verified live on both domains (mobile play confirmed -- the Qaop page has an on-screen keyboard).
Site-review notes + the GIF/WebP reasoning are the lasting lessons.

**Follow-up (2026-06-29): BILINGUAL SITE (English + Italian).** English at `/`, Italian at `/it/`, a header
EN.IT switcher, generated FROM ONE SOURCE so the two never drift: `site_src/template.html` (structure +
`{{key}}` placeholders + hreflang/canonical/og:locale + absolute asset paths) + `tools/build_site.py`
(EN exact + idiomatic IT strings; validates no `{{` left). To edit copy now: edit template/strings, run
`python3 tools/build_site.py`, deploy. Italian is ADAPTED not literal (dropped the 'broom'/'Re (king)'
glosses that exist only for English readers). The game ROM is already Italian so no Z80 change. Both
previewed via Playwright + verified live on both domains.

**Follow-up (2026-06-29): SELF-PLAY AI WATCHDOG (Tony's request) -- systematic odd-play audit, Z80-confirmed.**
`tools/ai_watch.py` plays a FAITHFUL host port of the shipped Esperto mid-game evaluator against itself
(weights read straight out of scopa.asm: card_count x3, coin +5, settebello +35, 7 +12, 6 +8, ace +6,
sweep +50, napola run-delta x35, drops, safety with the ThreatLive card-count gate, Seen = table+own-hand+
played). It logs every mid-game decision (the endgame minimax is provably optimal -> oddities only live in
the heuristic) and flags by DOMINANCE: a move is odd iff another legal move is >= on every fundamental
(cards, coins, settebello, primiera-gain, scopa, napola) and no worse on the bad axes (gives opp a scopa /
leaves the settebello). CONFIRMED ON THE REAL Z80: `tools/ai_zx_check.py` + a board-injection probe
(`TESTMODE 70`: poke Table/hand/OPile/Seen, run the real aiSelectPlay, read back BestSlot + captured mask)
-> 14/14 flagged boards reproduce identically -> the mirror is faithful, the findings are the shipped logic.
Found + fixed a real harness bug en route: zx_shot.write_mem used ZRCP `write-memory` + concatenated hex
(mangles multi-byte writes) -> must be `write-memory-raw`; also the first injected board after smartload
reads stale state -> the driver warms up with a throwaway run. FINDINGS (5000 matches): ~1.5 dominated
mid-game plays/match -- ~75% primiera (the eval's flat per-rank bonus can't see a card's MARGINAL primiera
value), ~16% napola subtleties, ~4% accepting a small sweep-risk over an equal safe move, ~5% carte/denari
trades. NO gross blunders (zero dropped settebelli, zero passed guaranteed points; the rare LEFT_SETTEBELLO/
PASSED_SCOPA are the napola fix completing a 3-5pt napola). The watchdog independently REDISCOVERED
AI_ANALYSIS s4/s6 -- the only systematic suboptimality is the marginal primiera/tempo blindness inherent to
a 1-ply evaluator, and primiera-awareness was already proven to HURT. No new bug; AI sound; left as-is.
Write-up = AI_ANALYSIS.md s8. TESTMODE 70 is gated (not in the shipped build -- normal scopa.tap byte-
identical, no redeploy).

**Follow-up (2026-06-29): opening-deal fairness check (Tony: "I don't recall ever seeing two same-value
cards on the opening table -- bias?").** Read the deal code: `Shuffle` is a correct Fisher-Yates (swap
Deck[b] with a random j in [0,b], b=39->1); `DealRound` takes the first 10 shuffled cards (3+3 hands, 4
table); there is NO re-deal rule and nothing that filters same-value pairs. The RNG `Rnd` does no PRNG
arithmetic -- it returns consecutive bytes of the lower-8KB Spectrum ROM (addr = Seed & 0x1FFF) and bumps
the pointer; the seed's low byte is set from the R refresh register at boot (cheap 8-bit thrift). MEASURED
the real algorithm (real ROM bytes + the real Fisher-Yates + the real deal order) over every starting seed
via `tools/deal_check.py`: **41.2% of opening tables have a same-value pair -- IDENTICAL to the fair-deck
theoretical rate** (1 - (36*32*28)/(39*38*37) = 0.412); 2000 chained deals = 40.5% (noise). So NO bias --
~2 deals in 5 do contain a pair. Why it's missed: a same-value pair is always two DIFFERENT suits (unique
deck -> no two identical cards), which don't read as "a pair" at a glance in a fast demo. Perception, not
code (same family as the "player wins more" variance hunch). Nothing to fix.

## Capture-removal timing rework (2026-06-30, branch capture-timing -> main, Tony CRT-tuned)
Tony questioned the crowded-capture removal ORDER: it went flash -> erase the in-hand card -> PAUSE ->
sweep the table cards, splitting one capture into two separated events (and the "beat" was holding on a
half-removed board). Reordered to flash -> HOLD -> erase in-hand + table sweep as ONE continuous removal:
the `ld b,1 / Delay` beat moved from the top of RemoveCascade to BEFORE the in-hand EraseCardRegion in all
three crowded paths (OppTurn / PlayerTurn / DemoPlayerTurn); RemoveCascade's own beat is now skipped when
RevealInPlace=1 (kept for non-crowded big captures, which have no in-hand erase). SWEEP SPEED: Tony A/B'd
the card-by-card RemoveCascade peel on the CRT -- 1 frame/card (original) too fast, 4 frames/card too slow,
settled on **3 frames/card (60ms/card PAL)** via two extra halts at .rcwait, placed so EVERY per-card path
passes through them (the two jumps land there; the neighbour-redraw path falls through -- a single-path
halt would have made consecutive-taken-card peels faster than the rest). Coverage: RemoveCascade is the
ONLY card-by-card removal (all Removed>=3 captures); 1-2-card removals are a single-frame delta vanish,
unchanged. Verified per iteration: clean build, demo advances + coherent, 3->0 multi-card sweep observed.
NOTE: TESTMODE 50 is bit-rotted (its direct ResolvePlay call no longer fires the sweep; fails identically
on the pre-change build -- its comment still references the removed ZipCompact behind-the-beam clear).
Future tidy, not a regression. [CORRECTION 2026-07-03: TM50 was NEVER bit-rotted -- see the root-and-branch
review entry below; the "failure" was a 6-second test read calibrated to the OLD animation timing, landing
mid-banner. TableN reads 0 from ~12s. The test is healthy.]

## Root-and-branch code review (2026-07-03, branch code-review, four parallel review agents + verify pass)
Tony's ask: full audit -- bugs, optimisation, reclaimable memory, rot. Method: four parallel deep-review
agents (logic/rules/AI; rendering/tear-invariants; memory/dead-code; tooling/tests/docs), every significant
claim then re-verified by hand against the source before any edit. Score: the game logic, scoring, endgame
minimax and the entire tear-free rendering architecture came back CLEAN -- the review found ONE real
defect class, some honest rot, and a set of unguarded build traps.

**THE BUG (fixed): per-play flags leak across the abandon longjmp.** DemoCheckSpace / CheckSoftReset /
CheckWinCheat abandon via `ld sp,0xBFF0 / jp NewGame` from ANY Delay/SlideIn poll -- and neither they nor
NewMatch/NewRound reset the per-play flags. Real, user-triggerable leaks: a stale RevealInPlace (abandon
during a crowded capture's banner hold) made every later non-crowded capture skip ShowCapture -- the played
card's image lingered on the band until the next repaint, persisting until the next crowded capture; a
stale WavePlayed (abandon mid-flash, the demo's most-watched moment) ghost-flashed an empty slot on the
next crowded wave. DropPreShift's leak was masked only by a fragile prologue default (dim-1's data-corruption
scenario was traced and shown UNREACHABLE -- the first play of a game always runs the slide prologue).
FIX: a 5-flag sanitize block in NewRound (DropPreShift/RevealInPlace/ChoiceMade/WavePlayed/Removed --
the R50 far-left flash was exactly a stale-Removed bug of this class). Verified by injecting all five
mid-demo and confirming NewRound clears them.

**Reclaimed 153 bytes (CodeEnd 0xB4E5 -> 0xB44C, ~1.45 KB free):** deleted dead code -- Blit (the historic
full-screen LDIR, zero callers since DeltaBlit), TriCol (orphaned tricolore table), CapN (dead state var),
WarmBoard+WarmArr (dead in the decoder region); gated ScoreTestSetup/LastPlayTestSetup/ScaleTune behind
IF TESTMODE != 0 (test fixtures were shipping in the game binary). False positives caught by hand-verify:
ShowTitle/TapeFlag look dead to a naive scan but live inside IF TESTMODE==0; win.zx0 is the INCBIN SOURCE
of win_zx0.bin (identical by construction, NOT a deletable duplicate). Deleted the genuinely orphaned
lose.scr/lose.zx0 (referenced by nothing -- the lose screen is the scoreboard by design). DEFERRED as
not-worth-the-risk: factoring the 25x addHLA idioms (~107B, cold code but churn) and the three CRT-tuned
crowded-capture tails (~35B) -- no memory pressure (another +1KB is one state-ORG slide away).

**Build traps closed (build_tap.py):** (1) STALENESS GUARD -- refuses to build if scopa_code.bin/scopa.sym
are older than scopa.asm (the stale-sym trap is now impossible, not just documented); (2) FIT ASSERTS --
deck<decoder (the gap was 40 BYTES), decoder<cache, dzx0-inside-decoder, titles<0x8000, win<0x10000,
loader<=256B: a worse-compressing asset now FAILS the build instead of silently corrupting RAM on the real
machine; (3) WinZX0/DecodeCardA/CacheBase now read from scopa.sym instead of hardcoded. NEW ./build.sh =
the one documented build command. README's public build instructions taught the stale-sym recipe -- fixed.

**Tooling drift killed:** tools/shipped_weights.py is now THE single source of the shipped AI weights
(there were FIVE divergent copies; ai_tune's W0 relabelled as the historical pre-tune baseline it actually
is; ai_watch imports the module; archived experiments annotated). ai_zx_check.py reads all state addresses
from scopa.sym instead of hardcoding them (the state ORG has moved four times; this pass alone moved Seen
by deleting CapN -- the hardcoded probe would have silently poked garbage). Session-specific scratch paths
-> ./tmp. site/index.html + /it/ now carry a GENERATED marker and DEVELOPMENT.md documents the site
generator (they were silently clobber-able). TESTMODE mailbox map documented in DEVELOPMENT.md s11.

**Comments added where the review found undocumented couplings:** SweepToLast clobbers Who (repaired by
.domove -- don't remove the reload); AddOption's 16-cap + the TableN<=13 proof; the demo player-side
Seen[] asymmetry (accepted, invisible in the human game); TM70's mailbox aliasing DBattr; TM35/36/50
comments refreshed to current semantics (thresholds, RemoveCascade, the 12s read note).

Verified: clean build, 10 TESTMODEs spot-assembled, flag-injection test, ai_watch selftest through the
new weights module, staleness guard trips on a stale sym and passes on a fresh one, 60s demo advancing.
tap 35,611B (was 35,766). Branch pushed for Tony's merge call -- the game binary changes (flag fix + dead
code), so the usual CRT pass applies before it ships.

## Docs for the announcement (2026-07-11, no code change)

Prep for announcing the game to the ZX Spectrum Italia community: the repo is about to get real
visitors, so the process story had to actually be *in* the repo. Audit found the gap — iteration
was documented (this file), collaboration was documented (ARTICLE.md), but the study-the-classics
phase lived only outside the repo. Three commits:

- **README "How this was made"** (130ea86): the five-act process — study the masters (book canon
  + disassembling Manic Miner/JSW/Knight Lore/Alien 8/Skool Daze), build the laboratory (headless
  ZEsarUX + TESTMODEs), recreate the game, let the CRT be the judge, prove it don't feel it.
- **ARTICLE.md fresh pass** (e4195bd): honest timeline ("first playable in a day; making it
  *right* took the month, and that's where the story lives"), four new chapters (studying the
  masters, the card-counting opponent, the one-pixel ghost, the rewritten close), placeholder
  links replaced with the live site + repo.
- **ARTICLE.it.md** (5e8815c): full idiomatic Italian translation + cross-links both ways.

Also translated the Facebook post + repo blurb for the group announcement (delivered outside the
repo).

## Scoreboard polish: bonus-row green highlights + black border (2026-07-15, Tony CRT-spotted)

Two Tony niggles from the scores screen, both confirmed in source and fixed:

**(a) Neapolitan/Palle numbers never went green.** HighlightWinners only looped the five CatWin
categories (rows 6-14); the NEAPOLITAN (row 15) and PALLE CANE (row 16) rows were printed after
the loop and stayed white however they scored. Both bonuses are inherently one-sided (only one
pile can hold coins A+2+3, or all four 7s), so the fix greens whichever side is non-zero -- no
tie case. Shared `.side` helper keeps it ~40 bytes.

**(b) The scoreboard kept the table's cyan border.** ShowResults never touched the border; the
cyan leaked from NewMatch ("cyan border for the game proper") because nothing between rounds
re-set it. Every other non-table screen (title/menu/win/lose) frames in black -- the scoreboard
was the only leak. Fix: ShowResults now sets border+BorderC black right after its WipeBlackSync;
the cyan set MOVED from NewMatch to DealCascade immediately after the FlipShadowSync scene cut,
so the border turns cyan at the exact moment the felt appears (previously the border went cyan
at match start, a beat before the scene cut -- with a black scoreboard that would have flashed).

TM24 enriched to seed Pnapola=3/Opalle=1: verified attrs 0x44 at (15,15)+(21,16), neighbours
still 0x07, BorderC=0, black-border screenshot. TM23 demo soak: BorderC cycles 5 (97s of play)
-> 0 (scores hold) -> 5 (round-2 felt), screenshots clean both sides. Shipping build: title ->
menu -> Easy -> deal shows the cyan felt (the NewMatch move holds on the real entry path).
tap 35,661B. Deployed to both domains 2026-07-15 (96b1a86). **Tony CRT-confirmed 2026-07-15:
running on the CRT, all is great — the black-framed scoreboard + green bonus numbers signed off.**

## The AI case file: two demo suspicions investigated + AI_ANALYSIS §9 + Italian (2026-07-15, no code change)

Two more "that looked odd" plays from Tony watching the demo, both run to ground with the
verified host mirror (`ai_watch.ai_select`) and the Z80 source:

**Ace played from a two-ace hand (asso on — the demo config).** Correct, decisively. On any
non-empty table the ace-sweep is the top-scoring play by a mile (23 vs −29 for the alternative
drop on a representative board); a second ace makes it better (opponent forced to drop onto the
empty table, second ace harvests the drop); and there's no "saving it" — all three hand cards
play before the redeal. Bonus finding: on an EMPTY table the eval will deliberately drop an ace
as sweep-armour (an ace on the table means the opponent's ace can only take that ace, not sweep)
— but only when the alternative drops are risky; given a face card it drops the face.

**2 of denari dropped while holding a plain 2.** The mid-game policy provably cannot do this —
DROP_DENARI −4 and value-identical safety mean the plain two wins strictly (verified in BOTH the
mirror and the Z80 EvalDrop source). So it was the deck-empty Esperto minimax: with the opponent
hand fully deduced, a coin drop is tie-optimal when it provably can't be punished (the coin comes
back via recapture or the end-of-round sweep), and ties break by enumeration order, not optics.
Standing offer: if ever seen with the deck NOT empty, capture the board — TESTMODE 70 would make
that a real find.

Both cases (and the five older ones) written up as **AI_ANALYSIS.md §9** — the emergent doctrine
(coin discipline, the ace doctrine, drop hierarchy, counted sweep-avoidance, the minimax switch
and why its ties look arbitrary) plus the case file table (score: machine 6, humans 1) and a
verbatim-verified mirror-probe snippet. README's AI section points to it. **AI_ANALYSIS.it.md**:
full Italian translation of the whole audit (all nine sections), ARTICLE-style cross-links.
Commits 9a47851 + 7863278.

## Scope row: green for BOTH non-zero sides (2026-07-20, Tony-spotted)

Tony's follow-up niggle on the scoreboard greens, and he was right: scope is ADDITIVE (each
side keeps a point per sweep — ScoreRound adds PScopa and OScopa to the round totals
unconditionally), but the display treated it as a fifth comparative category via CatWin+4 —
only the higher count greened, and a 1-1 tie greened NOBODY despite both sides having just
scored. Under the green's meaning everywhere else on the screen ("these points counted"),
that was wrong.

Fix: HighlightWinners' comparative loop shrunk to CatWin 0..3 (Carte/Denari/Settebello/
Primiera); scope joins napola/palle in the non-zero-green chain (same .side helper, row 14,
both columns independently). The now-dead CatWin+4 comparison deleted from ScoreRound
(display-only code; scoring untouched). TM24 now seeds scope 2-1 and asserts BOTH numbers
0x44 alongside the napola/palle checks — all six attr checks PASS + black border; TM23 demo
soak reaches a real scores screen with correct totals (0-0 scope correctly stays white).
tap 35,652B.
