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
