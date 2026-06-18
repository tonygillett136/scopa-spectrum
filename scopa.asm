    DEVICE ZXSPECTRUM48
CARDS = 0xC000
BACK  = 40
    IFNDEF TESTMODE
TESTMODE = 0
    ENDIF
; FASTSIM: 1 for the headless match-sims (37 bias / 41 Esperto integration) -> render/delay
; gates compile in. Always 0 in the shipped build (TESTMODE 0), so zero production cost.
FASTSIM = 0
    IF TESTMODE == 37
FASTSIM = 1
    ENDIF
    IF TESTMODE == 41
FASTSIM = 1
    ENDIF
    IF TESTMODE == 43
FASTSIM = 1
    ENDIF
; ---- state ----
; State block was at 0xB000 (code ceiling). Slid up to 0xB500 to hand code room for the Esperto
; card-counting AI (endgame minimax) + the deal cascade. State uses ~0x150B; stack at 0xBFF0
; leaves ~2.4KB below it for the stack + the minimax search frames.
    ORG 0xB500
Deck:     defs 40
Player:   defs 3
Opp:      defs 3
Table:    defs 16
TableN:   defs 1
DeckPos:  defs 1
Seed:     defs 2
PPile:    defs 40
PPileN:   defs 1
OPile:    defs 40
OPileN:   defs 1
PScopa:   defs 1
OScopa:   defs 1
Who:      defs 1
FCval:    defs 1
CapSel:   defs 16
CapN:     defs 1
Played:   defs 1
Cursor:   defs 1
LastCap:  defs 1
Keys:     defs 1
PMatch:   defs 1
OMatch:   defs 1
PRound:   defs 1
ORound:   defs 1
CatWin:   defs 5
PBest:    defs 4
Tmp0:     defs 1
Tmp1:     defs 1
BlitCrow: defs 1                  ; BlitCard/EraseCardRegion char-row counter (LDI clobbers BC)
Options:  defs 32
OptionN:  defs 1
ChoiceIdx: defs 1
AISlot:    defs 1
AIOptEval: defs 1
AICardId:  defs 1
AIOpt:     defs 1
ScoreW:    defs 2
BestScoreW: defs 2
BestSlot:  defs 1
BestOpt:   defs 1
TmpTable:  defs 16
TmpTableN: defs 1
Leader:    defs 1
OpenLeader: defs 1                ; who leads the FIRST deal of a match: random at boot, flips per match
Difficulty: defs 1
Seen:      defs 5
ScrOfs:    defs 1                  ; high-byte add: 0x00=screen, 0x20=shadow(0x6000)
HumanTurn: defs 1                  ; 1 only while the player is choosing -> cursor flashes
Pnapola:   defs 1                  ; Neapolitan (napola) points this round
Onapola:   defs 1
NapWhich:  defs 1
Ppalle:    defs 1                  ; "le palle del cane" (all four 7s) bonus
Opalle:    defs 1
SlColF:    defs 2                  ; card-slide: column (8.8 fixed point)
SlRow:     defs 1                  ; slide: current cell row
SlRowStep: defs 1                  ; slide: row delta per step (+2 / -2)
SlDc:      defs 2                  ; slide: column delta per step (8.8)
SlHandCol: defs 1                  ; slide: source column
SlDestCol: defs 1                  ; slide: destination column (table slot)
SlPrevCol: defs 1                  ; slide: card's previous drawn column (to erase)
SlPrevRow: defs 1                  ; slide: card's previous drawn char-row (to erase)
SlStep:    defs 1                  ; slide: step counter (0..7) -> indexes the ease-out hold table
ZipCur:    defs 16                 ; compaction zip: each surviving card's current column
ZipStep:   defs 1                  ; compaction zip: post-capture table column step
ZipFrames: defs 1                  ; compaction zip: frame counter (safety cap vs hang)
HideTable: defs 1                  ; RenderShadow flag: 1 = skip the table cards
Acc1:      defs 2                  ; title music: melody channel phase accumulator
Inc1:      defs 2                  ; title music: melody channel phase increment
Acc2:      defs 2                  ; title music: bass channel phase accumulator
Inc2:      defs 2                  ; title music: bass channel phase increment
BorderC:   defs 1                  ; current border colour -- restored after music/jingles
AceRule:   defs 1                  ; optional "asso piglia tutto": ace takes whole table (0=off default)
AceSweepOpt: defs 1                ; 1 = the current capture is an ace-sweep -> Scopa d'Assi: no scopa
ChoiceMade: defs 1                 ; 1 = player picked the capture before the slide (card stays in hand)
ChoiceVal:  defs 1                 ; the pre-chosen capture option index
RevealInPlace: defs 1              ; 1 = crowded-table capture shown in place (hand/opp-slot) -> ResolvePlay skips the on-table ShowCapture
CurTitle:   defs 2                 ; ShowTitle: address of the randomly-chosen title.rle (2-screen rotation)
DemoMode:   defs 1                 ; 1 = attract / CPU-vs-CPU self-play demo is running
HandPtr:    defs 2                 ; aiSelectPlay's hand source: Opp normally, Player for the demo's player turn
SoundOn:    defs 1                 ; user sound toggle (skill menu); 1 = on (default)

; ---- Esperto endgame: perfect-information minimax of the final round ----
; Once the deck is empty the unseen cards ARE the opponent's hand, so the AI can read the
; real Player[]/Opp[] arrays (legitimate deduction) and search the last <=6 plies exactly.
RootWho:   defs 1                  ; side the search maximises (0=player, 1=opp)
CurDepth:  defs 1                  ; recursion depth (0..6); indexes Frames[]
LfTN:      defs 1                  ; LeafEval snapshot: TableN
LfPP:      defs 1                  ; .. PPileN
LfOP:      defs 1                  ; .. OPileN
LfPM:      defs 1                  ; .. PMatch (ScoreRound bumps the match totals -> restored)
LfOM:      defs 1                  ; .. OMatch
FRSZ = 32
Frames:    defs FRSZ*7             ; per-depth node frame: undo snapshot + loop locals + a/b window
DealSave:  defs 10                 ; deal cascade: the dealt cards [P0-2 O0-2 T0-3] while revealing

    ORG 0x8000
Start:
    di
    ld sp,0xBFF0
    ld iy,0x5C3A                 ; ROM interrupt-handler sysvar base
    im 1
    ei                           ; interrupts on -> HALT can sync screen updates to vblank
    xor a
    ld (HideTable),a             ; default: RenderShadow draws the table normally
    ld (DemoMode),a              ; demo off
    ld hl,Opp
    ld (HandPtr),hl              ; AI evaluates the opponent hand by default
    ld a,1
    ld (SoundOn),a               ; sound on by default
    ld a,r                       ; random opening leader for the FIRST match of the session
    ld hl,23672
    xor (hl)
    and 1
    ld (OpenLeader),a            ; (NewMatch then alternates it each subsequent match)
    IF TESTMODE == 1
    call ScoreTestSetup
    call ScoreRound
    call ShowResults
.h1:
    jr .h1
    ENDIF
    IF TESTMODE == 2
    call LastPlayTestSetup
    ld a,6                       ; play the 7 of denari (already removed from hand above)
    ld c,0
    call ResolvePlay
.h2:
    jr .h2
    ENDIF
    IF TESTMODE == 3
    ; table values 1,2,3,4 (ids 0,1,2,3); enumerate captures for value 5
    xor a
    ld (Table),a
    ld a,1
    ld (Table+1),a
    ld a,2
    ld (Table+2),a
    ld a,3
    ld (Table+3),a
    ld a,4
    ld (TableN),a
    ld a,5
    call findAllCaptures
.h3:
    jr .h3
    ENDIF
    IF TESTMODE == 4
    ; table=[3,4]; AI hand=[7bastoni(sweep!), ace, 5denari] -> must pick the sweep
    ld a,2
    ld (Table),a
    ld a,3
    ld (Table+1),a
    ld a,2
    ld (TableN),a
    ld a,36                      ; 7 of bastoni (value 7) -> captures 3+4 = SWEEP
    ld (Opp),a
    ld a,0                       ; ace of denari (value 1) -> drop
    ld (Opp+1),a
    ld a,4                       ; 5 of denari (value 5) -> drop
    ld (Opp+2),a
    call aiSelectPlay
    ld (Tmp0),a                  ; chosen slot
.h4:
    jr .h4
    ENDIF
    IF TESTMODE == 9
    ; replicate PlayerTurn .play WITH the slide; id 23 (val 4) drops -> table=[8,23]
    ld a,23
    ld (Player),a
    ld a,0xFF
    ld (Player+1),a
    ld (Player+2),a
    ld a,8
    ld (Table),a
    ld a,1
    ld (TableN),a
    xor a
    ld (Cursor),a
    ld a,(Cursor)
    ld hl,Player
    call addHLA
    ld a,(hl)
    ld (hl),0xFF
    ld (Played),a
    ld a,(Cursor)
    call HandCol
    ld (SlHandCol),a
    ld a,16
    ld (SlRow),a
    ld a,0xFF
    ld (SlRowStep),a
    ld a,(TableN)
    call TableSlotCol
    ld (SlDestCol),a
    call SlideIn
    ld a,(Played)
    ld c,0
    call ResolvePlay
.h9:
    jr .h9
    ENDIF
    IF TESTMODE == 10
    ; winner screen inspector: YOU win 11-7
    ld a,11
    ld (PMatch),a
    ld a,7
    ld (OMatch),a
    call ShowWinYou
    call WaitWinner
.h10:
    jr .h10
    ENDIF
    IF TESTMODE == 11
    ; capture the LEFTMOST table card -> a survivor zips to column 1 (the underflow case
    ; that hung). Table=[0,1,2,3], play id 10 (ace coppe) captures id 0 -> table [1,2,3].
    xor a
    ld (Table),a
    ld a,1
    ld (Table+1),a
    ld a,2
    ld (Table+2),a
    ld a,3
    ld (Table+3),a
    ld a,4
    ld (TableN),a
    ld a,10
    ld (Player),a
    ld a,0xFF
    ld (Player+1),a
    ld (Player+2),a
    ld (Opp),a
    ld (Opp+1),a
    ld (Opp+2),a
    xor a
    ld (Cursor),a
    ld (PPileN),a
    ld (OPileN),a
    ld a,10
    ld c,0
    call ResolvePlay
.h11:
    jr .h11
    ENDIF
    IF TESTMODE == 12
    ; drop onto a 6-card table (ids 4..9) -> crosses the 6->7 step boundary: existing
    ; cards make room + the laid card flashes. Play ace (value 1) = cannot capture -> drop.
    ld hl,Table
    ld (hl),4
    inc hl
    ld (hl),5
    inc hl
    ld (hl),6
    inc hl
    ld (hl),7
    inc hl
    ld (hl),8
    inc hl
    ld (hl),9
    ld a,6
    ld (TableN),a
    xor a
    ld (Player),a                ; ace of denari (value 1) in hand
    ld a,0xFF
    ld (Player+1),a
    ld (Player+2),a
    ld (Opp),a
    ld (Opp+1),a
    ld (Opp+2),a
    xor a
    ld (Cursor),a
    ld (PPileN),a
    ld (OPileN),a
    ld (HumanTurn),a
    call PaintAll
    ld b,4
    call Delay
    xor a                        ; play the ace -> ResolvePlay drops it
    ld c,0
    call ResolvePlay
.h12:
    jr .h12
    ENDIF
    IF TESTMODE == 13
    ; engine pitch check: play an ascending C-major scale, then hang
    di
    ld hl,0
    ld (Acc1),hl
    ld (Acc2),hl
    ld hl,ScaleTune
    call PlayTune
    xor a
    out (254),a
    ei
.h13:
    jr .h13
    ENDIF
    IF TESTMODE == 14
    ; SECOND-to-last card: player clears the table (3+4 captured by the 7) but the OPPONENT
    ; still holds one card, deck empty -> total-after = 1 -> a VALID scopa (must count).
    ; (The old `cp 2` bug suppressed this.) Expect PScopa=1, TableN=0.
    xor a
    ld (PPileN),a
    ld (OPileN),a
    ld (PScopa),a
    ld (OScopa),a
    ld a,2
    ld (Table),a                 ; value 3
    ld a,3
    ld (Table+1),a               ; value 4
    ld a,2
    ld (TableN),a
    ld a,0xFF                    ; played card (id 6) already removed from the hand
    ld (Player),a
    ld (Player+1),a
    ld (Player+2),a
    ld a,11
    ld (Opp),a                   ; opponent still holds one card
    ld a,0xFF
    ld (Opp+1),a
    ld (Opp+2),a
    ld a,40
    ld (DeckPos),a
    ld a,6
    ld c,0
    call ResolvePlay
.h14:
    jr .h14
    ENDIF
    IF TESTMODE == 15
    ; capture-choice render: the played card stays IN THE HAND while you choose (so it can
    ; never overlap a table card). Two 7s + a spare on the table; the played 7 sits in hand.
    ld a,6                       ; 7 of denari on the table
    ld (Table),a
    ld a,16                      ; 7 of coppe on the table
    ld (Table+1),a
    ld a,9                       ; 10 of denari (spare, NOT a 7)
    ld (Table+2),a
    ld a,3
    ld (TableN),a
    ld a,26                      ; 7 of spade = the played card, STILL in the hand
    ld (Player),a
    ld a,0xFF
    ld (Player+1),a
    ld (Player+2),a
    ld (Opp),a
    ld (Opp+1),a
    ld (Opp+2),a
    xor a
    ld (PPileN),a
    ld (OPileN),a
    ld (Cursor),a                ; cursor on the played card
    inc a
    ld (HumanTurn),a            ; player's turn -> the in-hand card flashes
    ld a,26
    ld (Played),a
    ld a,7
    call findAllCaptures         ; value 7 -> two single-7 options
    xor a
    ld (ChoiceIdx),a
    call PaintChoice             ; played 7 stays in the hand; the candidate table 7 flashes
.h15:
    jr .h15
    ENDIF
    IF TESTMODE == 16
    ; asso piglia tutto (Scopa d'Assi): an ace sweeps a NON-ace table -> table clears, NO scopa.
    ; Expect PPileN=4 (3 table + the ace), TableN=0, PScopa=0.
    ld a,1
    ld (AceRule),a
    xor a
    ld (PPileN),a
    ld (OPileN),a
    ld (PScopa),a
    ld (OScopa),a
    ld a,4                       ; 5 of denari (value 5)
    ld (Table),a
    ld a,11                      ; 2 of coppe (value 2)
    ld (Table+1),a
    ld a,9                       ; 10 of denari (value 10) -- no ace anywhere on the table
    ld (Table+2),a
    ld a,3
    ld (TableN),a
    ld a,0xFF                    ; played ace already removed from the hand
    ld (Player),a
    ld (Player+1),a
    ld (Player+2),a
    ld a,12                      ; opponent still holds a card -> not the last play
    ld (Opp),a
    ld a,0xFF
    ld (Opp+1),a
    ld (Opp+2),a
    ld a,20
    ld (DeckPos),a
    xor a                        ; play id 0 = ace of denari (value 1)
    ld c,0
    call ResolvePlay
.h16:
    jr .h16
    ENDIF
    IF TESTMODE == 17
    ; player capture choice applied via the pre-slide ChoiceMade path: two 7s on the table,
    ; pick OPTION 1 (the 7 of coppe). Expect Table=[7denari], TableN=1, PPile=[7coppe,7spade].
    xor a
    ld (PPileN),a
    ld (OPileN),a
    ld a,6                       ; 7 of denari  -> option 0
    ld (Table),a
    ld a,16                      ; 7 of coppe   -> option 1
    ld (Table+1),a
    ld a,2
    ld (TableN),a
    ld a,0xFF                    ; played card already out of the hand
    ld (Player),a
    ld (Player+1),a
    ld (Player+2),a
    ld a,12
    ld (Opp),a
    ld a,0xFF
    ld (Opp+1),a
    ld (Opp+2),a
    ld a,1
    ld (ChoiceMade),a            ; simulate: the player pre-chose...
    ld (ChoiceVal),a             ; ...option 1 (the 7 of coppe)
    ld a,26                      ; played = 7 of spade
    ld c,0
    call ResolvePlay
.h17:
    jr .h17
    ENDIF
    IF TESTMODE == 18
    ; fix #1: the AI must NOT credit a scopa (+50) for an ace-sweep (Scopa d'Assi).
    ; AI hand=[ace denari]; table=[5d,7c,10d]. Ace sweep = 12 card-count + 33 bonuses = 45.
    ; (denari 5+12+5+11; played ace = denari5+ace6=11). Without the fix it would be 95.
    ld a,1
    ld (AceRule),a
    ld a,1
    ld (Difficulty),a            ; medium -> no HARD card-count term
    call ClearSeen
    ld a,4                       ; 5 of denari
    ld (Table),a
    ld a,16                      ; 7 of coppe
    ld (Table+1),a
    ld a,9                       ; 10 of denari
    ld (Table+2),a
    ld a,3
    ld (TableN),a
    xor a                        ; ace of denari (id 0) in hand slot 0
    ld (Opp),a
    ld a,0xFF
    ld (Opp+1),a
    ld (Opp+2),a
    call aiSelectPlay            ; -> BestScoreW = the ace-sweep's score
.h18:
    jr .h18
    ENDIF
    IF TESTMODE == 19
    ; fix #2: leaving an ace-less table (with the settebello on it) is penalised under AceRule.
    ; AI hand=[4 of coppe] captures the 4 of denari, LEAVING [settebello, 7 coppe] (no ace).
    ; score = 6 count + 5 (4d denari) - 5 (easy 7s) - 2 (ace-guard: 2 cards) - 25 (settebello) = -21.
    ld a,1
    ld (AceRule),a
    ld a,1
    ld (Difficulty),a
    call ClearSeen
    ld a,3                       ; 4 of denari (value 4)
    ld (Table),a
    ld a,6                       ; settebello (value 7)
    ld (Table+1),a
    ld a,16                      ; 7 of coppe (value 7)
    ld (Table+2),a
    ld a,3
    ld (TableN),a
    ld a,13                      ; 4 of coppe (value 4) -> captures the 4 of denari
    ld (Opp),a
    ld a,0xFF
    ld (Opp+1),a
    ld (Opp+2),a
    call aiSelectPlay
.h19:
    jr .h19
    ENDIF
    IF TESTMODE == 20
    ; card-art gallery: the three denari FIGURES (8/9/10 of denari = ids 7/8/9) on the
    ; table, so the coin-medallion art can be eyeballed in the real engine.
    ld a,7
    ld (Table),a                 ; Fante di denari
    ld a,8
    ld (Table+1),a               ; Cavallo di denari
    ld a,9
    ld (Table+2),a               ; Re di denari
    ld a,3
    ld (TableN),a
    ld a,0xFF                    ; empty both hands
    ld (Player),a
    ld (Player+1),a
    ld (Player+2),a
    ld (Opp),a
    ld (Opp+1),a
    ld (Opp+2),a
    xor a
    ld (PPileN),a
    ld (OPileN),a
    call PaintAll
.h20:
    jr .h20
    ENDIF
    IF TESTMODE == 22
    ; hidden SHIFT+SPACE-to-menu: SHIFT at the win screen -> SelectDifficulty (skill menu);
    ; plain SPACE plays again. CRUCIAL regression: a real game overwrites the title's RLE
    ; parking area @0x6000 (the shadow buffer) -- so trash it here to prove the feature does
    ; NOT re-decompress the title (which crashed/corrupted the screen on hardware).
    ld hl,0x6000
    ld de,0x6001
    ld bc,0x1AFF
    ld (hl),0xA5                 ; fill 0x6000-0x7AFF with garbage, as gameplay would
    ldir
    call NewMatch
    ld a,11
    ld (PMatch),a
    ld a,7
    ld (OMatch),a
    call ShowWinYou
    call WaitWinner
    ld a,0xFE
    in a,(0xFE)
    bit 0,a
    jp z,NewGame                 ; SHIFT held -> skill menu (must render cleanly despite trashed 0x6000)
.h22:
    jr .h22                      ; plain SPACE -> stay here (proves no false trigger)
    ENDIF
    IF TESTMODE == 23
    ; attract demo: drop straight into CPU-vs-CPU self-play (Hard + asso piglia tutto),
    ; skipping the title idle timer.
    ld a,2
    ld (Difficulty),a
    ld a,1
    ld (AceRule),a
    ld (DemoMode),a
    jp RunMatch
    ENDIF
    IF TESTMODE == 24
    ; render the per-round ShowResults grid in demo mode -> verify the "PRESS SPACE TO PLAY"
    ; prompt under the scoring grid, then hold via the demo wait.
    ld a,1
    ld (DemoMode),a
    call NewMatch
    call ShowResults
    call WaitSpaceOrDemo
.h24:
    jr .h24
    ENDIF
    IF TESTMODE == 25
    ; CPU-hand-position regression: deal a full round, then punch a GAP in the CPU hand
    ; (slot 1 empty). The backs must draw at their REAL slot columns (6 and 20, hole at 13),
    ; mirroring the player hand; and when the AI plays slot 0 or 2 the slide must start from
    ; that card's true slot column (HandCol(slot) = 6 or 20), matching where it was drawn.
    ; Screenshot during the Delay shows the gapped fan; SlHandCol after = the played column.
    ld a,1
    ld (Difficulty),a
    call NewMatch
    call NewRound
    ld a,0xFF
    ld (Opp+1),a                 ; gap at slot 1 -> backs at cols 6 and 20, hole at col 13
    call PaintAll
    ld b,10
    call Delay                   ; hold the gapped fan (~5s) for a screenshot
    call OppTurn
.h25:
    jr .h25
    ENDIF
    IF TESTMODE == 37
    ; BIAS SIM: play 200 Hard-vs-Hard demo-config matches (display/delays gated off via FastSim)
    ; and tally winners into Options[0]=player, Options[1]=opp. Confirms the demo is fair on the
    ; REAL Z80 logic (not just the host sim).
    ld a,2
    ld (Difficulty),a
    ld a,1
    ld (AceRule),a
    ld (DemoMode),a              ; PlayerTurn -> DemoPlayerTurn (both AI, no input)
    ld a,1
    ld (FastSim),a
    xor a
    ld (0x7E0B),a                ; player-win count (shadow tail; untouched -- render is gated off)
    ld (0x7E0C),a                ; opp-win count
    ld b,200
.ml37:
    push bc
    call FM37
    or a
    jr nz,.ow37
    ld hl,0x7E0B
    inc (hl)
    jr .t37
.ow37:
    ld hl,0x7E0C
    inc (hl)
.t37:
    pop bc
    djnz .ml37
.h37:
    jr .h37
FM37:                            ; play one full match -> A = winner (0 = player, 1 = opp)
    call NewMatch
.fmr:
    call NewRound
    call PlayRound
    call ScoreRound
    ld a,(PMatch)
    cp 11
    jr nc,.fmend
    ld a,(OMatch)
    cp 11
    jr nc,.fmend
    ld a,(Leader)
    xor 1
    ld (Leader),a
    jr .fmr
.fmend:
    ld a,(PMatch)
    ld c,a
    ld a,(OMatch)
    cp c
    jr z,.fmtie
    jr nc,.fmopp                 ; OMatch > PMatch -> opp wins
    xor a                        ; OMatch < PMatch -> player wins
    ret
.fmopp:
    ld a,1
    ret
.fmtie:
    ld a,(Leader)                ; tie at/over 11 -> another round
    xor 1
    ld (Leader),a
    jr .fmr
    ENDIF
    IF TESTMODE == 35
    ; re-pack hybrid SMOOTH path: 3-card table, cards 1&2 shifted right by 2 (narrow moving block).
    ; ZipMoveSpan should give W<=18 -> smooth slice; ZipCompact should land them on 1,6,11.
    call NewMatch
    call NewRound
    ld a,3
    ld (TableN),a
    ld hl,Table
    ld (hl),0
    inc hl
    ld (hl),11
    inc hl
    ld (hl),22
    ld hl,ZipCur
    ld (hl),1
    inc hl
    ld (hl),8
    inc hl
    ld (hl),13                   ; old cols 1,8,13 -> targets 1,6,11 (W = 13)
    call ZipCompact
.h35:
    jr .h35
    ENDIF
    IF TESTMODE == 36
    ; re-pack hybrid SNAP path: 5-card table all shifted right by 5 (wide moving block).
    ; ZipMoveSpan W=31 -> snap; ZipCompact should still land them on 1,6,11,16,21.
    call NewMatch
    call NewRound
    ld a,5
    ld (TableN),a
    ld hl,Table
    ld (hl),0
    inc hl
    ld (hl),11
    inc hl
    ld (hl),22
    inc hl
    ld (hl),33
    inc hl
    ld (hl),4
    ld hl,ZipCur
    ld (hl),6
    inc hl
    ld (hl),11
    inc hl
    ld (hl),16
    inc hl
    ld (hl),21
    inc hl
    ld (hl),26                   ; old 6,11,16,21,26 -> targets 1,6,11,16,21 (W = 31)
    call ZipCompact
.h36:
    jr .h36
    ENDIF
    IF TESTMODE == 34
    ; demo player crowded keep-in-hand: full table + a capturing card, DemoPlayerTurn auto-plays.
    ; Should flash in-hand (not slide) and resolve: PPileN 2, TableN 5.
    ld a,1
    ld (Difficulty),a
    ld a,1
    ld (DemoMode),a
    call NewMatch
    call NewRound
    ld hl,Table
    ld (hl),0
    inc hl
    ld (hl),1
    inc hl
    ld (hl),2
    inc hl
    ld (hl),3
    inc hl
    ld (hl),4
    inc hl
    ld (hl),5
    ld a,6
    ld (TableN),a
    ld a,15
    ld (Player),a
    ld a,0xFF
    ld (Player+1),a
    ld (Player+2),a
    call DemoPlayerTurn
.h34:
    jr .h34
    ENDIF
    IF TESTMODE == 33
    ; crowded-table PLAYER keep-in-hand: full table + a player card that captures. Enter PlayerTurn;
    ; the driver presses SPACE -> the card should flash in-hand (not slide), resolve: PPileN 2, TableN 5.
    ld a,1
    ld (Difficulty),a
    call NewMatch
    call NewRound
    ld hl,Table
    ld (hl),0
    inc hl
    ld (hl),1
    inc hl
    ld (hl),2
    inc hl
    ld (hl),3
    inc hl
    ld (hl),4
    inc hl
    ld (hl),5
    ld a,6
    ld (TableN),a
    ld a,15                       ; Player[0] = coppe 6 -> captures Table's denari 6 (id 5)
    ld (Player),a
    ld a,0xFF
    ld (Player+1),a
    ld (Player+2),a
    xor a
    ld (Cursor),a
    call PlayerTurn
.h33:
    jr .h33
    ENDIF
    IF TESTMODE == 32
    ; crowded-table opp REVEAL-IN-PLACE: full table (6 cards) + an opp card that captures one.
    ; OppTurn should turn the card face-up at its slot (not slide) and resolve: OPileN 2, TableN 5.
    ld a,1
    ld (Difficulty),a
    call NewMatch
    call NewRound
    ld hl,Table
    ld (hl),0
    inc hl
    ld (hl),1
    inc hl
    ld (hl),2
    inc hl
    ld (hl),3
    inc hl
    ld (hl),4
    inc hl
    ld (hl),5                     ; Table = ids 0..5 (values 1..6)
    ld a,6
    ld (TableN),a
    ld a,15                       ; Opp[0] = coppe 6 (value 6) -> captures Table's denari 6 (id 5)
    ld (Opp),a
    ld a,0xFF
    ld (Opp+1),a
    ld (Opp+2),a
    call OppTurn
.h32:
    jr .h32
    ENDIF
    IF TESTMODE == 31
    ; band DeltaBlit (zip path): full-paint a board, change a TABLE card (band rows 8..15 only),
    ; re-render with the band delta. screen must == shadow EVERYWHERE (band updated, rest intact).
    call NewMatch
    call NewRound
    call PaintAll                ; full paint -> screen == shadow
    ld a,(Table)
    inc a
    ld (Table),a                 ; mutate a table card -> only the band changes
    call RenderShadow
    xor a
    ld (ScrOfs),a
    ld a,8
    ld (DBstart),a               ; band rows 8..15
    ld a,16
    ld (DBend),a
    call DeltaBlit
.h31:
    jr .h31
    ENDIF
    IF TESTMODE == 30
    ; slide ease-out timing: time one SlideIn via FRAMES. Base = ~9 HALTs (1 initial + 8 steps);
    ; SlEaseTab [0,0,0,0,0,1,1,2] adds 4 -> expect ~13 frames. Driver reads Options as the count.
    call NewMatch
    call NewRound
    call PaintAll
    ld a,6
    ld (SlHandCol),a
    ld a,13
    ld (SlDestCol),a
    ld a,16
    ld (SlRow),a
    ld a,0xFF
    ld (SlRowStep),a             ; player slide: rows 16 -> 8
    ld a,5
    ld (Played),a
    ld hl,0
    ld (23672),hl
    call SlideIn
    ld hl,(23672)
    ld (Options),hl
.h30:
    jr .h30
    ENDIF
    IF TESTMODE == 29
    ; DeltaBlit invariant: render board A, change it, render board B via the delta path. After
    ; PaintAll the live screen (0x4000/0x5800) must equal the shadow (0x6000/0x7800) EVERYWHERE
    ; -> the driver compares the two regions byte-for-byte (any mismatch = a missed dirty cell).
    call NewMatch
    call NewRound
    call PaintAll                ; board A
    ld a,(TableN)
    or a
    jr z,.t29
    dec a
    ld (TableN),a                ; drop a table card -> board B (several cells change + relayout)
.t29:
    ld a,(Player)
    ld (Opp),a                   ; also mutate a hand card so a hand cell changes too
    call PaintAll                ; delta A->B
.h29:
    jr .h29
    ENDIF
    IF TESTMODE == 28
    ; opening-leader alternation: call NewMatch 6x, log Leader each time into Options[].
    ; Expect X,!X,X,!X,X,!X (X = the boot random opening leader).
    ld hl,Options
    ld b,6
.l28:
    push bc
    push hl
    call NewMatch
    pop hl
    ld a,(Leader)
    ld (hl),a
    inc hl
    pop bc
    djnz .l28
.h28:
    jr .h28
    ENDIF
    IF TESTMODE == 27
    ; EraseCardRegion correctness: paint a board (screen + shadow), stamp a card onto the LIVE
    ; SCREEN only at cell (13,8), then EraseCardRegion it. The screen region must be restored to
    ; the shadow background -> the driver reads screen vs shadow for the whole 6x8 card and they
    ; must byte-match. Deterministic; no deal randomness needed.
    call NewMatch
    call NewRound
    call PaintAll
    xor a
    ld (ScrOfs),a
    ld d,13
    ld e,8
    ld a,5
    call BlitCard                ; stray card on the screen only
    ld d,13
    ld e,8
    call EraseCardRegion         ; restore from shadow
.h27:
    jr .h27
    ENDIF
    IF TESTMODE == 8
    ; full table (7 cards) + a played card capturing one -> inspect ShowCapture layout
    ld hl,Table
    ld (hl),0
    inc hl
    ld (hl),11
    inc hl
    ld (hl),22
    inc hl
    ld (hl),33
    inc hl
    ld (hl),4
    inc hl
    ld (hl),15
    inc hl
    ld (hl),26
    ld a,7
    ld (TableN),a
    ld a,16
    ld (Played),a
    ld hl,CapSel
    ld b,16
    xor a
.c8:
    ld (hl),a
    inc hl
    djnz .c8
    ld a,1
    ld (CapSel+2),a              ; pretend card index 2 is captured
    call ShowCapture
.h8:
    jr .h8
    ENDIF
    IF TESTMODE == 7
    ; replicate PlayerTurn .play with a known card (id 23, value 4) that must DROP.
    ; Verifies the card id survives the HumanTurn write -> table gets id 23, not 0.
    ld a,23
    ld (Player),a
    ld a,0xFF
    ld (Player+1),a
    ld (Player+2),a
    ld a,8                       ; table = [9 of denari] (value 9) -> no capture
    ld (Table),a
    ld a,1
    ld (TableN),a
    xor a
    ld (Cursor),a
    ld a,(Cursor)
    ld hl,Player
    call addHLA
    ld a,(hl)
    ld (hl),0xFF
    push af
    xor a
    ld (HumanTurn),a
    pop af
    ld c,0
    call ResolvePlay
.h7:
    jr .h7
    ENDIF
    IF TESTMODE == 6
    ; PPile = coins A,2,3,4,5 (ids 0..4), no 6 -> napola should be 5
    ld hl,PPile
    ld (hl),0
    inc hl
    ld (hl),1
    inc hl
    ld (hl),2
    inc hl
    ld (hl),3
    inc hl
    ld (hl),4
    ld a,5
    ld (PPileN),a
    xor a
    call Napola
    ld (Tmp0),a
    call ShowNeapolitan
.h6:
    jr .h6
    ENDIF
    IF TESTMODE == 5
    ; table=[10] (value 10); AI hand=[settebello, 2denari, 2coppe] -> all must drop.
    ; AI must NOT drop the settebello: best is the coppe 2 (slot 2).
    ld a,9                       ; 10 of denari (value 10)
    ld (Table),a
    ld a,1
    ld (TableN),a
    ld a,6                       ; settebello
    ld (Opp),a
    ld a,1                       ; 2 of denari
    ld (Opp+1),a
    ld a,11                      ; 2 of coppe
    ld (Opp+2),a
    call aiSelectPlay
    ld (Tmp0),a
.h5:
    jr .h5
    ENDIF
    IF TESTMODE == 43
    ; STRENGTH: Esperto(Opp) vs Hard(Player), 30 matches (FastSim, per-side difficulty via
    ; SimMixed). Esperto should win clearly more than half. 0x7E0B Hard wins, 0x7E0C Esperto, 0x7E0D done.
    ld a,1
    ld (0x7E20),a                ; SimMixed on
    ld a,3
    ld (0x7E21),a                ; opp = Esperto
    ld a,2
    ld (0x7E22),a                ; player = Hard
    ld a,1
    ld (AceRule),a
    ld (DemoMode),a
    ld (FastSim),a
    xor a
    ld (0x7E0B),a
    ld (0x7E0C),a
    ld (0x7E0D),a
    ld b,30
.ml43:
    push bc
    call NewMatch
.fmr43:
    call NewRound
    call PlayRound
    call ScoreRound
    ld a,(PMatch)
    cp 11
    jr nc,.fme43
    ld a,(OMatch)
    cp 11
    jr nc,.fme43
    ld a,(Leader)
    xor 1
    ld (Leader),a
    jr .fmr43
.fme43:
    ld a,(OMatch)
    ld c,a
    ld a,(PMatch)
    cp c
    jr c,.ow43                   ; PMatch < OMatch -> Esperto(opp) win
    jr z,.dn43
    ld hl,0x7E0B                 ; Hard(player) win
    inc (hl)
    jr .dn43
.ow43:
    ld hl,0x7E0C                 ; Esperto win
    inc (hl)
.dn43:
    ld hl,0x7E0D
    inc (hl)
    pop bc
    djnz .ml43
.h43:
    jr .h43
    ENDIF
    IF TESTMODE == 42
    ; SKILL MENU render + key wiring: show SelectDifficulty, then key 4 should set Difficulty=3.
    ; -> 0x7E10 = chosen Difficulty.
    im 1
    ei
    call SelectDifficulty
    ld a,(Difficulty)
    ld (0x7E10),a
.h42:
    jr .h42
    ENDIF
    IF TESTMODE == 44
    ; DEAL CASCADE: deal a board, snapshot it, run the cascade, confirm every dealt card came
    ; back (none lost/duplicated). 0x7E2B = mismatch count (exp 0). Screenshot = final board.
    call NewMatch
    call NewRound
    ld hl,Player
    ld de,0x7E20
    ld bc,3
    ldir
    ld hl,Opp
    ld bc,3
    ldir
    ld hl,Table
    ld bc,4
    ldir                         ; 0x7E20..29 = dealt [P0-2 O0-2 T0-3]
    call DealCascade
    xor a
    ld (0x7E2B),a
    ld hl,Player
    ld de,0x7E20
    ld b,3
    call .cmp44
    ld hl,Opp
    ld de,0x7E23
    ld b,3
    call .cmp44
    ld hl,Table
    ld de,0x7E26
    ld b,4
    call .cmp44
    call RenderShadow            ; render the correct board to shadow; screen (direct-drawn)
    xor a                        ; should already equal it -> positions match RenderShadow exactly
    ld (ScrOfs),a
.h44:
    jr .h44
.cmp44:
    ld a,(de)
    cp (hl)
    jr z,.cm44n
    push hl
    ld hl,0x7E2B
    inc (hl)
    pop hl
.cm44n:
    inc hl
    inc de
    djnz .cmp44
    ret
    ENDIF
    IF TESTMODE == 41
    ; ESPERTO INTEGRATION: play 16 full Esperto-vs-Esperto matches (FastSim) through the REAL
    ; turn loop (PlayRound -> OppTurn/DemoPlayerTurn -> aiSelectPlay -> EndgameSearch -> ResolvePlay).
    ; Both sides Difficulty 3 -> exercises the search for RootWho 0 AND 1. Completing all 16 proves
    ; integration (no hang/desync). 0x7E0B player wins, 0x7E0C opp, 0x7E0D matches done.
    ld a,3
    ld (Difficulty),a
    ld a,1
    ld (AceRule),a
    ld (DemoMode),a
    ld (FastSim),a
    xor a
    ld (0x7E0B),a
    ld (0x7E0C),a
    ld (0x7E0D),a
    ld b,16
.ml41:
    push bc
    call NewMatch
.fmr41:
    call NewRound
    call PlayRound
    call ScoreRound
    ld a,(PMatch)
    cp 11
    jr nc,.fme41
    ld a,(OMatch)
    cp 11
    jr nc,.fme41
    ld a,(Leader)
    xor 1
    ld (Leader),a
    jr .fmr41
.fme41:
    ld a,(OMatch)
    ld c,a
    ld a,(PMatch)
    cp c
    jr c,.ow41                   ; PMatch < OMatch -> opp win
    jr z,.dn41                   ; tie (rare) -> count neither
    ld hl,0x7E0B                 ; player win
    inc (hl)
    jr .dn41
.ow41:
    ld hl,0x7E0C
    inc (hl)
.dn41:
    ld hl,0x7E0D
    inc (hl)
    pop bc
    djnz .ml41
.h41:
    jr .h41
    ENDIF
    IF TESTMODE == 40
    ; ENDGAME minimax depth-6 STRESS: full 3v3 final round, 3-card table with multi-option
    ; captures (heavy branching). Confirms no hang/stack-overflow + measures search frames.
    ; 0x7E10 BestSlot(0..2) 0x7E11 AIOpt 0x7E12 frames-elapsed(16) 0x7E14 TableN(exp 3)
    ; 0x7E15..17 Opp restored (exp 24,17,0).
    im 1
    ei
    ld a,3
    ld (Difficulty),a
    xor a
    ld (AceRule),a
    ld (PPileN),a
    ld (OPileN),a
    ld (PScopa),a
    ld (OScopa),a
    ld a,1
    ld (LastCap),a
    ld a,40
    ld (DeckPos),a
    ld a,1                        ; table = [2den, 3coppe, 5coppe]
    ld (Table),a
    ld a,12
    ld (Table+1),a
    ld a,14
    ld (Table+2),a
    ld a,3
    ld (TableN),a
    ld a,24                       ; Opp = [5spade, 8coppe, ace-den]
    ld (Opp),a
    ld a,17
    ld (Opp+1),a
    ld a,0
    ld (Opp+2),a
    ld a,21                       ; Player = [2spade, 7coppe, 4coppe]
    ld (Player),a
    ld a,16
    ld (Player+1),a
    ld a,13
    ld (Player+2),a
    ld hl,Opp
    ld (HandPtr),hl
    ld hl,(23672)
    ld (0x7E16),hl
    call aiSelectPlay
    ld (0x7E10),a
    ld a,(AIOpt)
    ld (0x7E11),a
    ld hl,(23672)
    ld de,(0x7E16)
    or a
    sbc hl,de
    ld (0x7E12),hl
    ld a,(TableN)
    ld (0x7E14),a
    ld hl,(Opp)
    ld (0x7E15),hl
    ld a,(Opp+2)
    ld (0x7E17),a
.h40:
    jr .h40
    ENDIF
    IF TESTMODE == 39
    ; ENDGAME minimax (basic correctness + state restoration). Deck empty; AI=Opp can grab
    ; the settebello with its 7. Table=[settebello]. Opp=[7coppe,2den,3coppe].
    ; Player=[3den,4coppe,8coppe] (no 7). Optimal: slot 0 (the 7) captures the settebello.
    ; results -> 0x7E10 BestSlot(exp 0), 0x7E11 AIOpt(exp 0),
    ; 0x7E12 TableN(exp 1), 0x7E13 PPileN(exp 0), 0x7E14 OPileN(exp 0),
    ; 0x7E15..17 Opp[] restored (exp 16,1,12).
    ld a,3
    ld (Difficulty),a
    xor a
    ld (AceRule),a
    ld (PPileN),a
    ld (OPileN),a
    ld (PScopa),a
    ld (OScopa),a
    ld (LastCap),a
    ld a,40
    ld (DeckPos),a
    ld a,6
    ld (Table),a
    ld a,1
    ld (TableN),a
    ld a,16
    ld (Opp),a
    ld a,1
    ld (Opp+1),a
    ld a,12
    ld (Opp+2),a
    ld a,2
    ld (Player),a
    ld a,13
    ld (Player+1),a
    ld a,17
    ld (Player+2),a
    ld hl,Opp
    ld (HandPtr),hl
    call aiSelectPlay
    ld (0x7E10),a
    ld a,(AIOpt)
    ld (0x7E11),a
    ld a,(TableN)
    ld (0x7E12),a
    ld a,(PPileN)
    ld (0x7E13),a
    ld a,(OPileN)
    ld (0x7E14),a
    ld hl,(Opp)
    ld (0x7E15),hl
    ld a,(Opp+2)
    ld (0x7E17),a
.h39:
    jr .h39
    ENDIF
    IF TESTMODE == 38
    ; card-counting helpers: mark all four 5s + three 7s (leave the 7 of suit 3 unseen).
    ; expect UnseenOfValue(5)=0, (7)=1, (3)=4  -> 0x7E10..0x7E12.
    call ClearSeen
    ld a,4
    call MarkSeen                 ; 5 of denari (value 5 -> id 4)
    ld a,14
    call MarkSeen
    ld a,24
    call MarkSeen
    ld a,34
    call MarkSeen                 ; all four 5s seen
    ld a,6
    call MarkSeen                 ; 7 of denari
    ld a,16
    call MarkSeen
    ld a,26
    call MarkSeen                 ; three 7s seen (id 36 left unseen)
    ld a,5
    call UnseenOfValue
    ld (0x7E10),a
    ld a,7
    call UnseenOfValue
    ld (0x7E11),a
    ld a,3
    call UnseenOfValue
    ld (0x7E12),a
.h38:
    jr .h38
    ENDIF
    IF TESTMODE == 0
    xor a
    out (254),a                  ; black border behind the loading/title art
    ld (BorderC),a
    ld (ScrOfs),a                ; default: render straight to the screen
    ld (AceRule),a               ; optional ace-takes-all rule defaults OFF
    ld a,1
    ld (Difficulty),a            ; default medium
    ld a,r
    ld (Seed),a
    ld a,(23672)
    ld (Seed+1),a
    ld b,6
    call Delay                   ; hold the loading screen >= ~3s (min display)
    call ShowTitle               ; show the title ONCE at boot (its RLE source @0x6000 is intact only now)
    jp NewGame                   ; -> skill menu -> match
    ENDIF

; =================== match / round ===================
RunMatch:
    call NewMatch
.round:
    call NewRound
    call DealCascade             ; deal the board in one card at a time (tear-free)
    call PlayRound
    call ScoreRound
    ld a,(Pnapola)
    ld b,a
    ld a,(Onapola)
    or b
    call nz,ShowNeapolitan       ; brief NEAPOLITAN screen + rising scale
    call ShowResults
    call WaitSpaceOrDemo
    ld a,(Leader)                ; the deal alternates each round
    xor 1
    ld (Leader),a
    ld a,(PMatch)
    ld c,a
    ld a,(OMatch)
    ld b,a
    ld a,c
    cp 11
    jr nc,.maybe
    ld a,b
    cp 11
    jr nc,.maybe
    jr .round
.maybe:
    ld a,c
    cp b
    jr z,.round                  ; tie at/over 11 -> another round
    jr nc,.pwon
    call ShowWinOpp
    call WaitSpaceOrDemo
    ld a,0xFE                    ; hidden: hold SHIFT at the play-again prompt -> back to the title menu
    in a,(0xFE)                  ; read the CAPS-SHIFT half-row (0xFEFE)
    bit 0,a                      ; CAPS SHIFT: 0 = pressed
    jp z,NewGame
    jr RunMatch
.pwon:
    call ShowWinYou
    call WaitWinner              ; tricolore border shimmer until SPACE
    ld a,0xFE                    ; hidden: hold SHIFT at the play-again prompt -> back to the title menu
    in a,(0xFE)
    bit 0,a                      ; CAPS SHIFT: 0 = pressed
    jp z,NewGame
    jr RunMatch

NewGame:                         ; skill/rules menu -> new match. The hidden SHIFT+SPACE returns
                                 ; HERE, NOT to ShowTitle: the title's compressed source at 0x6000
                                 ; is overwritten by the gameplay shadow buffer, so re-decompressing
                                 ; it after a game would render garbage / crash. SelectDifficulty
                                 ; draws itself from scratch (its own "SCOPA / SELECT SKILL LEVEL").
    xor a
    out (254),a                  ; black border behind the menu
    ld (BorderC),a
    call SelectDifficulty
    jp RunMatch

; EnterDemo: 25s idle on the title -> attract / self-play demo (CPU vs CPU, Esperto + asso piglia
; tutto, silent). Loops forever until the watcher presses SPACE.
EnterDemo:
    ld a,3
    ld (Difficulty),a            ; Esperto (shows off the card-counting AI)
    ld a,1
    ld (AceRule),a               ; asso piglia tutto on
    ld (DemoMode),a              ; demo on (also forces sound off via SoundEnabled)
    jp RunMatch

; DemoCheckSpace: during the demo, a SPACE press abandons the throwaway match and returns to
; the skill menu. No-op outside the demo. Called from the pacing Delays / slide / result waits.
DemoCheckSpace:
    ld a,(DemoMode)
    or a
    ret z                        ; not in demo -> nothing to do
    ld a,0x7F
    in a,(0xFE)                  ; 0x7FFE half-row: SPACE = bit 0 (0 = pressed)
    bit 0,a
    ret nz                       ; SPACE not pressed
    ld sp,0xBFF0                 ; SPACE -> abandon the in-progress match (it's throwaway)
    xor a
    ld (DemoMode),a
    jp NewGame                   ; -> skill menu, ready for the human

; WaitSpaceOrDemo: in the demo, hold the screen ~10s (SPACE exits via DemoCheckSpace) then
; return so the demo plays on; otherwise behave exactly like WaitSpace.
WaitSpaceOrDemo:
    ld a,(DemoMode)
    or a
    jp z,WaitSpace
    ld hl,0
    ld (23672),hl                ; zero the ROM frame counter
.dw:
    halt
    call DemoCheckSpace          ; SPACE -> leaves the demo (never returns)
    ld hl,(23672)
    ld de,500                    ; 10s @ 50 Hz
    or a
    sbc hl,de
    jr c,.dw
    ret

; DemoOverlay: in attract/demo mode, a thin top banner telling the watcher how to take
; over. Drawn into the current render target (the shadow buffer during RenderShadow), so
; Blit carries it onto the board with everything else. No-op outside the demo.
DemoOverlay:
    ld a,(DemoMode)
    or a
    ret z
    ld a,(ScrOfs)                ; attribute strip on row 0, cols 4..27 -> a tidy HUD bar
    add a,0x58                   ; 0x58 (live screen) or 0x78 (shadow)
    ld h,a
    ld l,4
    ld b,24
.attr:
    ld (hl),0x47                 ; bright white ink on black paper
    inc hl
    djnz .attr
    ld hl,StrDemoPrompt          ; centred within the bar
    ld d,6
    ld e,0
    jp PrintStr
StrDemoPrompt: defb "PRESS SPACE TO PLAY",0

NewMatch:
    ld a,5
    out (254),a                  ; cyan border for the game proper
    ld (BorderC),a
    xor a
    ld (PMatch),a
    ld (OMatch),a
    ld a,(OpenLeader)            ; opening leader: random for match 1 (set at boot),
    ld (Leader),a                ; then alternating each match this session
    xor 1
    ld (OpenLeader),a            ; flip for the next match
    ret

NewRound:
    xor a
    ld (PPileN),a
    ld (OPileN),a
    ld (PScopa),a
    ld (OScopa),a
    ld (Cursor),a
    ld (LastCap),a
    call InitDeck
    call Shuffle
    call DealRound
    call ClearSeen               ; the AI sees the table + its own hand
    ld hl,Table
    ld b,4
    call MarkCards
    ld hl,Opp
    ld b,3
    call MarkCards
    ret

PlayRound:
.l:
    ld a,(Leader)
    or a
    jr nz,.oppfirst
    call CountPlayer
    or a
    call nz,PlayerTurn
    call CountOpp
    or a
    call nz,OppTurn
    jr .chk
.oppfirst:
    call CountOpp
    or a
    call nz,OppTurn
    call CountPlayer
    or a
    call nz,PlayerTurn
.chk:
    call CountPlayer
    ld b,a
    call CountOpp
    add a,b
    or a
    jr nz,.l
    ld a,(DeckPos)
    cp 40
    jr nc,.end
    call DealHands
    call DealRevealHands         ; cascade the 6 new hand cards in (tear-free), table stays
    jr .l
.end:
    call SweepToLast
    ret

; =================== player turn ===================
PlayerTurn:
    ld a,(DemoMode)
    or a
    jp nz,DemoPlayerTurn        ; attract demo -> the CPU plays the player's hand too
    ld a,1
    ld (HumanTurn),a            ; the player's card may flash now
    call FixCursor
    call PaintAll                ; full paint once per turn (not per cursor move)
.drain:
    call ReadKeys
    or a
    jr nz,.drain
.wait:
    call ReadKeys
    or a
    jr z,.wait
    ld e,a
.rel:
    call ReadKeys
    or a
    jr nz,.rel
    bit 2,e
    jr nz,.play
    bit 0,e
    jr nz,.left
    bit 1,e
    jr nz,.right
    jr .wait
.left:                           ; attr-only highlight move -> no flicker
    call UnhighlightCursor
    call CursorPrev
    call HighlightCursor
    jr .wait
.right:
    call UnhighlightCursor
    call CursorNext
    call HighlightCursor
    jr .wait
.play:
    ld a,(Cursor)
    ld hl,Player
    call addHLA
    ld a,(hl)
    cp 0xFF
    jr z,.wait
    ld (Played),a                ; keep the card IN the hand for now (no table overlap while choosing)
    ; resolve the capture choice while the card is still in your hand
    ld a,(Played)
    call valueOf
    call findAllCaptures
    xor a
    ld (ChoiceMade),a            ; default: nothing pre-chosen
    ld a,(OptionN)
    cp 2
    jr c,.commit                 ; 0/1 options -> nothing to choose
    call PlayerChooseCapture     ; pick now; played card stays shown (flashing) in your hand
    ld (ChoiceVal),a
    ld a,1
    ld (ChoiceMade),a
.commit:
    ld a,(OptionN)
    or a
    jr z,.doslide                ; a drop (no capture) must land on the table -> slide
    ld a,(TableN)
    cp 6
    jr c,.doslide                ; table not crowded -> slide as usual
    ; --- crowded-table capture: keep the card FLASHING IN YOUR HAND, no slide onto the clutter ---
    ld a,(ChoiceMade)
    or a
    jr z,.kih0
    ld a,(ChoiceVal)             ; multi: the chosen option index
    jr .kihshow
.kih0:
    xor a                        ; single capture: the only option
.kihshow:
    call MaskToCapSel            ; CapSel = the captured set
    call PaintAll                ; card is still in your hand -> drawn there
    call HighlightCursor         ; flash it in the hand
    call FlashCaptured           ; flash the table cards it takes
    ld hl,CaptureJingle
    call PlayJingle
    ld b,2
    call Delay
    ld a,(Cursor)                ; now remove it and resolve (no slide, no on-table show)
    ld hl,Player
    call addHLA
    ld (hl),0xFF
    xor a
    ld (HumanTurn),a
    ld a,1
    ld (RevealInPlace),a
    ld a,(Played)
    ld c,0
    call ResolvePlay
    xor a
    ld (RevealInPlace),a
    call FixCursor
    call PaintAll
    ret
.doslide:
    ld a,(Cursor)                ; now take the card out of the hand and slide it to the table
    ld hl,Player
    call addHLA
    ld (hl),0xFF
    xor a
    ld (HumanTurn),a            ; stop the cursor flashing as the play resolves
    ld a,(Cursor)
    call HandCol
    ld (SlHandCol),a
    ld a,16
    ld (SlRow),a
    ld a,0xFF                    ; -1 cell/step (rows 16 -> 8, 8 smooth synced steps)
    ld (SlRowStep),a
    ld a,(TableN)
    call TableSlotCol
    ld (SlDestCol),a
    call SlideIn
    ld a,(Played)
    ld c,0
    call ResolvePlay
    call FixCursor               ; move cursor off the now-empty slot before repaint
    call PaintAll
    ret

FixCursor:
    ld a,(Cursor)
    ld hl,Player
    call addHLA
    ld a,(hl)
    cp 0xFF
    ret nz
CursorNext:
    ld a,(Cursor)
    ld b,3
.cn:
    inc a
    cp 3
    jr c,.ck
    xor a
.ck:
    ld c,a
    ld hl,Player
    call addHLA
    ld a,(hl)
    cp 0xFF
    jr nz,.found
    ld a,c
    djnz .cn
    ret
.found:
    ld a,c
    ld (Cursor),a
    ret

CursorPrev:
    ld a,(Cursor)
    ld b,3
.cp:
    dec a
    jp p,.ck
    ld a,2
.ck:
    ld c,a
    ld hl,Player
    call addHLA
    ld a,(hl)
    cp 0xFF
    jr nz,.found
    ld a,c
    djnz .cp
    ret
.found:
    ld a,c
    ld (Cursor),a
    ret

; =================== opponent (AI v0) ===================
OppTurn:
    ld hl,Opp
    ld (HandPtr),hl             ; AI evaluates the opponent's hand
    xor a
    ld (HumanTurn),a            ; CPU's turn -> the player's card must not flash
    call PaintAll
    ld b,1
    call Delay
    call aiSelectPlay            ; A = best slot, sets AIOpt
    push af                      ; save the played slot
    ld hl,Opp
    call addHLA
    ld a,(hl)
    ld (hl),0xFF                 ; remove the played card -> leaves a gap at that slot
    ld (Played),a
    pop af                       ; the played slot
    call HandCol                 ; CPU backs are drawn at their REAL slot columns (with gaps,
    ld (SlHandCol),a             ; like the player's hand), so slide from the card's true slot
    ; --- crowded-table capture? turn the card FACE-UP IN PLACE at its slot, don't slide ---
    ld a,(Played)
    call valueOf
    call findAllCaptures          ; Options[]/OptionN for the played card
    ld a,(OptionN)
    or a
    jr z,.oppslide                ; a drop must land on the table -> slide
    ld a,(TableN)
    cp 6
    jr c,.oppslide                ; not crowded -> slide as usual
    ld a,(AIOpt)
    call MaskToCapSel             ; CapSel = the captured set
    call PaintAll                 ; board with the opp slot now a gap
    ld a,(SlHandCol)
    ld d,a
    ld e,0
    ld a,(Played)
    call BlitCard                 ; reveal the played card face-up at its slot (top row)
    ld a,(SlHandCol)
    ld d,a
    ld e,0
    call FlashCardRegion          ; flash it in place
    call FlashCaptured            ; flash the table cards it takes
    ld hl,CaptureJingle
    call PlayJingle
    ld b,2
    call Delay
    ld a,1
    ld (RevealInPlace),a
    ld a,(Played)
    ld c,1
    call ResolvePlay
    xor a
    ld (RevealInPlace),a
    call PaintAll
    ld b,1
    call Delay
    ret
.oppslide:
    xor a
    ld (SlRow),a                 ; rows 0 -> 8 (CPU hand at top, 8 smooth synced steps)
    ld a,1
    ld (SlRowStep),a
    ld a,(TableN)
    call TableSlotCol
    ld (SlDestCol),a
    call SlideIn
    ld a,(Played)
    ld c,1
    call ResolvePlay
    call PaintAll
    ld b,1
    call Delay
    ret

; DemoPlayerTurn: in the attract demo the CPU plays the PLAYER's hand too. Mirrors OppTurn but
; evaluates Player[] (HandPtr), slides from the bottom row, and routes the capture through the
; PLAYER path (Who=0) -- so its captured cards go to the player's pile. ResolvePlay's player path
; uses ChoiceMade/ChoiceVal (no human here), so we feed it the AI's chosen option (AIOpt).
DemoPlayerTurn:
    ld hl,Player
    ld (HandPtr),hl             ; AI evaluates the player's hand
    xor a
    ld (HumanTurn),a
    call PaintAll
    ld b,1
    call Delay
    call aiSelectPlay            ; A = best slot, sets AIOpt
    ld a,(AIOpt)
    ld (ChoiceVal),a             ; feed the AI's capture choice into the player path
    ld a,1
    ld (ChoiceMade),a
    ld a,(BestSlot)
    ld (Cursor),a                ; point the cursor at the played card (for the in-hand flash)
    ld hl,Player
    ld a,(BestSlot)
    call addHLA
    ld a,(hl)
    ld (Played),a                ; the played card value (still in the hand for now)
    ; --- crowded-table capture? keep the card flashing IN HAND like a human play, no slide ---
    ld a,(Played)
    call valueOf
    call findAllCaptures
    ld a,(OptionN)
    or a
    jr z,.demoslide              ; drop -> slide
    ld a,(TableN)
    cp 6
    jr c,.demoslide              ; not crowded -> slide
    ld a,(AIOpt)
    call MaskToCapSel            ; CapSel = captured set
    ld a,1
    ld (HumanTurn),a             ; let HighlightCursor flash the in-hand card
    call PaintAll                ; card still in Player[BestSlot] -> drawn in the hand
    call HighlightCursor
    call FlashCaptured
    ld hl,CaptureJingle
    call PlayJingle
    ld b,2
    call Delay
    xor a
    ld (HumanTurn),a
    ld a,(BestSlot)              ; now remove it and resolve (no slide, no on-table show)
    ld hl,Player
    call addHLA
    ld (hl),0xFF
    ld a,1
    ld (RevealInPlace),a
    ld a,(Played)
    ld c,0
    call ResolvePlay
    xor a
    ld (RevealInPlace),a
    call PaintAll
    ld b,1
    call Delay
    ret
.demoslide:
    ld a,(BestSlot)
    ld hl,Player
    call addHLA
    ld (hl),0xFF
    ld a,(BestSlot)
    call HandCol
    ld (SlHandCol),a
    ld a,16
    ld (SlRow),a                 ; player hand at the bottom (rows 16 -> 8)
    ld a,0xFF
    ld (SlRowStep),a
    ld a,(TableN)
    call TableSlotCol
    ld (SlDestCol),a
    call SlideIn
    ld a,(Played)
    ld c,0                       ; Who = player
    call ResolvePlay
    call PaintAll
    ld b,1
    call Delay
    ret

; ===== strong AI: weighted evaluation of every legal play =====
; Mirrors ai.js (medium: sweep-avoidance on). MY suit convention: denari=ids0-9,
; settebello=id6. Scores are signed 16-bit in ScoreW.
aiSelectPlay:                    ; -> A = chosen hand slot; sets AIOpt
    IF FASTSIM
    ld a,(0x7E20)                ; SimMixed: head-to-head sim sets Difficulty per side
    or a
    jr z,.nomix
    ld hl,(HandPtr)
    ld de,Opp
    or a
    sbc hl,de
    jr z,.mixopp
    ld a,(0x7E22)               ; player side difficulty
    jr .setmix
.mixopp:
    ld a,(0x7E21)               ; opp side difficulty
.setmix:
    ld (Difficulty),a
.nomix:
    ENDIF
    ld a,(Difficulty)
    cp 3
    jr nz,.heur                  ; not Esperto -> weighted heuristic
    ld a,(DeckPos)
    cp 40
    jp nc,EndgameSearch          ; Esperto + deck empty -> exact endgame minimax (sets AIOpt, rets)
.heur:
    ld hl,0x8000
    ld (BestScoreW),hl           ; -32768
    ld a,0xFF
    ld (BestSlot),a
    ld (BestOpt),a
    xor a
    ld (AISlot),a
.slot:
    ld hl,(HandPtr)              ; the hand being evaluated (Opp, or Player in the demo)
    ld a,(AISlot)
    call addHLA
    ld a,(hl)
    cp 0xFF
    jp z,.nextslot
    ld (AICardId),a
    call valueOf
    call findAllCaptures
    ld a,(OptionN)
    or a
    jr z,.drop
    xor a
    ld (AIOptEval),a
.opt:
    ld hl,0
    ld (ScoreW),hl
    ld a,(AIOptEval)
    call EvalCapture
    call ConsiderBest
    ld a,(AIOptEval)
    inc a
    ld (AIOptEval),a
    ld hl,OptionN
    cp (hl)
    jr c,.opt
    jr .nextslot
.drop:
    ld hl,0
    ld (ScoreW),hl
    call EvalDrop
    ld a,0xFF
    ld (AIOptEval),a
    call ConsiderBest
.nextslot:
    ld a,(AISlot)
    inc a
    ld (AISlot),a
    cp 3
    jp c,.slot
    ld a,(BestOpt)
    ld (AIOpt),a
    ld a,(BestSlot)
    ret

; ============================================================================
; Esperto endgame: exact minimax (alpha-beta) of the final round.
; Entered from aiSelectPlay when Difficulty==3 and the deck is empty. The unseen cards
; are exactly the opponent's hand, so the search reads the real Player[]/Opp[] arrays and
; drives the SAME rules engine (findAllCaptures/AddToPile/CompactTable/ScoreRound) via
; make/unmake. Values are signed bytes = (RootWho's round points - the other's); +-100 = INF.
; Each recursion level owns a 32-byte frame in Frames[]: [0..15]=Table snapshot,
; 16=TableN 17=PPileN 18=OPileN 19=PScopa 20=OScopa 21=LastCap 23=played card,
; 24=this node's side, 25=slot, 26=optMax, 27=opt, 28=alpha, 29=beta.
; ============================================================================
EndgameSearch:                   ; -> A = best slot; sets AIOpt (same contract as aiSelectPlay)
    ld hl,(HandPtr)
    ld de,Opp
    or a
    sbc hl,de
    ld a,0
    jr nz,.rwset                 ; HandPtr != Opp -> player side (RootWho 0)
    inc a                        ; HandPtr == Opp -> RootWho 1
.rwset:
    ld (RootWho),a
    ld (Who),a                   ; root: side to move
    xor a
    ld (CurDepth),a
    call FramePtrIX
    ld a,(Who)
    ld (ix+24),a
    ld a,0x9C                    ; -100 (alpha = -INF)
    ld (ix+28),a
    ld a,100                     ; beta = +INF
    ld (ix+29),a
    ld a,0xFF
    ld (BestSlot),a
    ld (BestOpt),a
    call SearchNode              ; explores depth 0 (max node); records BestSlot/BestOpt
    ld a,(BestOpt)
    ld (AIOpt),a
    ld a,(BestSlot)
    ret

; SearchNode: position with (Who) to move; frame[CurDepth].alpha/beta preset. -> A = value.
SearchNode:
    call FramePtrIX
    ld a,(Who)
    ld (ix+24),a
    call CurHandPtr
    ld a,(hl)
    inc hl
    and (hl)
    inc hl
    and (hl)
    inc a                        ; all three 0xFF -> 0 (hand empty)
    jp nz,.notleaf
    jp LeafEval                  ; terminal -> score; returns A
.notleaf:
    call FramePtrIX
    xor a
    ld (ix+25),a                 ; slot = 0
.slotloop:
    call FramePtrIX
    call CurHandPtr
    ld a,(ix+25)
    call addHLA
    ld a,(hl)
    cp 0xFF
    jp z,.nextslot
    call valueOf
    call findAllCaptures
    call FramePtrIX
    ld a,(OptionN)
    ld (ix+26),a
    or a
    jr nz,.opts
    ld a,0xFF
    ld (ix+27),a                 ; no captures -> single DROP move
    call .domove
    call FramePtrIX
    call .cutq
    jp c,.done
    jp .nextslot
.opts:
    xor a
    ld (ix+27),a
.optloop:
    call .domove
    call FramePtrIX
    call .cutq
    jp c,.done
    call FramePtrIX
    ld a,(ix+27)
    inc a
    ld (ix+27),a
    ld b,a
    ld a,(ix+26)
    cp b
    jp nz,.optloop
.nextslot:
    call FramePtrIX
    ld a,(ix+25)
    inc a
    ld (ix+25),a
    cp 3
    jp c,.slotloop
.done:
    call FramePtrIX
    call .ismax
    jr nz,.retbeta
    ld a,(ix+28)                 ; max node -> alpha
    ret
.retbeta:
    ld a,(ix+29)                 ; min node -> beta
    ret

.ismax:                          ; Z set iff this node maximises (side == RootWho)
    ld a,(ix+24)
    ld hl,RootWho
    cp (hl)
    ret

.cutq:                           ; CF=1 iff alpha >= beta (prune)
    ld a,(ix+28)
    ld e,(ix+29)
    call SCmpAE                  ; CF=1 iff alpha < beta
    ccf
    ret

.domove:                         ; play (ix+25,ix+27), recurse, unmake, update alpha/beta
    call SimApply
    ld a,(Who)
    xor 1
    ld (Who),a                   ; child to move
    call FramePtrIX
    ld e,(ix+28)
    ld d,(ix+29)                 ; inherit window
    ld a,(CurDepth)
    inc a
    ld (CurDepth),a
    call FramePtrIX
    ld (ix+28),e
    ld (ix+29),d
    call SearchNode              ; A = child value
    push af
    ld a,(CurDepth)
    dec a
    ld (CurDepth),a
    call FramePtrIX
    ld a,(ix+24)
    ld (Who),a                   ; back to this node's side
    call SimUndo
    call FramePtrIX
    pop af
    ld c,a                       ; C = child value (preserve across .ismax)
    call .ismax
    jr nz,.updmin
    ld a,(ix+28)                 ; max: value > alpha ?
    ld e,c
    call SCmpAE                  ; CF=1 iff alpha < value
    jr nc,.duret
    ld (ix+28),c                 ; alpha = value
    ld a,(CurDepth)
    or a
    jr nz,.duret
    ld a,(ix+25)                 ; root -> record the best move
    ld (BestSlot),a
    ld a,(ix+27)
    ld (BestOpt),a
.duret:
    ret
.updmin:
    ld a,c                       ; min: value < beta ?
    ld e,(ix+29)
    call SCmpAE                  ; CF=1 iff value < beta
    jr nc,.duret
    ld (ix+29),c                 ; beta = value
    ret

; SimApply: make the move (ix+25=slot, ix+27=opt or 0xFF=drop, Who=mover). Snapshots undo.
SimApply:
    call FramePtrIX
    ld a,(TableN)
    ld (ix+16),a
    ld a,(PPileN)
    ld (ix+17),a
    ld a,(OPileN)
    ld (ix+18),a
    ld a,(PScopa)
    ld (ix+19),a
    ld a,(OScopa)
    ld (ix+20),a
    ld a,(LastCap)
    ld (ix+21),a
    push ix
    pop de
    ld hl,Table
    ld bc,16
    ldir                         ; frame[0..15] = Table[]
    call CurHandPtr
    ld a,(ix+25)
    call addHLA
    ld a,(hl)
    ld (ix+23),a                 ; save played card
    ld (hl),0xFF                 ; remove from hand
    ld a,(ix+27)
    cp 0xFF
    jr z,.drop
    ld a,(ix+23)
    call valueOf
    call findAllCaptures         ; refresh Options/AceSweepOpt (table == enumeration time)
    ld a,(ix+27)
    call MaskToCapSel
    ld a,(TableN)
    ld b,a
    ld e,0
.cap:
    ld a,e
    cp b
    jr nc,.capdone
    ld hl,CapSel
    ld a,e
    call addHLA
    ld a,(hl)
    or a
    jr z,.capn
    ld hl,Table
    ld a,e
    call addHLA
    ld a,(hl)
    push bc
    push de
    call AddToPile               ; captured card -> mover's pile (uses Who)
    pop de
    pop bc
.capn:
    inc e
    jr .cap
.capdone:
    ld a,(ix+23)
    call AddToPile               ; played card -> mover's pile
    call CompactTable
    ld a,(Who)
    ld (LastCap),a
    ld a,(TableN)
    or a
    jr nz,.amdone                ; table not cleared -> no scopa
    ld a,(AceSweepOpt)
    or a
    jr nz,.amdone                ; Scopa d'Assi -> no scopa
    call IsLastPlay
    or a
    jr nz,.amdone                ; final card of the deal -> no scopa
    ld a,(Who)
    or a
    jr nz,.osc
    ld hl,PScopa
    inc (hl)
    jr .amdone
.osc:
    ld hl,OScopa
    inc (hl)
.amdone:
    ret
.drop:
    ld a,(TableN)
    ld hl,Table
    call addHLA
    ld a,(ix+23)
    ld (hl),a
    ld hl,TableN
    inc (hl)
    ret

; SimUndo: restore the state snapshotted by SimApply (Who must be this node's side).
SimUndo:
    call FramePtrIX
    push ix
    pop hl
    ld de,Table
    ld bc,16
    ldir                         ; Table[] = frame[0..15]
    ld a,(ix+16)
    ld (TableN),a
    ld a,(ix+17)
    ld (PPileN),a
    ld a,(ix+18)
    ld (OPileN),a
    ld a,(ix+19)
    ld (PScopa),a
    ld a,(ix+20)
    ld (OScopa),a
    ld a,(ix+21)
    ld (LastCap),a
    call CurHandPtr
    ld a,(ix+25)
    call addHLA
    ld a,(ix+23)
    ld (hl),a                    ; card back into the hand slot
    ret

; LeafEval: both hands empty -> sweep remaining table to LastCap, score, return signed
; (RootWho points - other points) in A. Restores the bits ScoreRound/SweepToLast touch.
LeafEval:
    ld a,(TableN)
    ld (LfTN),a
    ld a,(PPileN)
    ld (LfPP),a
    ld a,(OPileN)
    ld (LfOP),a
    ld a,(PMatch)
    ld (LfPM),a
    ld a,(OMatch)
    ld (LfOM),a
    call SweepToLast
    call ScoreRound
    ld a,(RootWho)
    or a
    jr nz,.opp
    ld a,(PRound)
    ld hl,ORound
    sub (hl)                     ; player perspective
    jr .restore
.opp:
    ld a,(ORound)
    ld hl,PRound
    sub (hl)                     ; opp perspective
.restore:
    push af
    ld a,(LfPM)
    ld (PMatch),a
    ld a,(LfOM)
    ld (OMatch),a
    ld a,(LfTN)
    ld (TableN),a
    ld a,(LfPP)
    ld (PPileN),a
    ld a,(LfOP)
    ld (OPileN),a
    pop af
    ret

; FramePtrIX: IX = Frames + CurDepth*32. Preserves DE; clobbers A,flags.
FramePtrIX:
    ld a,(CurDepth)
    add a,a
    add a,a
    add a,a
    add a,a
    add a,a                      ; *32 (depth<=6 -> <=192)
    ld ix,Frames
    push de
    ld e,a
    ld d,0
    add ix,de
    pop de
    ret

; CurHandPtr: HL = address of (Who)'s hand.
CurHandPtr:
    ld a,(Who)
    or a
    ld hl,Player
    ret z
    ld hl,Opp
    ret

; SCmpAE: signed compare A vs E -> CF=1 iff A < E (signed); Z=1 iff equal. Clobbers A.
SCmpAE:
    sub e
    ret z
    jp pe,.ov
    jp m,.lt
    or a
    ret
.ov:
    jp p,.lt
    or a
    ret
.lt:
    scf
    ret

; AddScoreDE: ScoreW += DE (signed)
AddScoreDE:
    push hl
    ld hl,(ScoreW)
    add hl,de
    ld (ScoreW),hl
    pop hl
    ret

; ConsiderBest: if ScoreW > BestScoreW, record AISlot/AIOptEval as best.
; The first play is always taken (avoids signed overflow vs the -32768 sentinel;
; thereafter BestScoreW is bounded so the sbc compare is safe).
ConsiderBest:
    ld a,(BestSlot)
    cp 0xFF
    jr z,.take
    ld hl,(ScoreW)
    ld de,(BestScoreW)
    or a
    sbc hl,de
    jr z,.skip
    bit 7,h
    jr nz,.skip
.take:
    ld hl,(ScoreW)
    ld (BestScoreW),hl
    ld a,(AISlot)
    ld (BestSlot),a
    ld a,(AIOptEval)
    ld (BestOpt),a
.skip:
    ret

; CardBonus: A=cardid -> add capture-value bonuses
CardBonus:
    ld c,a
    cp 10
    jr nc,.nd
    ld de,5                      ; denari card
    call AddScoreDE
.nd:
    ld a,c
    cp 6
    jr nz,.ns
    ld de,35                     ; settebello captured
    call AddScoreDE
.ns:
    ld a,c
    call valueOf
    cp 7
    jr nz,.b6
    ld de,12                     ; SEVEN capture (self-play tuned, was 15)
    call AddScoreDE
    ret
.b6:
    cp 6
    jr nz,.b1
    ld de,8
    call AddScoreDE
    ret
.b1:
    cp 1
    ret nz
    ld de,6
    call AddScoreDE
    ret

; EvalCapture: A=option index -> ScoreW for taking that capture
EvalCapture:
    call MaskToCapSel
    ld a,(TableN)
    ld b,a
    ld c,0
    or a
    jr z,.cc0
    ld e,0
.cc:
    ld hl,CapSel
    ld a,e
    call addHLA
    ld a,(hl)
    or a
    jr z,.cc2
    inc c
.cc2:
    inc e
    ld a,e
    cp b
    jr c,.cc
.cc0:
    inc c                        ; + played card
    ld a,c                       ; CARD_COUNT weight = *3 (self-play tuned, was *2)
    add a,a
    add a,c
    ld e,a
    ld d,0
    call AddScoreDE
    ld a,(TableN)
    ld b,a
    ld e,0
.cb:
    ld a,e
    cp b
    jr nc,.cbd
    ld hl,CapSel
    ld a,e
    call addHLA
    ld a,(hl)
    or a
    jr z,.cb2
    ld hl,Table
    ld a,e
    call addHLA
    ld a,(hl)
    push bc
    push de
    call CardBonus
    pop de
    pop bc
.cb2:
    inc e
    jr .cb
.cbd:
    ld a,(AICardId)
    call CardBonus
    ld a,(Difficulty)
    cp 2
    call z,CardCount             ; HARD: card-counting bonus
    call BuildRemaining
    ld a,(TmpTableN)
    or a
    jr nz,.sf
    ld a,(AceSweepOpt)
    or a
    ret nz                       ; ace-sweep clears the table but scores NO scopa (Scopa d'Assi)
    ld de,50                     ; SWEEP (scopa)
    call AddScoreDE
    ret
.sf:
    ld a,(Difficulty)
    or a
    ret z                        ; EASY: no sweep-avoidance
    call EvalSafety
    ret

; CardCount: HARD-mode late-game aggression -- once most cards have been seen,
; value captures more (push to grab the remaining points). Uses Seen + CapSel.
CardCount:
    call CountUnseen
    cp 16
    ret nc                       ; >=16 unseen -> early game, no bonus
    ; +1 per captured card (CapSel popcount + the played card)
    ld a,(TableN)
    ld b,a
    ld c,1                       ; +1 for the played card
    or a
    jr z,.cadd
    ld e,0
.ccl:
    ld hl,CapSel
    ld a,e
    call addHLA
    ld a,(hl)
    or a
    jr z,.ccn
    inc c
.ccn:
    inc e
    ld a,e
    cp b
    jr c,.ccl
.cadd:
    ld e,c
    ld d,0
    call AddScoreDE
    ret

; CountUnseen: A = 40 - popcount(Seen)
CountUnseen:
    ld hl,Seen
    ld b,5
    ld c,0
.cu:
    ld a,(hl)
    ld d,8
.cb:
    rra
    jr nc,.cn
    inc c
.cn:
    dec d
    jr nz,.cb
    inc hl
    djnz .cu
    ld a,40
    sub c
    ret

; ClearSeen: zero the 40-bit seen set
ClearSeen:
    ld hl,Seen
    ld b,5
    xor a
.cs:
    ld (hl),a
    inc hl
    djnz .cs
    ret

; MarkSeen: A = card id -> set its seen bit
MarkSeen:
    ld c,a
    srl a
    srl a
    srl a                        ; byte index
    ld hl,Seen
    call addHLA
    ld a,c
    and 7
    ld b,a
    ld a,1
    inc b
.ms:
    dec b
    jr z,.set
    add a,a
    jr .ms
.set:
    or (hl)
    ld (hl),a
    ret

; MarkCards: HL=ptr, B=count -> mark each as seen
MarkCards:
    ld a,(hl)
    push hl
    push bc
    call MarkSeen
    pop bc
    pop hl
    inc hl
    djnz MarkCards
    ret

; ===== card-counting queries (Esperto) =====
; IsSeen: A=card id -> A=0 if UNSEEN, nonzero if seen. Preserves BC,DE,HL.
IsSeen:
    push bc
    push hl
    ld c,a
    srl a
    srl a
    srl a                        ; byte index = id>>3
    ld hl,Seen
    call addHLA                  ; preserves BC,DE
    ld a,c
    and 7
    ld b,a
    ld a,1
    inc b
.sh:
    dec b
    jr z,.t
    add a,a
    jr .sh
.t:
    and (hl)                     ; isolate the bit -> 0 (unseen) / bit-value (seen)
    pop hl
    pop bc
    ret

; UnseenOfValue: A=value(1..10) -> A = count(0..4) of cards of that value NOT yet seen.
; The four card ids of value v are (v-1)+10*suit. Preserves BC,DE,HL.
UnseenOfValue:
    push bc
    push de
    push hl
    dec a
    ld e,a                       ; E = id of (suit 0, value v)
    ld d,4                       ; 4 suits
    ld c,0                       ; C = unseen count
.uv:
    ld a,e
    call IsSeen                  ; preserves BC,DE,HL
    or a
    jr nz,.seen
    inc c
.seen:
    ld a,e
    add a,10
    ld e,a                       ; next suit's id
    dec d
    jr nz,.uv
    ld a,c
    pop hl
    pop de
    pop bc
    ret

; ThreatLive: A=value -> A=0 (skip this threat) / nonzero (apply the penalty).
; For Esperto (Difficulty 3) a threat is dead if the opponent provably can't hold the
; matching value (all 4 already seen). Other levels: always live (original behaviour).
; Clobbers A,B; preserves C,DE,HL (via UnseenOfValue).
ThreatLive:
    ld b,a
    ld a,(Difficulty)
    cp 3
    ld a,b
    ret nz                       ; not Esperto -> value (nonzero) -> apply
    jp UnseenOfValue             ; Esperto -> unseen count (0 -> skip)

; BuildRemaining: TmpTable = table cards NOT in CapSel
BuildRemaining:
    ld a,(TableN)
    ld b,a
    ld c,0
    ld e,0
.r:
    ld a,e
    cp b
    jr nc,.d
    ld hl,CapSel
    ld a,e
    call addHLA
    ld a,(hl)
    or a
    jr nz,.n
    ld hl,Table
    ld a,e
    call addHLA
    ld a,(hl)
    push af
    ld hl,TmpTable
    ld a,c
    call addHLA
    pop af
    ld (hl),a
    inc c
.n:
    inc e
    jr .r
.d:
    ld a,c
    ld (TmpTableN),a
    ret

; EvalSafety: penalise leaving an easily-swept / easily-captured TmpTable
EvalSafety:
    ld a,(TmpTableN)
    or a
    ret z
    ld b,a
    ld e,0
    ld c,0
.ss:
    ld hl,TmpTable
    ld a,e
    call addHLA
    ld a,(hl)
    call valueOf
    add a,c
    ld c,a
    inc e
    ld a,e
    cp b
    jr c,.ss
    ld a,c
    cp 11
    jr nc,.nsr
    call ThreatLive              ; Esperto: only a sweep risk if the opp can hold value==sum
    or a
    jr z,.nsr
    ld de,-9                     ; LEAVE_SWEEP_RISK (sum <= 10) (self-play tuned, was -20)
    call AddScoreDE
.nsr:
    ld d,1
.vv:
    ld a,(TmpTableN)
    ld b,a
    ld e,0
.vs:
    ld hl,TmpTable
    ld a,e
    call addHLA
    ld a,(hl)
    call valueOf
    cp d
    jr z,.vm
    inc e
    ld a,e
    cp b
    jr c,.vs
    jr .vn
.vm:
    ld a,d                       ; Esperto: skip if the opp can't hold a card of value d
    call ThreatLive
    or a
    jr z,.vn
    push de
    ld de,-5                     ; LEAVE_EASY_CAPTURE (per matchable value) (self-play tuned, was -2)
    call AddScoreDE
    pop de
.vn:
    inc d
    ld a,d
    cp 11
    jr c,.vv
    ; --- asso piglia tutto: a table with NO ace can be swept by the opponent's ace ---
    ld a,(AceRule)
    or a
    ret z                        ; rule off -> no ace-sweep risk
    ld a,(Difficulty)            ; Esperto: if no ace is still unseen, the opp can't ace-sweep
    cp 3
    jr nz,.aceon
    ld a,1
    call UnseenOfValue
    or a
    ret z
.aceon:
    ld a,(TmpTableN)
    ld b,a
    ld e,0
    ld c,0                       ; C.0 = settebello is on the leftover table
.asx:
    ld hl,TmpTable
    ld a,e
    call addHLA
    ld a,(hl)
    cp 6                         ; settebello id
    jr nz,.asx2
    set 0,c
.asx2:
    call valueOf
    cp 1
    ret z                        ; an ace is on the table -> sweep-proof, no risk
    inc e
    ld a,e
    cp b
    jr c,.asx
    ld a,(TmpTableN)             ; no ace -> opponent could sweep the lot with an ace
    neg
    ld e,a
    ld d,0xFF                    ; -1 per leftover card
    call AddScoreDE
    bit 0,c
    ret z
    ld de,-25                    ; ...and the settebello would be lost to that sweep
    call AddScoreDE
    ret

; EvalDrop: ScoreW for dropping AICardId (no capture available)
EvalDrop:
    ld a,(AICardId)
    ld c,a
    cp 6
    jr nz,.ns7
    ld de,-40                    ; SETTEBELLO_DROP
    call AddScoreDE
    jr .den
.ns7:
    ld a,c
    call valueOf
    cp 7
    jr nz,.n7
    ld de,-5                     ; DROP_7 (self-play tuned, was -12)
    call AddScoreDE
    jr .den
.n7:
    cp 6
    jr nz,.den
    ld de,-5                     ; DROP_6 (self-play tuned, was -6)
    call AddScoreDE
.den:
    ld a,c
    cp 10
    jr nc,.fc
    ld de,-4                     ; DROP_DENARI
    call AddScoreDE
.fc:
    ld a,c
    call valueOf
    cp 8
    jr c,.sf
    ld de,3                      ; prefer dropping face cards
    call AddScoreDE
.sf:
    ld a,(Difficulty)
    or a
    ret z                        ; EASY: no sweep-avoidance
    ld a,(TableN)
    ld b,a
    ld e,0
.cp:
    ld a,e
    cp b
    jr nc,.cpd
    ld hl,Table
    ld a,e
    call addHLA
    ld a,(hl)
    push af
    ld hl,TmpTable
    ld a,e
    call addHLA
    pop af
    ld (hl),a
    inc e
    jr .cp
.cpd:
    ld a,(TableN)
    ld hl,TmpTable
    call addHLA
    ld a,(AICardId)
    ld (hl),a
    ld a,(TableN)
    inc a
    ld (TmpTableN),a
    call EvalSafety
    ret

; =================== deal / deck ===================
InitDeck:
    ld hl,Deck
    ld b,40
    xor a
.id:
    ld (hl),a
    inc hl
    inc a
    djnz .id
    ret

Rnd:
    push hl
    ld hl,(Seed)
    ld a,h
    and 0x1F
    ld h,a
    ld a,(hl)
    inc hl
    ld (Seed),hl
    pop hl
    ret

Shuffle:
    di                           ; IY is hijacked below; keep the ROM interrupt out
    ld b,39
.sh:
    call Rnd
    ld c,b
    inc c
.mod:
    cp c
    jr c,.gotj
    sub c
    jr .mod
.gotj:
    ld hl,Deck
    ld d,0
    ld e,b
    add hl,de
    ld iy,Deck
    ld e,a
    add iy,de
    ld a,(hl)
    ld c,(iy+0)
    ld (hl),c
    ld (iy+0),a
    djnz .sh
    ld iy,0x5C3A                 ; restore the ROM interrupt-handler base
    ei
    ret

DealRound:
    xor a
    ld (DeckPos),a
    ld hl,Player
    ld b,3
    call DealTo
    ld hl,Opp
    ld b,3
    call DealTo
    ld hl,Table
    ld b,4
    call DealTo
    ld a,4
    ld (TableN),a
    xor a
    ld (Cursor),a
    ret

DealHands:
    ld hl,Player
    ld b,3
    call DealTo
    ld hl,Opp
    ld b,3
    call DealTo
    ld hl,Opp                    ; AI sees its freshly dealt hand
    ld b,3
    call MarkCards
    xor a
    ld (Cursor),a
    ret

DealTo:
    push hl
    ld a,(DeckPos)
    ld hl,Deck
    call addHLA
    pop de
.dl:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    ld a,(DeckPos)
    inc a
    ld (DeckPos),a
    djnz .dl
    ret

SweepToLast:
    ld a,(LastCap)
    ld (Who),a
    ld a,(TableN)
    or a
    ret z
    ld d,a
    ld e,0
.sl:
    ld hl,Table
    ld a,e
    call addHLA
    ld a,(hl)
    push de
    call AddToPile
    pop de
    inc e
    ld a,e
    cp d
    jr c,.sl
    xor a
    ld (TableN),a
    ret

; =================== rules engine ===================
addHLA:
    add a,l
    ld l,a
    ld a,0
    adc a,h
    ld h,a
    ret

valueOf:
    cp 10
    jr c,.lt
.sub:
    sub 10
    cp 10
    jr nc,.sub
.lt:
    inc a
    ret

; SplitId: A=id -> D=suit(0..3), E=value(1..10)
SplitId:
    ld d,0
.s:
    cp 10
    jr c,.dn
    sub 10
    inc d
    jr .s
.dn:
    inc a
    ld e,a
    ret

ResolvePlay:
    ld (Played),a
    ld a,c
    ld (Who),a
    ld a,(Played)
    call MarkSeen                ; the played card is now visible to the AI
    ld a,(Played)
    call valueOf
    call findAllCaptures
    ld a,(OptionN)
    or a
    jp z,.drop
    ld a,(Who)
    or a
    jr nz,.aipick
    ld a,(ChoiceMade)            ; player: use the choice made before the slide (card was in hand)
    or a
    jr z,.popt
    ld a,(ChoiceVal)
    jr .applyopt
.popt:
    ld a,(OptionN)
    cp 2
    jr c,.opt0                   ; single option -> auto
    call PlayerChooseCapture     ; fallback (normal flow pre-chooses in PlayerTurn)
    jr .applyopt
.opt0:
    xor a
    jr .applyopt
.aipick:
    ld a,(AIOpt)                 ; strong AI's pre-chosen capture option
.applyopt:
    call MaskToCapSel
    ld a,(RevealInPlace)         ; crowded-table capture already shown in place -> skip the table draw
    or a
    jr nz,.shown
    call ShowCapture             ; show the played card + flash what it takes
.shown:
    ld a,(TableN)
    ld d,a
    ld e,0
.capl:
    ld a,e
    cp d
    jr nc,.capdone
    ld hl,CapSel
    ld a,e
    call addHLA
    ld a,(hl)
    or a
    jr z,.capn
    ld hl,Table
    ld a,e
    call addHLA
    ld a,(hl)
    push de
    call AddToPile
    pop de
.capn:
    inc e
    jr .capl
.capdone:
    ld a,(Played)
    call AddToPile
    call CaptureZipOld           ; record surviving cards' OLD columns (pre-compaction)
    call CompactTable
    call ZipCompact              ; zip the survivors to their new compacted columns
    ld a,(Who)
    ld (LastCap),a
    ld a,(TableN)
    or a
    jr nz,.done
    ld a,(AceSweepOpt)
    or a
    jr nz,.done                  ; Scopa d'Assi: sweeping the table WITH AN ACE is not a scopa
    call IsLastPlay              ; no scopa on the final play of the round
    or a
    jr nz,.done
    ld a,(Who)
    or a
    jr nz,.osc
    ld hl,PScopa
    inc (hl)
    call ShowScopa
    jr .done
.osc:
    ld hl,OScopa
    inc (hl)
    call ShowScopa
    jr .done
.drop:
    ld a,(TableN)
    or a
    jr z,.dropset                ; empty table -> no existing cards to record
    ld b,a
    call TableStep
    ld c,a
    call FillZipCols             ; ZipCur[0..oldN-1] = existing cards' current columns
.dropset:
    ld a,(TableN)
    call TableSlotCol            ; column the slide left the new card at
    ld c,a
    ld hl,ZipCur
    ld a,(TableN)
    call addHLA
    ld (hl),c                    ; ZipCur[oldN] = the new card's current column
    ld hl,Table
    ld a,(TableN)
    call addHLA
    ld a,(Played)
    ld (hl),a
    ld hl,TableN
    inc (hl)
    call ZipCompact              ; existing cards make room + the new one settles (no snap)
                                 ; (no crowded-table flash: the slide already shows where the
                                 ;  card lands; the hardware-FLASH blink read as a glitch)
.done:
    ret

; IsLastPlay: A=1 if the card now being played is the last of the round.
; total remaining = cards in both hands (incl. the one in play) + deck left.
; IsLastPlay: A=1 only if NO cards remain anywhere after the card just played -- i.e. this
; was the very last card of the deal. (pagat.com: "Capturing the last card(s) ... at the
; very end of the last deal ... never counts as a scopa.") The played card is already
; removed from the hand, so a clear on the SECOND-to-last card (opponent still holds one)
; is a valid scopa and must NOT be suppressed -- the old `cp 2` wrongly suppressed it.
IsLastPlay:
    call CountPlayer
    ld b,a
    call CountOpp
    add a,b                      ; A = cards left in both hands (after this card)
    ld b,a
    ld a,40
    ld hl,DeckPos
    sub (hl)                     ; A = deck cards left (40 - DeckPos)
    add a,b                      ; A = total cards left after this card
    or a
    jr z,.last
    xor a
    ret                          ; cards remain -> NOT the last play (scopa counts)
.last:
    ld a,1
    ret                          ; nothing left -> the final card -> no scopa

AddToPile:
    ld c,a
    ld a,(Who)
    or a
    jr nz,.opp
    ld a,(PPileN)
    ld hl,PPile
    call addHLA
    ld (hl),c
    ld hl,PPileN
    inc (hl)
    ret
.opp:
    ld a,(OPileN)
    ld hl,OPile
    call addHLA
    ld (hl),c
    ld hl,OPileN
    inc (hl)
    ret

CompactTable:
    ld a,(TableN)
    ld d,a
    ld e,0
    ld c,0
.cl:
    ld a,e
    cp d
    jr nc,.cdone
    ld hl,CapSel
    ld a,e
    call addHLA
    ld a,(hl)
    or a
    jr nz,.skip
    ld hl,Table
    ld a,e
    call addHLA
    ld a,(hl)
    push af
    ld hl,Table
    ld a,c
    call addHLA
    pop af
    ld (hl),a
    inc c
.skip:
    inc e
    jr .cl
.cdone:
    ld a,c
    ld (TableN),a
    ret

; CaptureZipOld: before compaction, record each SURVIVING table card's current column
; into ZipCur[] (in left-to-right order). ZipCur[k] then = where survivor k is right now;
; CompactTable packs Table[] so survivor k lands at column 1 + newstep*k, and ZipCompact
; slides ZipCur[k] from the former to the latter.
CaptureZipOld:
    ld a,(TableN)
    call TableStep
    ld c,a                       ; C = old column step
    ld a,(TableN)
    ld b,a                       ; B = old card count (loop)
    or a
    ret z
    ld d,1                       ; D = column of old index e (= 1 + step*e)
    ld e,0                       ; E = old index
    xor a
    ld (ZipStep),a               ; reuse as the survivor counter k for now
.l:
    ld hl,CapSel
    ld a,e
    call addHLA                  ; preserves BC, DE
    ld a,(hl)
    or a
    jr nz,.cap                   ; captured -> not a survivor
    ld hl,ZipCur
    ld a,(ZipStep)
    call addHLA                  ; preserves DE
    ld (hl),d                    ; ZipCur[k] = current column
    ld hl,ZipStep
    inc (hl)
.cap:
    ld a,d
    add a,c
    ld d,a                       ; column += step
    inc e
    djnz .l
    ret

; ZipCompact: slide the (already-compacted) Table cards from their recorded ZipCur columns
; to their final compacted columns (1 + newstep*k), a few columns per frame -> a fast zip.
ZipCompact:
    IF FASTSIM
    ld a,(FastSim)
    or a
    ret nz                       ; bias sim: skip the re-pack animation (state already compacted)
    ENDIF
    ld a,(TableN)
    or a
    ret z                        ; table emptied (e.g. a scopa) -> nothing to zip
    call TableStep
    ld (ZipStep),a               ; new column step
    ; --- removal beat: the taken cards are already out of Table[]; show the survivors still at
    ; their OLD columns (taken cards now gone) and hold briefly, so the removal reads as its own
    ; step BEFORE the cards slide together (not simultaneously). ---
    ld a,1
    ld (HideTable),a
    call RenderShadow
    xor a
    ld (HideTable),a
    call DrawZipCards
    xor a
    ld (DBstart),a               ; TEAR-FREE removal: delta-blit only the taken cards' cells
    ld a,24
    ld (DBend),a
    call DeltaBlit               ; (was a full Blit -> the "horizontal blinds" when cards vanished)
    xor a
    ld (ScrOfs),a
    halt                         ; just a frame or two so the removal registers, not a long pause
    halt
    ; --- decide smooth slice vs snap by how WIDE the moving block is ---
    call ZipMoveSpan             ; A = moving-block width, sets ZipSliceC0 / ZipSliceW
    cp 15
    jr c,.zsmooth                ; narrow block -> the slice stays ahead of the beam (with ULA
                                 ; contention margin) -> smooth glide. 21 was too loose: contention
                                 ; made the lower band rows fall behind the beam -> tore.
    ; wide block: can't slide tear-free in one frame. Snap the cards to their compacted positions
    ; in state, then REVEAL the table band left-to-right in narrow chunks (each a tear-free
    ; BlitSlice) -> the survivors re-settle a strip at a time, no full-blit tear.
    call ZipSnap                 ; ZipCur[k] = target column for every survivor
    ld a,1
    ld (HideTable),a
    call RenderShadow            ; compacted board -> shadow (HUD/hand rows are outside the band)
    xor a
    ld (HideTable),a
    call DrawZipCards            ; survivors at their final columns, into the shadow
    xor a
    ld (ZipSliceC0),a            ; reveal the band (cols 0..31) in 4-col chunks, left to right
.snwipe:
    ld a,(ZipSliceC0)
    ld c,a
    ld a,32
    sub c                        ; columns remaining
    cp 5
    jr c,.snwl                   ; <=4 left -> copy the remainder
    ld a,4
.snwl:
    ld (ZipSliceW),a
    call BlitSlice               ; HALT + copy this band chunk from the shadow -> tear-free
    ld a,(ZipSliceC0)
    add a,4
    ld (ZipSliceC0),a
    cp 32
    jr c,.snwipe
    jr .zipdone
.zsmooth:
    xor a
    ld (ZipFrames),a
.frame:
    ld a,1
    ld (HideTable),a
    call RenderShadow            ; board WITHOUT the table -> shadow (ScrOfs=0x20)
    xor a
    ld (HideTable),a
    call DrawZipCards            ; draw the survivors at ZipCur[] onto the shadow
    call BlitSlice               ; copy ONLY the moving slice (cols c0..31, table band) -> tear-free
    ; advance every survivor one notch toward its target; note if any still moving
    xor a
    ld (Tmp0),a                  ; "moved" flag
    ld a,(TableN)
    ld b,a                       ; B = count
    ld a,(ZipStep)
    ld c,a                       ; C = new step
    ld d,1                       ; D = target column (1 + step*k)
    ld e,0                       ; E = k
.mv:
    ld hl,ZipCur
    ld a,e
    call addHLA                  ; HL = &ZipCur[k], preserves BC,DE
    ld a,(hl)
    cp d
    jr z,.atk                    ; already at target
    jr c,.right                  ; cur < target -> the table spread out, move right
    ; cur > target -> move left. Work out the distance FIRST (sub 4 on a near value
    ; underflows past 0 and the card never settles -> hang + a card sweeping the screen).
    sub d                        ; A = distance (cur - target)
    cp 5
    jr c,.snap                   ; within one step -> land exactly on target
    ld a,(hl)
    sub 4                        ; distance >= 5 -> move 4 left (no underflow)
    jr .set
.right:
    ld a,d
    sub (hl)                     ; A = distance (target - cur)
    cp 5
    jr c,.snap
    ld a,(hl)
    add a,4                      ; move 4 right
    jr .set
.snap:
    ld a,d                       ; snap onto the target column
.set:
    ld (hl),a
    ld a,1
    ld (Tmp0),a                  ; something moved this frame
.atk:
    ld a,d
    add a,c
    ld d,a                       ; target += step
    inc e
    djnz .mv
    ld a,(Tmp0)
    or a
    jr z,.zipdone                ; nothing moved -> all settled
    ld hl,ZipFrames
    inc (hl)
    ld a,(hl)
    cp 48
    jr c,.frame                  ; safety cap -> can never hard-hang
.zipdone:
    xor a
    ld (ScrOfs),a
    ret

ZipSliceC0 equ 0x7E08            ; re-pack: leftmost column in motion (slice left edge)
ZipSliceW  equ 0x7E09            ; re-pack: slice width = 32 - ZipSliceC0
FastSim    equ 0x7E0A            ; (TESTMODE 37 only) 1 = skip display/delays for the bias match-sim

; ZipMoveSpan: -> A = width of the moving block (= 32 - leftmost moving column), and stores
; that leftmost column in ZipSliceC0. A card is "moving" if its current column (ZipCur[k])
; differs from its target (1 + ZipStep*k); the leftmost position any moving card occupies is
; min over those of min(current, target). Wide block -> snap; narrow -> tear-free slice.
ZipMoveSpan:
    ld a,(TableN)
    ld b,a
    ld a,(ZipStep)
    ld c,a
    ld d,1                       ; D = target column (1 + step*k)
    ld e,0                       ; E = k
    ld a,32
    ld (ZipSliceC0),a            ; running min column (start high)
    xor a
    ld (ZipSliceW),a             ; running MAX column (start low; becomes width at the end)
.zms:
    ld hl,ZipCur
    ld a,e
    call addHLA
    ld a,(hl)                    ; A = ZipCur[k] (current column)
    cp d
    jr z,.zmsn                   ; current == target -> not moving, ignore
    call ZMSupd                  ; extend [min,max] with the current column (A)
    ld a,d
    call ZMSupd                  ; ...and with the target column
.zmsn:
    ld a,d
    add a,c
    ld d,a                       ; target += step
    inc e
    djnz .zms
    ld a,(ZipSliceW)             ; max column reached by any moving card
    add a,6                      ; + card width = right edge of the moving block
    ld hl,ZipSliceC0
    sub (hl)                     ; A = width = (max+6) - min
    ld (ZipSliceW),a             ; store the slice width
    ret
; ZMSupd: A = a column -> grow the [ZipSliceC0(min), ZipSliceW(max)] span to include it.
ZMSupd:
    ld hl,ZipSliceC0
    cp (hl)
    jr nc,.notmin
    ld (hl),a
.notmin:
    ld hl,ZipSliceW
    cp (hl)
    ret c
    ld (hl),a
    ret

; ZipSnap: set every survivor's ZipCur[k] straight to its target column (1 + ZipStep*k).
ZipSnap:
    ld a,(TableN)
    ld b,a
    ld a,(ZipStep)
    ld c,a
    ld d,1
    ld e,0
.zsn:
    ld hl,ZipCur
    ld a,e
    call addHLA
    ld a,d
    ld (hl),a
    ld a,d
    add a,c
    ld d,a
    inc e
    djnz .zsn
    ret

; BlitSlice: HALT, then copy columns [ZipSliceC0 .. 31] of the table band (char-rows 8..15)
; from the shadow buffer to the screen, raster-order, per char-row LDIR. Small enough (the
; slice is <=16 cols) to finish ahead of the descending beam -> tear-free re-pack frame.
BlitSlice:
    halt                         ; ZipSliceC0/ZipSliceW already set by ZipMoveSpan
    di
    ld a,8
    ld (Tmp0),a                  ; char-row 8..15
.bsrow:
    ld a,(Tmp0)                  ; HL = screen addr of (row, c0), pixel line 0
    and 0x18
    or 0x40
    ld h,a
    ld a,(Tmp0)
    and 7
    rrca
    rrca
    rrca
    ld e,a
    ld a,(ZipSliceC0)
    add a,e
    ld l,a
    ld a,8
    ld (Tmp1),a                  ; 8 pixel lines
.bsline:
    push hl                      ; screen line start
    ld d,h
    ld e,l                       ; DE = screen dst
    ld a,h
    add a,0x20
    ld h,a                       ; HL = shadow src
    ld a,(ZipSliceW)
    ld c,a
    ld b,0
    ldir                         ; copy W bytes (shadow -> screen)
    pop hl
    inc h                        ; next pixel line
    ld a,(Tmp1)
    dec a
    ld (Tmp1),a
    jr nz,.bsline
    ; colour row (shadow -> screen): 0x5800 + row*32 + c0, W cells
    ld a,(Tmp0)
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl                    ; row*32
    ld a,(ZipSliceC0)
    add a,l
    ld l,a
    ld a,h
    adc a,0x58
    ld h,a                       ; HL = screen attr (row, c0)
    ld d,h
    ld e,l
    ld a,h
    add a,0x20
    ld h,a                       ; HL = shadow attr
    ld a,(ZipSliceW)
    ld c,a
    ld b,0
    ldir
    ld hl,Tmp0
    inc (hl)
    ld a,(hl)
    cp 16
    jr c,.bsrow
    ei
    ret

; DrawZipCards: draw each surviving table card (Table[k]) at column ZipCur[k], row 8,
; onto the current target (shadow during ZipCompact). Skips off-screen columns (>=27).
DrawZipCards:
    ld a,(TableN)
    ld b,a                       ; B = count
    ld e,0                       ; E = k
.dz:
    ld hl,ZipCur
    ld a,e
    call addHLA                  ; preserves BC,DE
    ld a,(hl)
    cp 27
    jr nc,.dzn                   ; off the right edge -> don't draw
    ld d,a                       ; D = column
    push bc
    push de
    ld hl,Table
    ld a,e
    call addHLA
    ld a,(hl)                    ; A = card id
    ld e,8                       ; row 8 (the table row)
    call BlitCard
    pop de
    pop bc
.dzn:
    inc e
    djnz .dz
    ret

; FillZipCols: B=count, C=step -> ZipCur[0..count-1] = 1 + step*k (current table columns)
FillZipCols:
    ld d,1                       ; column
    ld e,0                       ; k
.f:
    ld hl,ZipCur
    ld a,e
    call addHLA                  ; preserves BC, DE
    ld (hl),d
    ld a,d
    add a,c
    ld d,a
    inc e
    djnz .f
    ret

; findAllCaptures: A=value -> Options[] (table-index masks), OptionN.
; Singles take priority: if any single matches, ONLY singles are listed.
findAllCaptures:
    ld (FCval),a
    xor a
    ld (OptionN),a
    ld (AceSweepOpt),a            ; default: not an ace-sweep
    ld a,(TableN)
    or a
    ret z
    ; --- "asso piglia tutto": an ace sweeps the whole table (unless an ace is on it) ---
    ld a,(AceRule)
    or a
    jr z,.sgstart                ; rule off
    ld a,(FCval)
    cp 1
    jr nz,.sgstart               ; not an ace
    ld e,0                       ; scan: is there already an ace on the table?
.acesc:
    ld hl,Table
    ld a,e
    call addHLA
    ld a,(hl)
    call valueOf
    cp 1
    jr z,.sgstart                ; ace present -> ordinary single-capture (ace takes the ace)
    inc e
    ld a,(TableN)
    cp e
    jr nz,.acesc
    ld a,(TableN)                ; no ace present -> one option: capture ALL cards
    ld b,a
    ld hl,1
.acemk:
    dec b
    jr z,.acemkd
    add hl,hl
    jr .acemk
.acemkd:
    add hl,hl
    dec hl                       ; HL = (1<<TableN)-1 = every table bit
    ld d,h
    ld e,l
    call AddOption               ; Options[0] = full-table mask, OptionN = 1
    ld a,1
    ld (AceSweepOpt),a           ; flag it so ResolvePlay awards NO scopa (Scopa d'Assi)
    ret
.sgstart:
    ld e,0
.sg:
    ld hl,Table
    ld a,e
    call addHLA
    ld a,(hl)
    call valueOf
    ld hl,FCval
    cp (hl)
    jr nz,.sgn
    push de
    ld a,e
    call BitMask
    call AddOption
    pop de
.sgn:
    inc e
    ld a,(TableN)
    cp e
    jr nz,.sg
    ld a,(OptionN)
    or a
    ret nz                       ; singles present -> priority rule, done
    ld a,(TableN)
    ld b,a
    ld hl,1
.mk:
    dec b
    jr z,.mkd
    add hl,hl
    jr .mk
.mkd:
    add hl,hl
    ld (FCmaxmask),hl
    ld hl,3
    ld (FCmask),hl
.ml:
    ld hl,(FCmask)
    ld d,h
    ld e,l
    dec de
    ld a,l
    and e
    ld c,a
    ld a,h
    and d
    or c
    jr z,.mln                    ; mask is a single bit -> skip (handled as single)
    call MaskSum
    ld a,(FCsum)
    ld hl,FCval
    cp (hl)
    jr nz,.mln
    ld de,(FCmask)
    call AddOption
.mln:
    ld hl,(FCmask)
    inc hl
    ld (FCmask),hl
    ld de,(FCmaxmask)
    or a
    sbc hl,de
    jr c,.ml
    ret

; CanCapture: A=value -> A=1 if any capture exists, else 0
CanCapture:
    call findAllCaptures
    ld a,(OptionN)
    or a
    ret z
    ld a,1
    ret

; BitMask: A=bit index -> DE = 1<<A
BitMask:
    ld de,1
    or a
    ret z
    ld b,a
.b:
    sla e
    rl d
    djnz .b
    ret

; AddOption: append mask DE to Options[OptionN], cap 16
AddOption:
    ld a,(OptionN)
    cp 16
    ret nc
    ld hl,Options
    add a,a
    call addHLA
    ld (hl),e
    inc hl
    ld (hl),d
    ld hl,OptionN
    inc (hl)
    ret

; MaskToCapSel: A=option index -> expand Options[A] into CapSel[]
MaskToCapSel:
    ld hl,Options
    add a,a
    call addHLA
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (FCmask),de
    ld hl,CapSel
    ld b,16
    xor a
.c:
    ld (hl),a
    inc hl
    djnz .c
    call MarkMask
    ret

MaskSum:
    ld hl,(FCmask)
    ld a,(TableN)
    ld b,a
    ld e,0
    ld c,0
    ld d,0
.ms:
    ld a,l
    and 1
    jr z,.msn
    push hl
    push bc
    ld hl,Table
    ld a,e
    call addHLA
    ld a,(hl)
    call valueOf
    pop bc
    add a,c
    ld c,a
    inc d
    pop hl
.msn:
    srl h
    rr l
    inc e
    djnz .ms
    ld a,c
    ld (FCsum),a
    ret

MarkMask:
    ld hl,(FCmask)
    ld a,(TableN)
    ld b,a
    ld e,0
.mm:
    ld a,l
    and 1
    jr z,.mmn
    push hl
    ld hl,CapSel
    ld a,e
    call addHLA
    ld (hl),1
    pop hl
.mmn:
    srl h
    rr l
    inc e
    djnz .mm
    ret

FCmask:    defw 0
FCmaxmask: defw 0
FCsum:     defb 0

; =================== scoring ===================
PRIME:     defb 16,12,13,14,15,18,21,10,10,10   ; value 1..10

; CountDenari: HL=pile, B=count -> A=count of suit-0 cards (id<10)
CountDenari:
    ld c,0
    ld a,b
    or a
    jr z,.done
.dl:
    ld a,(hl)
    cp 10
    jr nc,.dn
    inc c
.dn:
    inc hl
    djnz .dl
.done:
    ld a,c
    ret

; HasSette: HL=pile, B=count -> A=1 if id6 present
HasSette:
    ld a,b
    or a
    ret z
.hl:
    ld a,(hl)
    cp 6
    jr z,.yes
    inc hl
    djnz .hl
    xor a
    ret
.yes:
    ld a,1
    ret

; Primiera: HL=pile, B=count -> A=prime sum
Primiera:
    xor a
    ld (PBest+0),a
    ld (PBest+1),a
    ld (PBest+2),a
    ld (PBest+3),a
    ld a,b
    or a
    jr z,.sum
    ld c,b
.loop:
    ld a,(hl)
    push hl
    push bc
    call SplitId                 ; D=suit, E=value
    ld a,e
    dec a
    ld hl,PRIME
    call addHLA
    ld a,(hl)                    ; A=prime points
    ld hl,PBest
    push af
    ld a,d
    call addHLA                  ; HL=&PBest[suit]
    pop af
    cp (hl)
    jr c,.noupd
    ld (hl),a
.noupd:
    pop bc
    pop hl
    inc hl
    dec c
    jr nz,.loop
.sum:
    ; primiera requires at least one card in ALL four suits, else 0
    ld a,(PBest+0)
    or a
    ret z
    ld a,(PBest+1)
    or a
    ret z
    ld a,(PBest+2)
    or a
    ret z
    ld a,(PBest+3)
    or a
    ret z
    ld a,(PBest+0)
    ld hl,PBest+1
    add a,(hl)
    ld hl,PBest+2
    add a,(hl)
    ld hl,PBest+3
    add a,(hl)
    ret

; AwardCat: B=pval, C=oval, A=catidx -> updates PRound/ORound + CatWin[A]
AwardCat:
    ld hl,CatWin
    call addHLA
    ld a,b
    cp c
    jr z,.tie
    jr c,.opp
    ld (hl),0
    ld hl,PRound
    inc (hl)
    ret
.opp:
    ld (hl),1
    ld hl,ORound
    inc (hl)
    ret
.tie:
    ld (hl),2
    ret

ScoreRound:
    xor a
    ld (PRound),a
    ld (ORound),a
    ; carte
    ld a,(PPileN)
    ld b,a
    ld a,(OPileN)
    ld c,a
    xor a
    call AwardCat
    ; denari
    ld hl,PPile
    ld a,(PPileN)
    ld b,a
    call CountDenari
    ld (Tmp0),a
    ld hl,OPile
    ld a,(OPileN)
    ld b,a
    call CountDenari
    ld (Tmp1),a
    ld a,(Tmp0)
    ld b,a
    ld a,(Tmp1)
    ld c,a
    ld a,1
    call AwardCat
    ; settebello
    ld hl,PPile
    ld a,(PPileN)
    ld b,a
    call HasSette
    ld (Tmp0),a
    ld hl,OPile
    ld a,(OPileN)
    ld b,a
    call HasSette
    ld (Tmp1),a
    ld a,(Tmp0)
    ld b,a
    ld a,(Tmp1)
    ld c,a
    ld a,2
    call AwardCat
    ; primiera
    ld hl,PPile
    ld a,(PPileN)
    ld b,a
    call Primiera
    ld (Tmp0),a
    ld hl,OPile
    ld a,(OPileN)
    ld b,a
    call Primiera
    ld (Tmp1),a
    ld a,(Tmp0)
    ld b,a
    ld a,(Tmp1)
    ld c,a
    ld a,3
    call AwardCat
    ; scope
    ld a,(PScopa)
    ld b,a
    ld a,(PRound)
    add a,b
    ld (PRound),a
    ld a,(OScopa)
    ld b,a
    ld a,(ORound)
    add a,b
    ld (ORound),a
    ld a,(PScopa)
    ld b,a
    ld a,(OScopa)
    ld c,a
    ld hl,CatWin+4
    ld a,b
    cp c
    jr z,.stie
    jr c,.sopp
    ld (hl),0
    jr .mtot
.sopp:
    ld (hl),1
    jr .mtot
.stie:
    ld (hl),2
.mtot:
    ; --- napola / Neapolitan (run of coins from the ace) ---
    xor a
    call Napola
    ld (Pnapola),a
    ld b,a
    ld a,(PRound)
    add a,b
    ld (PRound),a
    ld a,1
    call Napola
    ld (Onapola),a
    ld b,a
    ld a,(ORound)
    add a,b
    ld (ORound),a
    ; --- le palle del cane (all four sevens = +1) ---
    xor a
    call PalleDelCane
    ld (Ppalle),a
    ld b,a
    ld a,(PRound)
    add a,b
    ld (PRound),a
    ld a,1
    call PalleDelCane
    ld (Opalle),a
    ld b,a
    ld a,(ORound)
    add a,b
    ld (ORound),a
    ; --- match totals ---
    ld a,(PMatch)
    ld b,a
    ld a,(PRound)
    add a,b
    ld (PMatch),a
    ld a,(OMatch)
    ld b,a
    ld a,(ORound)
    add a,b
    ld (OMatch),a
    ret

; Napola: A = which (0 player / 1 opp) -> A = Neapolitan points.
; Needs coins A,2,3 (ids 0,1,2) = 3 pts; +1 for each further consecutive coin
; (4,5,6.. = ids 3,4,5..); all ten coins = 10 ("Napoleone"). 0 if A,2,3 not all held.
Napola:
    ld (NapWhich),a
    ld c,0
    call NapHas
    or a
    ret z
    ld c,1
    call NapHas
    or a
    ret z
    ld c,2
    call NapHas
    or a
    ret z
    ld d,3                       ; have ids 0,1,2 -> 3 points
    ld c,3                       ; next coin to check (id 3 = the four)
.ext:
    call NapHas
    or a
    jr z,.done
    ld a,c
    inc a
    ld d,a                       ; points = value of this coin (id+1)
    inc c
    ld a,c
    cp 10
    jr c,.ext
.done:
    ld a,d
    ret

; NapHas: C = card id, uses (NapWhich) -> A=1 if that id is in the pile
NapHas:
    push bc
    push de
    ld a,(NapWhich)
    or a
    jr nz,.opp
    ld hl,PPile
    ld a,(PPileN)
    jr .scan
.opp:
    ld hl,OPile
    ld a,(OPileN)
.scan:
    or a
    jr z,.no
    ld b,a
.l:
    ld a,(hl)
    cp c
    jr z,.yes
    inc hl
    djnz .l
.no:
    pop de
    pop bc
    xor a
    ret
.yes:
    pop de
    pop bc
    ld a,1
    ret

; PalleDelCane ("le palle del cane"): A=which -> A=1 if the pile holds ALL FOUR sevens
; (ids 6,16,26,36) -> +1 bonus point on top of primiera.
PalleDelCane:
    ld (NapWhich),a
    ld c,6
    call NapHas
    or a
    ret z
    ld c,16
    call NapHas
    or a
    ret z
    ld c,26
    call NapHas
    or a
    ret z
    ld c,36
    jp NapHas

; P holds the four 7s (all suits -> primiera 84, settebello, 1 denari, 4 cards).
; O holds three aces of suits 0/1/2 (MISSING suit 3 -> primiera must be 0).
ScoreTestSetup:
    ld hl,PPile
    ld (hl),6                    ; 7 denari (settebello, suit0)
    inc hl
    ld (hl),16                   ; 7 coppe  (suit1)
    inc hl
    ld (hl),26                   ; 7 spade  (suit2)
    inc hl
    ld (hl),36                   ; 7 bastoni(suit3)
    ld a,4
    ld (PPileN),a
    ld hl,OPile
    ld (hl),0                    ; ace denari (suit0)
    inc hl
    ld (hl),10                   ; ace coppe  (suit1)
    inc hl
    ld (hl),20                   ; ace spade  (suit2) -- no suit3
    ld a,3
    ld (OPileN),a
    ld a,1
    ld (PScopa),a
    xor a
    ld (OScopa),a
    ld (PMatch),a
    ld (OMatch),a
    ret

; Last-play test: table [3,4], player holds only the settebello (value 7),
; opp hand empty, deck exhausted -> sweeping is the LAST play -> NO scopa.
LastPlayTestSetup:
    xor a
    ld (PPileN),a
    ld (OPileN),a
    ld (PScopa),a
    ld (OScopa),a
    ld a,2
    ld (Table),a
    ld a,3
    ld (Table+1),a
    ld a,2
    ld (TableN),a
    ld a,0xFF                    ; played card (id 6) ALREADY removed from hand, as in real
    ld (Player),a                ; play -> hand empty, opp empty -> total-after = 0 -> last card
    ld (Player+1),a
    ld (Player+2),a
    ld (Opp),a
    ld (Opp+1),a
    ld (Opp+2),a
    ld a,40
    ld (DeckPos),a
    ret

; =================== counts ===================
CountOpp:
    ld hl,Opp
    jr CountHand
CountPlayer:
    ld hl,Player
CountHand:
    ld b,3
    ld c,0
.ch:
    ld a,(hl)
    inc hl
    cp 0xFF
    jr z,.chn
    inc c
.chn:
    djnz .ch
    ld a,c
    ret

; =================== input ===================
ReadKeys:
    xor a
    ld (Keys),a
    ld bc,0xDFFE
    in a,(c)
    bit 1,a
    jr nz,.nl
    ld hl,Keys
    set 0,(hl)
.nl:
    ld bc,0xDFFE
    in a,(c)
    bit 0,a
    jr nz,.nr
    ld hl,Keys
    set 1,(hl)
.nr:
    ld bc,0x7FFE
    in a,(c)
    bit 0,a
    jr nz,.ns
    ld hl,Keys
    set 2,(hl)
.ns:
    ld a,(Keys)
    ret

WaitSpace:
.dr:
    call ReadKeys
    or a
    jr nz,.dr
.w:
    call ReadKeys
    bit 2,a
    jr z,.w
.r:
    call ReadKeys
    or a
    jr nz,.r
    ret

Delay:
    IF FASTSIM
    ld a,(FastSim)
    or a
    ret nz                       ; bias sim: no waiting
    ENDIF
    call DemoCheckSpace          ; demo: a SPACE in any pause drops back to the menu (clobbers A only)
.d1:
    ld de,0
.d2:
    dec de
    ld a,d
    or e
    jr nz,.d2
    djnz .d1
    ret

; Beep: B=toggle count, DE=pitch delay (smaller=higher). Border kept cyan.
Beep:
    ld c,5
.b1:
    ld a,c
    xor 0x10
    ld c,a
    out (254),a
    ld h,d
    ld l,e
.b2:
    dec hl
    ld a,h
    or l
    jr nz,.b2
    djnz .b1
    ld a,5
    out (254),a
    ret

; SoundEnabled: Z = stay silent (user turned sound off, OR the demo is running), NZ = play.
SoundEnabled:
    ld a,(DemoMode)
    or a
    jr nz,.off
    ld a,(SoundOn)
    or a
    ret                          ; Z if SoundOn == 0
.off:
    xor a
    ret                          ; Z

; NeapolitanSound: a pleasing run up the scale (delays descend -> pitch rises)
NeapolitanSound:
    call SoundEnabled
    ret z
    ld hl,ScaleTbl
    ld c,9
.ns:
    push bc
    push hl
    ld e,(hl)
    ld d,0
    ld b,34
    call Beep
    pop hl
    pop bc
    inc hl
    dec c
    jr nz,.ns
    ret
ScaleTbl: defb 250,222,198,187,167,148,132,125,118

; ShowNeapolitan: brief celebratory screen with NEAPOLITAN in big letters + the scale
ShowNeapolitan:
    xor a
    ld (ScrOfs),a
    call ClsBlack
    ld hl,NeapolitanBanner       ; big TrueType "NEAPOLITAN" (same style as SCOPA!)
    ld a,9
    call BlitBanner
    call NeapolitanSound
    ld b,3
    call Delay
    ret

; ---- 2x-size text ----
DoubleNib: defb 0x00,0x03,0x0C,0x0F,0x30,0x33,0x3C,0x3F,0xC0,0xC3,0xCC,0xCF,0xF0,0xF3,0xFC,0xFF

; Double8: A=8 bits -> B=left doubled byte, C=right doubled byte
Double8:
    push af
    rrca
    rrca
    rrca
    rrca
    and 0x0F
    ld hl,DoubleNib
    call addHLA
    ld b,(hl)
    pop af
    and 0x0F
    ld hl,DoubleNib
    call addHLA
    ld c,(hl)
    ret

; ScreenDown: DE = screen addr -> next pixel row down
ScreenDown:
    inc d
    ld a,d
    and 7
    ret nz
    ld a,e
    add a,0x20
    ld e,a
    ret c
    ld a,d
    sub 8
    ld d,a
    ret

; PrintBigChar: A=char, D=col(cell), E=crow(cell) -> 16x16 glyph (direct to screen)
PrintBigChar:
    push de
    sub 32
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    ld bc,0x3D00
    add hl,bc                    ; HL = glyph (8 bytes)
    pop de                       ; D=col, E=crow
    ld a,e
    and 0x18
    or 0x40
    ld b,a
    ld a,e
    and 7
    rrca
    rrca
    rrca
    or d
    ld c,a
    ld d,b
    ld e,c                       ; DE = screen addr (top pixel row of the cell)
    ld a,8
.row:
    push af
    ld a,(hl)
    inc hl
    push hl
    call Double8                 ; B=left, C=right doubled bytes
    ld a,b
    ld (de),a
    inc e
    ld a,c
    ld (de),a
    dec e
    call ScreenDown
    ld a,b
    ld (de),a
    inc e
    ld a,c
    ld (de),a
    dec e
    call ScreenDown
    pop hl
    pop af
    dec a
    jr nz,.row
    ret

; PrintBigStr: HL=ptr, D=col, E=crow (advances 2 cells per char)
PrintBigStr:
.l:
    ld a,(hl)
    or a
    ret z
    push hl
    push de
    call PrintBigChar
    pop de
    pop hl
    inc hl
    inc d
    inc d
    jr .l

; =================== text ===================
ClsBlack:
    ld hl,0x4000
    ld de,0x4001
    ld bc,0x17FF
    ld (hl),0
    ldir
    ld hl,0x5800
    ld de,0x5801
    ld bc,0x2FF
    ld (hl),0x07
    ldir
    ret

; PrintChar: A=char, D=col, E=crow
PrintChar:
    push de
    sub 32
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    ld de,0x3D00
    add hl,de
    pop de
    ld a,e
    and 0x18
    or 0x40
    push hl
    ld hl,ScrOfs
    add a,(hl)                   ; screen or shadow
    pop hl
    ld b,a
    ld a,e
    and 7
    rrca
    rrca
    rrca
    or d
    ld e,a
    ld d,b
    ld b,8
.pl:
    ld a,(hl)
    ld (de),a
    inc hl
    inc d
    djnz .pl
    ret

; PrintStr: HL=ptr(0-term), D=col, E=crow
PrintStr:
.ps:
    ld a,(hl)
    or a
    ret z
    push hl
    push de
    call PrintChar
    pop de
    pop hl
    inc hl
    inc d
    jr .ps

; PrintNum: A=value(0..99), D=col, E=crow
PrintNum:
    ld b,0
.t:
    cp 10
    jr c,.u
    sub 10
    inc b
    jr .t
.u:
    push af
    ld a,b
    add a,'0'
    push de
    call PrintChar
    pop de
    inc d
    pop af
    add a,'0'
    call PrintChar
    ret

; =================== screens ===================
; PickTitle: random rotation between the two title screens. Entropy = the boot Seed
; (R + FRAMES, set just before ShowTitle) mixed with the live refresh register. HL = chosen.
PickTitle:
    ld a,(Seed)
    ld b,a
    ld a,(Seed+1)
    xor b
    ld b,a
    ld a,r
    xor b
    and 1
    ld hl,TitleRle
    ret z
    ld hl,Title2Rle
    ret

ShowTitle:
    call PickTitle               ; pick a title at random (2-screen rotation)
    ld (CurTitle),hl
    call DecompressScr           ; expand the chosen SCOMPACT-packed title onto the screen (0x4000)
    call PlayTitleMusic          ; A: 0=finished, 1=SPACE(skip->game), 2=H(help)
    cp 1
    ret z                        ; SPACE during music -> straight to the game
    cp 2
    jr z,.help                   ; H during music -> rules screen
.startwait:
    ld hl,0
    ld (23672),hl                ; (re)start the 25s attract-mode idle timer
.wait:
    call ReadKeys
    bit 2,a
    jr nz,.go                    ; SPACE -> start the game
    ld a,0xBF                    ; H half-row (ENTER L K J H); H = bit 4
    in a,(0xFE)
    bit 4,a
    jr z,.help                   ; H pressed -> rules screen
    ld hl,(23672)                ; idle 25s with no key -> attract / self-play demo
    ld de,1250                   ; 25s @ 50 Hz
    or a
    sbc hl,de
    jr c,.wait                   ; not yet -> keep waiting
    jp EnterDemo
.help:
    call ShowHowToPlay           ; H -> rules screen, then redraw the same title
    ld hl,(CurTitle)
    call DecompressScr
.drainh:
    ld a,0xBF
    in a,(0xFE)
    bit 4,a
    jr z,.drainh                 ; wait for H release
    jr .startwait                ; back to waiting, idle timer reset (player was active)
.go:
    call ReadKeys                ; drain SPACE
    or a
    jr nz,.go
    ret

; ShowHowToPlay: one-screen rules + controls summary; SPACE returns.
ShowHowToPlay:
    xor a
    ld (ScrOfs),a
    call ClsBlack
    ld hl,HtpLines
.pl:
    ld a,(hl)
    cp 0xFF
    jr z,.pld
    ld d,a                       ; col
    inc hl
    ld e,(hl)                    ; row
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)                    ; BC = string ptr
    inc hl
    push hl
    ld h,b
    ld l,c
    call PrintStr
    pop hl
    jr .pl
.pld:
    ld e,1
    ld a,0x46                    ; gold title row
    call FillAttrRow
    call WaitSpace
    ret

HtpLines:                        ; col, row, string-ptr
    defb 10,1
    defw StrHtpT
    defb 3,3
    defw StrHtp1
    defb 3,4
    defw StrHtp2
    defb 3,6
    defw StrHtp3
    defb 3,7
    defw StrHtp4
    defb 3,8
    defw StrHtp5
    defb 3,10
    defw StrHtp6
    defb 3,12
    defw StrHtp7
    defb 3,13
    defw StrHtp8
    defb 3,14
    defw StrHtp9
    defb 3,15
    defw StrHtp10
    defb 3,16
    defw StrHtp11
    defb 3,18
    defw StrHtp12
    defb 2,21
    defw StrHtp13
    defb 5,23
    defw StrHtpBack
    defb 0xFF
StrHtpT:    defb "HOW TO PLAY",0
StrHtp1:    defb "Capture table cards by",0
StrHtp2:    defb "matching their value.",0
StrHtp3:    defb "Play a card equal to one on",0
StrHtp4:    defb "the table - or to the total",0
StrHtp5:    defb "of several - to win them all.",0
StrHtp6:    defb "Empty the table = SCOPA! (+1)",0
StrHtp7:    defb "Round points go to:",0
StrHtp8:    defb " - most cards",0
StrHtp9:    defb " - most coins (denari)",0
StrHtp10:   defb " - the seven of coins",0
StrHtp11:   defb " - best primiera + each scopa",0
StrHtp12:   defb "First to 11 wins the match.",0
StrHtp13:   defb "O / P  move      SPACE  play",0
StrHtpBack: defb "PRESS SPACE TO GO BACK",0

; DecompressScr: HL = RLE source -> expands exactly 6912 bytes to 0x4000.
; Control byte: bit7 set -> run of (c & 0x7F) copies of the next byte; else literal of c bytes.
DecompressScr:
    ld de,0x4000
.l:
    ld a,(hl)
    inc hl
    bit 7,a
    jr nz,.run
    ld c,a                       ; literal: copy A bytes
    ld b,0
    ldir
    jr .chk
.run:
    and 0x7F
    ld c,a                       ; run length
    ld a,(hl)
    inc hl
.rl:
    ld (de),a
    inc de
    dec c
    jr nz,.rl
.chk:
    ld a,d
    cp 0x5B                      ; DE reached 0x5B00 = 0x4000 + 6912 -> done
    jr nz,.l
    ret

; SelectDifficulty: skill via 1/2/3; key 4 toggles "asso piglia tutto" (default OFF).
SelectDifficulty:
    xor a
    ld (ScrOfs),a
    ld (AceRule),a               ; rule starts OFF each time the menu is shown
    call ClsBlack
    ld hl,StrScopa
    ld d,11
    ld e,2
    call PrintStr
    ld hl,StrSkill
    ld d,7
    ld e,6
    call PrintStr
    ld hl,StrEasy
    ld d,11
    ld e,8
    call PrintStr
    ld hl,StrMed
    ld d,11
    ld e,10
    call PrintStr
    ld hl,StrHard
    ld d,11
    ld e,12
    call PrintStr
    ld hl,StrExpert
    ld d,11
    ld e,14
    call PrintStr
    ld hl,StrAssoSub             ; subtitle under the rule toggle
    ld d,5
    ld e,18
    call PrintStr
    ld e,2                        ; tricolore-flavoured colouring
    ld a,0x46
    call FillAttrRow              ; SCOPA gold
    ld e,6
    ld a,0x45
    call FillAttrRow              ; prompt cyan
    ld e,8
    ld a,0x44
    call FillAttrRow              ; EASY green
    ld e,10
    ld a,0x47
    call FillAttrRow              ; MEDIUM white
    ld e,12
    ld a,0x42
    call FillAttrRow              ; HARD red
    ld e,14
    ld a,0x43
    call FillAttrRow              ; ESPERTO magenta
    ld e,18
    ld a,0x05
    call FillAttrRow              ; subtitle dim cyan
    call .drawasso               ; rule toggle (row 16)
    call .drawsound              ; sound toggle (row 20)
.w:
    ld bc,0xF7FE                  ; keys 1,2,3,4,5
    in a,(c)
    bit 0,a
    jr z,.easy
    bit 1,a
    jr z,.med
    bit 2,a
    jr z,.hard
    bit 3,a                      ; key 4 -> Esperto (card-counting AI)
    jr z,.expert
    bit 4,a                      ; key 5 -> toggle the asso rule
    jr z,.toggle
    ld bc,0xEFFE                  ; keys 6,7,8,9,0
    in a,(c)
    bit 4,a                       ; key 6 -> toggle sound
    jr z,.snd
    jr .w
.toggle:
    ld a,(AceRule)
    xor 1
    ld (AceRule),a
    call .drawasso
.trel:                           ; debounce: wait for key 5 to be released
    ld bc,0xF7FE
    in a,(c)
    bit 4,a
    jr z,.trel
    jr .w
.snd:
    ld a,(SoundOn)
    xor 1
    ld (SoundOn),a
    call .drawsound
.srel:                           ; debounce: wait for key 6 to be released
    ld bc,0xEFFE
    in a,(c)
    bit 4,a
    jr z,.srel
    jr .w
.easy:
    xor a
    jr .set
.med:
    ld a,1
    jr .set
.hard:
    ld a,2
    jr .set
.expert:
    ld a,3
.set:
    ld (Difficulty),a
    ret
.drawasso:                       ; redraw the rule toggle line (row 16) from AceRule
    ld a,(AceRule)
    or a
    ld hl,StrAssoOff
    jr z,.dao
    ld hl,StrAssoOn
.dao:
    ld d,4
    ld e,16
    call PrintStr
    ld a,(AceRule)
    or a
    ld a,0x47                     ; OFF -> white
    jr z,.dac
    ld a,0x44                     ; ON  -> green
.dac:
    ld e,16
    call FillAttrRow
    ret
.drawsound:                      ; redraw the sound toggle line (row 21) from SoundOn
    ld a,(SoundOn)
    or a
    ld hl,StrSoundOff
    jr z,.dso
    ld hl,StrSoundOn
.dso:
    ld d,9
    ld e,20
    call PrintStr
    ld a,(SoundOn)
    or a
    ld a,0x42                     ; OFF -> red
    jr z,.dsc
    ld a,0x44                     ; ON  -> green
.dsc:
    ld e,20
    call FillAttrRow
    ret

StrSkill: defb "SELECT SKILL LEVEL",0
StrEasy:  defb "1   EASY",0
StrMed:   defb "2   MEDIUM",0
StrHard:  defb "3   HARD",0
StrExpert: defb "4   ESPERTO",0
StrAssoOff: defb "5  ASSO PIGLIA TUTTO  OFF",0
StrAssoOn:  defb "5  ASSO PIGLIA TUTTO  ON ",0
StrAssoSub: defb "(ACE TAKES WHOLE TABLE)",0
StrSoundOff: defb "6  SOUND  OFF",0
StrSoundOn:  defb "6  SOUND  ON ",0

; FillAttrRow: E=char row, A=attr -> fill that whole attr row
FillAttrRow:
    ld c,a
    ld h,0
    ld l,e
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    ld de,0x5800
    add hl,de
    ld b,32
.fr:
    ld (hl),c
    inc hl
    djnz .fr
    ret

ShowResults:
    call ClsBlack
    ld hl,ScopaFlag              ; SCOPA on the Italian tricolore (flag header)
    ld a,0
    call BlitBanner
    ld hl,StrHdr
    ld d,15
    ld e,4
    call PrintStr
    ; CARTE
    ld hl,StrCarte
    ld d,2
    ld e,6
    call PrintStr
    ld a,(PPileN)
    ld d,15
    ld e,6
    call PrintNum
    ld a,(OPileN)
    ld d,21
    ld e,6
    call PrintNum
    ; DENARI
    ld hl,StrDen
    ld d,2
    ld e,8
    call PrintStr
    ld hl,PPile
    ld a,(PPileN)
    ld b,a
    call CountDenari
    ld d,15
    ld e,8
    call PrintNum
    ld hl,OPile
    ld a,(OPileN)
    ld b,a
    call CountDenari
    ld d,21
    ld e,8
    call PrintNum
    ; SETTEBELLO
    ld hl,StrSette
    ld d,2
    ld e,10
    call PrintStr
    ld hl,PPile
    ld a,(PPileN)
    ld b,a
    call HasSette
    ld d,15
    ld e,10
    call PrintNum
    ld hl,OPile
    ld a,(OPileN)
    ld b,a
    call HasSette
    ld d,21
    ld e,10
    call PrintNum
    ; PRIMIERA
    ld hl,StrPrim
    ld d,2
    ld e,12
    call PrintStr
    ld hl,PPile
    ld a,(PPileN)
    ld b,a
    call Primiera
    ld d,15
    ld e,12
    call PrintNum
    ld hl,OPile
    ld a,(OPileN)
    ld b,a
    call Primiera
    ld d,21
    ld e,12
    call PrintNum
    ; SCOPE
    ld hl,StrScope
    ld d,2
    ld e,14
    call PrintStr
    ld a,(PScopa)
    ld d,15
    ld e,14
    call PrintNum
    ld a,(OScopa)
    ld d,21
    ld e,14
    call PrintNum
    ; NEAPOLITAN
    ld hl,StrNapola
    ld d,2
    ld e,15
    call PrintStr
    ld a,(Pnapola)
    ld d,15
    ld e,15
    call PrintNum
    ld a,(Onapola)
    ld d,21
    ld e,15
    call PrintNum
    ; PALLE DEL CANE
    ld hl,StrPalle
    ld d,2
    ld e,16
    call PrintStr
    ld a,(Ppalle)
    ld d,15
    ld e,16
    call PrintNum
    ld a,(Opalle)
    ld d,21
    ld e,16
    call PrintNum
    ; ROUND
    ld hl,StrRound
    ld d,2
    ld e,17
    call PrintStr
    ld a,(PRound)
    ld d,15
    ld e,17
    call PrintNum
    ld a,(ORound)
    ld d,21
    ld e,17
    call PrintNum
    ; MATCH
    ld hl,StrMatch
    ld d,2
    ld e,19
    call PrintStr
    ld a,(PMatch)
    ld d,15
    ld e,19
    call PrintNum
    ld a,(OMatch)
    ld d,21
    ld e,19
    call PrintNum
    ld e,4                        ; colour accents (SCOPA header is the gold banner)
    ld a,0x45
    call FillAttrRow             ; YOU/CPU header cyan
    ld e,17
    ld a,0x45
    call FillAttrRow             ; ROUND cyan
    ld e,19
    ld a,0x46
    call FillAttrRow             ; MATCH gold
    call HighlightWinners        ; glow the winner's number green per category
    ld a,(DemoMode)
    or a
    ret z                        ; normal game: caller owns the wait prompt
    ld hl,StrDemoPrompt          ; demo: prompt under the scoring grid
    ld d,6
    ld e,21
    call PrintStr
    ld e,21
    ld a,0x47                    ; bright white
    call FillAttrRow
    ret

; HighlightWinners: for the 5 scored categories (CatWin 0..4 at rows 6,8,10,12,14) colour
; the winning side's 2-digit number bright green. Tie -> left white.
HighlightWinners:
    xor a
    ld (Tmp0),a                  ; category index 0..4
.hw:
    ld a,(Tmp0)
    cp 5
    ret nc
    ld hl,CatWin
    call addHLA
    ld a,(hl)                    ; 0=player, 1=opp, 2=tie
    cp 2
    jr z,.hwn
    or a
    ld d,15                      ; player number column
    jr z,.hwc
    ld d,21                      ; opp number column
.hwc:
    ld a,(Tmp0)
    add a,a
    add a,6                      ; row = 6 + cat*2
    ld e,a
    ld bc,0x0244                 ; B = 2 cells, C = bright green
    call SetCellAttr
.hwn:
    ld hl,Tmp0
    inc (hl)
    jr .hw

; SetCellAttr: D=col, E=row, B=count, C=attr -> paint B attribute cells.
SetCellAttr:
    ld h,0
    ld l,e
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl                    ; HL = row*32
    ld a,l
    add a,d
    ld l,a
    ld a,h
    adc a,0x58
    ld h,a                       ; HL = 0x5800 + row*32 + col
.sc:
    ld (hl),c
    inc hl
    djnz .sc
    ret

ShowWinYou:
    call ClsBlack
    xor a
    out (254),a                  ; black border for the win screen
    ld (BorderC),a
    ld hl,StrYouBig              ; big "YOU WIN" (14 cells, centred col 9)
    ld d,9
    ld e,4
    call PrintBigStr
    ld e,4
    ld a,0x44                    ; bright green
    call FillAttrRow
    ld e,5
    ld a,0x44
    call FillAttrRow
    ld hl,StrCampione
    ld d,9
    ld e,8
    call PrintStr
    ld e,8
    ld a,0x46                    ; gold
    call FillAttrRow
    call ShowScoreAndPrompt
    ld hl,WinTune
    call PlayJingle
    ret
ShowWinOpp:
    call ClsBlack
    xor a
    out (254),a                  ; black border for the loss screen
    ld (BorderC),a
    ld hl,StrCpuBig             ; big "CPU WINS" (16 cells, centred col 8)
    ld d,8
    ld e,4
    call PrintBigStr
    ld e,4
    ld a,0x42                    ; bright red
    call FillAttrRow
    ld e,5
    ld a,0x42
    call FillAttrRow
    ld hl,StrUnlucky
    ld d,5
    ld e,8
    call PrintStr
    call ShowScoreAndPrompt
    ld hl,LoseTune
    call PlayJingle
    ret

; ShowScoreAndPrompt: FINAL SCORE panel + "PRESS SPACE TO PLAY AGAIN" (shared by both)
ShowScoreAndPrompt:
    ld hl,StrFinal
    ld d,10
    ld e,12
    call PrintStr
    ld e,12
    ld a,0x46                    ; gold
    call FillAttrRow
    ld hl,StrYOU
    ld d,8
    ld e,14
    call PrintStr
    ld a,(PMatch)
    ld d,12
    ld e,14
    call PrintNum
    ld hl,StrCPU
    ld d,18
    ld e,14
    call PrintStr
    ld a,(OMatch)
    ld d,22
    ld e,14
    call PrintNum
    ld e,14
    ld a,0x45                    ; cyan
    call FillAttrRow
    ld hl,StrAgain
    ld d,3
    ld e,20
    call PrintStr
    ld e,20
    ld a,0x47                    ; bright white
    call FillAttrRow
    ret

; WaitWinner: tricolore border shimmer until SPACE (celebratory match-win wait)
WaitWinner:
    ld a,(DemoMode)
    or a
    jp nz,WaitSpaceOrDemo        ; demo: a timed 10s hold instead of the shimmer-until-SPACE
    call ReadKeys
    or a
    jr nz,WaitWinner             ; drain any held keys first
    ld c,0
.w:
    ld a,c
    and 3
    ld hl,TriCol
    call addHLA
    ld a,(hl)
    out (254),a                  ; green / white / red / white shimmer
    inc c
    ld de,0xA000
.d:
    dec de
    ld a,d
    or e
    jr nz,.d
    call ReadKeys
    bit 2,a
    jr z,.w
    xor a
    out (254),a                  ; restore black border
.fin:
    call ReadKeys
    or a
    jr nz,.fin
    ret
TriCol: defb 4,7,2,7             ; green, white, red, white

StrScopa:  defb "S C O P A",0
StrSub:    defb "ANGELO'S CARD GAME",0
StrKeys:   defb "O / P  MOVE    SPACE  PLAY",0
StrStart:  defb "PRESS SPACE TO START",0
StrHdr:    defb "YOU   CPU",0
StrCarte:  defb "CARTE",0
StrDen:    defb "DENARI",0
StrSette:  defb "SETTEBELLO",0
StrPrim:   defb "PRIMIERA",0
StrScope:  defb "SCOPE",0
StrNapola: defb "NEAPOLITAN",0           ; results-screen label (the big banner is now BlitBanner)
StrPalle:  defb "PALLE CANE",0
StrRound:  defb "ROUND",0
StrMatch:  defb "MATCH",0
StrYouBig:   defb "YOU WIN",0
StrCpuBig:   defb "CPU WINS",0
StrCampione: defb "- CAMPIONE! -",0
StrUnlucky:  defb "BETTER LUCK NEXT TIME",0
StrFinal:    defb "FINAL SCORE",0
StrAgain:    defb "PRESS SPACE TO PLAY AGAIN",0

; =================== card paint ===================
; PaintAll = build the frame in the shadow buffer, then blit it to the screen.
PaintAll:
    IF FASTSIM
    ld a,(FastSim)
    or a
    ret nz                       ; bias sim: no rendering
    ENDIF
    call RenderShadow
    xor a
    ld (DBstart),a               ; delta over the full screen
    ld a,24
    ld (DBend),a
    call DeltaBlit               ; copy only the changed cells -> tear-free board redraws
    xor a
    ld (ScrOfs),a
    ret

; ===== deal cascade: reveal freshly-dealt cards ONE AT A TIME, each drawn DIRECTLY with the
; (R30-tear-free) BlitCard after a HALT -- a single card draw stays ahead of the beam even at the
; top of the screen. NO RenderShadow/DeltaBlit per card: that was both slower (it redrew the whole
; board each time) and over the top-border budget (the per-cell delta is slower than BlitCard's
; unrolled LDI -> the CPU's cards tore). The cards live in the game state the whole time; we just
; draw them onto the already-painted empty board, in deal order. =====
DEALHOLD = 1                     ; extra frames each dealt card is held (deal rhythm; raise to slow)

BlankFF:                         ; HL=ptr, B=count -> fill 0xFF
    ld (hl),0xFF
    inc hl
    djnz BlankFF
    ret

DealPace:                        ; B = frames to hold (polls SPACE so the demo can bail)
    halt
    call DemoCheckSpace
    djnz DealPace
    ret

DrawDealtCard:                   ; A=card, D=col, E=row -> HALT, draw to the screen, brief hold
    halt
    push af
    push de
    call DemoCheckSpace          ; the demo can bail mid-deal (clobbers A)
    pop de
    pop af
    call BlitCard                ; unrolled-LDI draw -> stays ahead of the raster
    ld b,DEALHOLD
    jp DealPace

RevealHands:                     ; deal Player[k] face-up + Opp[k] as a BACK, k=0..2
    xor a
    ld (ScrOfs),a                ; draw to the live screen (0x4000)
    ld (Tmp0),a
.rh:
    ld a,(Tmp0)                  ; player card = DealSave[k] -> Player[k] @ HandCol(k), row 16
    ld hl,DealSave
    call addHLA
    ld c,(hl)
    ld a,(Tmp0)
    ld hl,Player
    call addHLA
    ld (hl),c                    ; keep state in sync (so the next PaintAll is a no-op)
    ld a,(Tmp0)
    call HandCol                 ; A=col, preserves C
    ld d,a
    ld e,16
    ld a,c
    call DrawDealtCard
    ld a,(Tmp0)                  ; opp card = DealSave[3+k] -> Opp[k]; drawn as a BACK @ row 0
    add a,3
    ld hl,DealSave
    call addHLA
    ld c,(hl)
    ld a,(Tmp0)
    ld hl,Opp
    call addHLA
    ld (hl),c
    ld a,(Tmp0)
    call HandCol
    ld d,a
    ld e,0
    ld a,BACK
    call DrawDealtCard
    ld hl,Tmp0
    inc (hl)
    ld a,(hl)
    cp 3
    jr c,.rh
    ret

RevealTable:                     ; deal Table[k] at its FINAL 4-card slot, row 8, k=0..3
    xor a
    ld (ScrOfs),a
    ld (Tmp0),a
.rt:
    ld a,(Tmp0)
    call TableSlotCol            ; A=col FIRST (it clobbers BC/DE)
    ld d,a
    ld a,(Tmp0)
    add a,6
    ld hl,DealSave
    call addHLA
    ld a,(hl)                    ; A = table card
    push af
    ld c,a
    ld a,(Tmp0)
    ld hl,Table
    call addHLA
    ld (hl),c                    ; keep state in sync
    pop af
    ld e,8
    call DrawDealtCard
    ld hl,Tmp0
    inc (hl)
    ld a,(hl)
    cp 4
    jr c,.rt
    ret

DealCascade:                     ; round start: empty board (scene cut), then deal hands + table
    IF FASTSIM
    ld a,(FastSim)
    or a
    ret nz
    ENDIF
    ld hl,Player
    ld de,DealSave
    ld bc,3
    ldir
    ld hl,Opp
    ld bc,3
    ldir
    ld hl,Table
    ld bc,4
    ldir                         ; DealSave = [P0 P1 P2 O0 O1 O2 T0 T1 T2 T3]
    ld hl,Player
    ld b,3
    call BlankFF
    ld hl,Opp
    ld b,3
    call BlankFF
    ld hl,Table
    ld b,4
    call BlankFF                 ; TableN unchanged -> fixed 4-card layout; render skips 0xFF
    call PaintAll                ; the empty table (cards cascade onto it next)
    call RevealHands
    jp RevealTable

DealRevealHands:                 ; mid-game redeal: the table stays, just cascade the 6 new cards
    IF FASTSIM
    ld a,(FastSim)
    or a
    ret nz
    ENDIF
    ld hl,Player
    ld de,DealSave
    ld bc,3
    ldir
    ld hl,Opp
    ld bc,3
    ldir
    ld hl,Player
    ld b,3
    call BlankFF
    ld hl,Opp
    ld b,3
    call BlankFF                 ; screen already shows empty hands -> no scene-cut paint needed
    jp RevealHands

; RenderShadow: render the whole frame into the shadow buffer (no blit, ScrOfs left 0x20).
; The slide animation reuses this as its per-step background.
RenderShadow:
    ld a,0x20                     ; render everything into the shadow buffer (0x6000)
    ld (ScrOfs),a
    ld hl,0x6000
    ld de,0x6001
    ld bc,0x17FF
    ld (hl),0
    ldir
    ld hl,0x7800
    ld de,0x7801
    ld bc,0x2FF
    ld (hl),0x28
    ldir
    ; CPU hand: a face-down BACK at each occupied slot's REAL column (col 6 + 7*slot),
    ; skipping empties -- mirrors the player loop below, so a played card leaves a gap
    ; exactly where it was (and the OppTurn slide starts from that same real column).
    ld ix,Opp
    ld b,3
    ld d,6
.opb:
    ld a,(ix+0)
    cp 0xFF
    jr z,.opbn
    ld a,BACK
    ld e,0
    push bc
    push de
    call BlitCard
    pop de
    pop bc
.opbn:
    inc ix
    ld a,d
    add a,7
    ld d,a
    djnz .opb
    ld a,(HideTable)
    or a
    jr nz,.notab                 ; zip animation draws the table cards itself
    ld a,(TableN)
    or a
    jr z,.notab
    ld b,a
    call TableStep               ; C = column step (shared with FlashTableCard)
    ld c,a
    ld ix,Table
    ld d,1
.tb:
    ld a,d
    cp 27
    jr nc,.tbn
    ld a,(ix+0)
    cp 0xFF
    jr z,.tbn                    ; blanked slot (deal cascade) -> skip; keeps the 4-card layout fixed
    ld e,8
    push bc
    push de
    call BlitCard
    pop de
    pop bc
.tbn:
    inc ix
    ld a,d
    add a,c
    ld d,a
    djnz .tb
.notab:
    ld ix,Player
    ld b,3
    ld d,6
.ph:
    ld a,(ix+0)
    cp 0xFF
    jr z,.phn
    ld e,16
    push bc
    push de
    call BlitCard
    pop de
    pop bc
.phn:
    inc ix
    ld a,d
    add a,7
    ld d,a
    djnz .ph
    ; status: captured-pile counts (CPU top-left, YOU bottom-left)
    ld hl,StrCPU
    ld d,0
    ld e,0
    call PrintStr
    ld a,(OPileN)
    ld d,0
    ld e,1
    call PrintNum
    ld hl,StrYOU
    ld d,0
    ld e,22
    call PrintStr
    ld a,(PPileN)
    ld d,0
    ld e,23
    call PrintNum
    call DemoOverlay             ; demo: a "PRESS SPACE TO PLAY" banner across the top
    call HighlightCursor
    ret

; Blit: copy the shadow buffer (0x6000) to the display (0x4000). No clear of the
; live screen, so the eye never sees a blank -> no flicker. HALT first so the copy
; always starts at the top of the frame -> the wholesale-redraw seam is STABLE, not a
; shimmer. (A full 6912-byte copy is ~2 frames, too big to fit the blanking interval;
; the per-card slide below is what's genuinely tear-free.)
Blit:
    halt
    ld hl,0x6000
    ld de,0x4000
    ld bc,6912
    ldir
    ret

; DeltaBlit: copy ONLY the character cells that changed from the shadow buffer (0x6000) to the
; screen (0x4000), instead of the wholesale 6912-byte Blit (which is 2+ frames -> tears as the
; raster crosses it). Pass 1 diffs shadow vs screen (reads only -> invisible, runs before HALT);
; Pass 2, after HALT, copies just the dirty cells in raster order (bitmap+attr together per cell)
; -> small enough to stay ahead of the descending beam -> tear-free even at the top of the screen.
; Dirty map parked in the unused shadow tail (0x7B00+; RenderShadow only uses 0x6000-0x7AFF).
DirtyArr equ 0x7B00              ; 768 bytes, 1 per char cell, raster order (row*32 + col)
DBattr   equ 0x7E00              ; 2-byte scratch: Pass-2 screen attribute cursor
DBstart  equ 0x7E02              ; band: first char-row to process (PaintAll 0, zip 8)
DBend    equ 0x7E03              ; band: one past the last char-row (PaintAll 24, zip 16)
DBoff    equ 0x7E04              ; computed = DBstart*32 (dirty/attr index offset)
DBcount  equ 0x7E06              ; computed = (DBend-DBstart)*32
DeltaBlit:
    ld a,(DBstart)               ; DBoff = DBstart*32
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    ld (DBoff),hl
    ld a,(DBend)                 ; DBcount = (DBend-DBstart)*32
    ld hl,DBstart
    sub (hl)
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    ld (DBcount),hl
    ld hl,DirtyArr               ; clear only the band's dirty map
    ld de,(DBoff)
    add hl,de
    ld d,h
    ld e,l
    inc de
    ld bc,(DBcount)
    dec bc
    ld (hl),0
    ldir
    ; ---- Pass 1a: bitmap diff (8 lines per cell) ----
    ld ix,DirtyArr
    ld de,(DBoff)
    add ix,de                    ; IX = &DirtyArr[band start]
    ld a,(DBstart)
    ld c,a                       ; C = char-row (band)
.brow:
    ld a,c
    and 0x18
    or 0x40
    ld h,a
    ld a,c
    and 7
    rrca
    rrca
    rrca
    ld l,a                       ; HL = screen bitmap (row C, col 0) line 0
    ld b,32
.bcol:
    push hl                      ; cell line-0 screen addr
    ld a,h
    add a,0x20
    ld d,a
    ld e,l                       ; DE = shadow line 0 (screen + 0x2000)
    ld a,(de)
    cp (hl)
    jr nz,.bdirty
    inc h
    inc d
    ld a,(de)
    cp (hl)
    jr nz,.bdirty
    inc h
    inc d
    ld a,(de)
    cp (hl)
    jr nz,.bdirty
    inc h
    inc d
    ld a,(de)
    cp (hl)
    jr nz,.bdirty
    inc h
    inc d
    ld a,(de)
    cp (hl)
    jr nz,.bdirty
    inc h
    inc d
    ld a,(de)
    cp (hl)
    jr nz,.bdirty
    inc h
    inc d
    ld a,(de)
    cp (hl)
    jr nz,.bdirty
    inc h
    inc d
    ld a,(de)
    cp (hl)
    jr nz,.bdirty
    pop hl                       ; all 8 lines equal -> not dirty (yet)
    jr .bnext
.bdirty:
    pop hl
    ld (ix+0),1
.bnext:
    inc ix
    inc l                        ; next col (lbase+col stays < 256 within a row)
    djnz .bcol
    inc c
    ld a,c
    ld hl,DBend
    cp (hl)
    jr c,.brow                   ; c < DBend -> next row
    ; ---- Pass 1b: attr diff (linear over the band) ----
    ld de,(DBoff)
    ld hl,0x5800
    add hl,de                    ; HL = screen attr band start
    ld d,h
    ld e,l
    ld a,d
    add a,0x20
    ld d,a                       ; DE = shadow attr band start
    ld ix,DirtyArr
    push de
    ld de,(DBoff)
    add ix,de
    pop de
    ld bc,(DBcount)
.acmp:
    ld a,(de)
    cp (hl)
    jr z,.aok
    ld (ix+0),1
.aok:
    inc hl
    inc de
    inc ix
    dec bc
    ld a,b
    or c
    jr nz,.acmp
    ; ---- HALT, then Pass 2: copy dirty cells in raster order ----
    halt
    di                           ; HALT synced us; keep the small copy un-interrupted
    ld ix,DirtyArr
    ld de,(DBoff)
    add ix,de                    ; IX = &DirtyArr[band start]
    ld a,(DBstart)
    ld c,a
.crow2:
    ld a,c                       ; HL = screen bitmap (row C, col 0)
    and 0x18
    or 0x40
    ld h,a
    ld a,c
    and 7
    rrca
    rrca
    rrca
    ld l,a
    ld a,c                       ; DBattr = 0x5800 + C*32 (screen attr cursor)
    ld e,a
    ld d,0
    ex de,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl                    ; C*32
    ld a,h
    add a,0x58
    ld h,a
    ld (DBattr),hl
    ex de,hl                     ; HL = bitmap addr again, DE = old (discarded)
    ld b,32
.ccol2:
    ld a,(ix+0)
    or a
    jr z,.cskip
    push hl                      ; bitmap: 8 lines shadow -> screen
    ld d,h
    ld e,l
    ld a,h
    add a,0x20
    ld h,a                       ; HL = shadow src, DE = screen dst
    ld a,(hl)
    ld (de),a
    inc h
    inc d
    ld a,(hl)
    ld (de),a
    inc h
    inc d
    ld a,(hl)
    ld (de),a
    inc h
    inc d
    ld a,(hl)
    ld (de),a
    inc h
    inc d
    ld a,(hl)
    ld (de),a
    inc h
    inc d
    ld a,(hl)
    ld (de),a
    inc h
    inc d
    ld a,(hl)
    ld (de),a
    inc h
    inc d
    ld a,(hl)
    ld (de),a
    pop hl                       ; screen cell line0
    push hl
    ld hl,(DBattr)               ; attr: shadow -> screen (same cell)
    ld d,h
    ld e,l
    ld a,h
    add a,0x20
    ld h,a
    ld a,(hl)
    ld (de),a
    pop hl
.cskip:
    ld de,(DBattr)
    inc de
    ld (DBattr),de
    inc ix
    inc l
    djnz .ccol2
    inc c
    ld a,c
    ld hl,DBend
    cp (hl)
    jr c,.crow2
    ei
    ret

; HandCol: A=hand slot (0..2) -> A = column (6 + 7*slot)
HandCol:
    ld b,a
    ld a,6
    inc b
.h:
    dec b
    jr z,.d
    add a,7
    jr .h
.d:
    ret

; TableSlotCol: A=table index -> A = column (1 + TableStep*index), clamped <=26
TableSlotCol:
    ld c,a
    call TableStep
    ld e,a
    ld b,c
    ld a,1
    inc b
.t:
    dec b
    jr z,.d
    add a,e
    jr .t
.d:
    cp 27
    ret c
    ld a,26
    ret

; SlideDelta: A=signed delta -> HL = delta<<5 (sign-extended) = 1/8 of the column travel
; per step (the slide is 8 char-row steps, one cell of vertical travel each).
SlideDelta:
    ld l,a
    ld h,0
    bit 7,a
    jr z,.p
    ld h,0xFF
.p:
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    ret

; SlideIn: slide (Played) from its hand cell (SlHandCol, SlRow) to its table cell
; (SlDestCol, row 8) in 8 cell-row steps. The static board is rendered ONCE into the
; shadow buffer; each step is HALT-synced and only erases the card's previous cell
; footprint (restored from the shadow) and redraws it at the new cell. That's ~2 cards
; of work per frame -- small enough to finish ahead of the raster, so it never tears.
SlideIn:
    IF FASTSIM
    ld a,(FastSim)
    or a
    ret nz                       ; bias sim: skip the slide animation
    ENDIF
    call RenderShadow            ; shadow = the board WITHOUT the moving card
    xor a
    ld (ScrOfs),a                ; erase + BlitCard now target the live screen (0x4000)
    ld a,(SlHandCol)
    ld h,a
    ld l,0
    ld (SlColF),hl               ; colF = handcol << 8
    ld a,(SlDestCol)
    ld hl,SlHandCol
    sub (hl)
    call SlideDelta
    ld (SlDc),hl                 ; dc = (destcol-handcol) << 5 (one eighth per step)
    halt                         ; initial frame: draw the card at the start cell
    ld a,(SlColF+1)
    ld d,a
    ld a,(SlRow)
    ld e,a
    ld a,(Played)
    call BlitCard
    ld a,(SlColF+1)
    ld (SlPrevCol),a
    ld a,(SlRow)
    ld (SlPrevRow),a
    xor a
    ld (SlStep),a                ; ease-out: start the step counter
.l:
    ld a,(SlRow)
    cp 8
    jr z,.done                   ; reached the table row
    ld a,(SlRowStep)             ; advance one cell row toward the table
    ld hl,SlRow
    add a,(hl)
    ld (SlRow),a
    ld hl,(SlColF)               ; advance the interpolated column
    ld de,(SlDc)
    add hl,de
    ld (SlColF),hl
    halt                         ; sync to the top of the frame
    call DemoCheckSpace          ; demo: SPACE during a slide also bails to the menu (clobbers A only)
    ld a,(SlPrevCol)             ; lift the card off its old cell (restore the board)
    ld d,a
    ld a,(SlPrevRow)
    ld e,a
    call EraseCardRegion
    ld a,(SlColF+1)              ; draw it at the new cell
    ld d,a
    ld a,(SlRow)
    ld e,a
    ld a,(Played)
    call BlitCard
    ld a,(SlColF+1)
    ld (SlPrevCol),a
    ld a,(SlRow)
    ld (SlPrevRow),a
    ld a,(SlStep)                ; ease-out: hold the later steps extra frames (decelerate)
    ld hl,SlEaseTab
    call addHLA
    ld b,(hl)
    ld a,b
    or a
    jr z,.noease
.ease:
    halt                         ; card stays put -> a little slower each step near the slot
    call DemoCheckSpace
    djnz .ease
.noease:
    ld hl,SlStep
    inc (hl)
    jr .l
.done:
    ret
SlEaseTab: defb 0,0,0,0,0,1,2,4  ; extra hold-frames per step 0..7 (fast whoosh -> clear settle)

; EraseCardRegion: D=col, E=char-row -> restore the 6x8-cell card footprint at that
; cell from the shadow buffer (0x6000) onto the live screen (0x4000). Lifts the sliding
; card off its previous cell without re-blitting the whole screen.
; INTERLEAVED per char-row: each char-row's 8 pixel lines AND its colour row are restored
; together, top-to-bottom, so the colour stays locked to the pixels ahead of the raster
; (the old version restored ALL pixels then ALL colour -> the colour lagged -> colour tearing).
; Optimised to match BlitCard: 8 pixel lines unrolled with LDI (no inner counter / per-line
; bc-save), char-row count in memory. ~40% faster so the slide's erase+draw fits ahead of
; the raster even at the top of the screen (tear-free for the CPU's slides too).
EraseCardRegion:
    ld a,8                       ; 8 char-rows, top to bottom
    ld (BlitCrow),a
.crow:
    push de                      ; col (D) / char-row (E)
    ; -- bitmap: this char-row's 8 pixel lines (shadow -> screen) --
    ld a,e
    and 0x18
    or 0x40
    ld h,a
    ld a,e
    and 7
    rrca
    rrca
    rrca
    or d
    ld l,a                       ; HL = screen addr of (col, char-row), pixel line 0
    DUP 8
    push hl                      ; screen line start
    ld d,h
    ld e,l                       ; DE = screen dst
    ld a,h
    add a,0x20
    ld h,a                       ; HL = shadow src (screen + 0x2000)
    ldi
    ldi
    ldi
    ldi
    ldi
    ldi                          ; 6 bytes shadow -> screen
    pop hl                       ; screen line start
    inc h                        ; next pixel line within this char-row
    EDUP
    ; -- colour: this char-row's 6 cells (shadow -> screen) --
    pop de                       ; col (D) / char-row (E)
    push de                      ; keep for the next char-row
    ld h,0
    ld l,e
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl                    ; char-row * 32
    ld a,l
    add a,d
    ld l,a
    ld a,h
    adc a,0x58
    ld h,a                       ; HL = 0x5800 + char-row*32 + col (screen attr)
    ld d,h
    ld e,l                       ; DE = screen attr dst
    ld a,h
    add a,0x20
    ld h,a                       ; HL = shadow attr src
    ldi
    ldi
    ldi
    ldi
    ldi
    ldi                          ; 6 attr cells shadow -> screen
    ; -- next char-row --
    pop de                       ; col (D) / char-row (E)
    inc e
    ld a,(BlitCrow)
    dec a
    ld (BlitCrow),a
    jp nz,.crow
    ret

; HandAttrHL: A=hand slot -> HL = attr address of that card (row 16)
HandAttrHL:
    ld b,a
    ld a,6
    inc b
.h:
    dec b
    jr z,.d
    add a,7
    jr .h
.d:
    ld l,a
    ld a,0x5A                    ; 0x5800 + 16*32 (+ShadowOfs)
    push hl
    ld hl,ScrOfs
    add a,(hl)
    pop hl
    ld h,a
    ret

; FillHandAttr: HL=attr addr, A=value -> fill the 6x8 card block
FillHandAttr:
    ld c,a
    ld a,8
.r:
    push hl
    ld b,6
.col:
    ld (hl),c
    inc hl
    djnz .col
    pop hl
    ld de,32
    add hl,de
    dec a
    jr nz,.r
    ret

; HighlightCursor: flash the selected hand card -- only while it's the player's turn
; (so the CPU's turn doesn't imply an available action), and not on an empty slot.
HighlightCursor:
    ld a,(HumanTurn)
    or a
    ret z
    ld a,(Cursor)
    ld hl,Player
    call addHLA
    ld a,(hl)
    cp 0xFF
    ret z
    ld a,(Cursor)
    call HandAttrHL
    ld a,0xF8
    jp FillHandAttr

; UnhighlightCursor: restore the cursor slot to its normal colour (card or field)
UnhighlightCursor:
    ld a,(Cursor)
    ld hl,Player
    call addHLA
    ld a,(hl)
    cp 0xFF
    ld a,0x78                    ; has a card -> white card
    jr nz,.go
    ld a,0x28                    ; empty -> cyan field
.go:
    push af
    ld a,(Cursor)
    call HandAttrHL
    pop af
    jp FillHandAttr

; PlayerChooseCapture: O/P cycle options (their table cards flash), SPACE confirms.
; -> A = chosen option index
PlayerChooseCapture:
    xor a
    ld (ChoiceIdx),a
.cl:
    ld a,(ChoiceIdx)
    call PaintChoice
.cdr:
    call ReadKeys
    or a
    jr nz,.cdr
.cw:
    call ReadKeys
    or a
    jr z,.cw
    ld e,a
.cr:
    call ReadKeys
    or a
    jr nz,.cr
    bit 2,e
    jr nz,.cdone
    bit 0,e
    jr nz,.cprev
    bit 1,e
    jr nz,.cnext
    jr .cl
.cnext:
    ld a,(ChoiceIdx)
    inc a
    ld hl,OptionN
    cp (hl)
    jr c,.cn2
    xor a
.cn2:
    ld (ChoiceIdx),a
    jr .cl
.cprev:
    ld a,(ChoiceIdx)
    or a
    jr nz,.cp2
    ld a,(OptionN)
.cp2:
    dec a
    ld (ChoiceIdx),a
    jr .cl
.cdone:
    ld a,(ChoiceIdx)
    ret

; PaintChoice: A=option index -> normal paint + flash that option's table cards
PaintChoice:
    push af
    call PaintAll
    call HighlightCursor         ; the played card is still in your hand -> flash it there (no table overlap)
    pop af
    call MaskToCapSel
    ld a,(TableN)
    ld c,a
    ld e,0
.pl:
    ld a,e
    cp c
    jr nc,.pd
    ld hl,CapSel
    ld a,e
    call addHLA
    ld a,(hl)
    or a
    jr z,.pn
    ld a,e
    push bc
    push de
    call FlashTableCard
    pop de
    pop bc
.pn:
    inc e
    jr .pl
.pd:
    ret

; TableStep: A = current table column step (<=6 ->5, ==7 ->4, >=8 ->3)
; TableStep: column step shrinks as the table fills so all cards stay visible:
;   <=6 ->5, 7 ->4, 8-9 ->3, >=10 ->2 (fits up to ~13 cards in the 32-col row).
; (Beyond ~13 a single row still overflows -> would need the deferred N/M scroll.)
TableStep:
    ld a,(TableN)
    cp 7
    jr c,.s5                     ; 0-6
    cp 8
    jr c,.s4                     ; 7
    cp 10
    jr c,.s3                     ; 8-9
    ld a,2                       ; 10+
    ret
.s3:
    ld a,3
    ret
.s4:
    ld a,4
    ret
.s5:
    ld a,5
    ret

; FlashTableCard: A=table index -> flash only that card's VISIBLE width (= step for
; an overlapped card, 6 for the last/played card), so the flash never bleeds onto the
; card drawn on top of it.
FlashTableCard:
    ld c,a                       ; C = index
    call TableStep
    ld e,a                       ; E = step
    ; col = 1 + step*index
    ld b,c
    ld a,1
    inc b
.col:
    dec b
    jr z,.cold
    add a,e
    jr .col
.cold:
    cp 27
    jr c,.colok
    ld a,26                      ; clamp to 26 -- MUST match ShowCapture's clamped draw,
.colok:                          ; else the flash lands off the played card on a full table
    ld d,a                       ; D = col
    ; width = (index < TableN-1) ? step : 6
    ld a,(TableN)
    dec a
    cp c
    jr c,.w6                     ; index past last (the played card) -> full 6
    jr z,.w6                     ; index == last -> full 6
    ld a,e                       ; else only the visible (left) step columns
    jr .gotw
.w6:
    ld a,6
.gotw:
    ld c,a                       ; C = width
    ; clamp col+width to <= 32
    ld a,d
    add a,c
    cp 33
    jr c,.noclamp
    ld a,32
    sub d
    ld c,a
.noclamp:
    ld a,d
    cp 32
    ret nc                       ; off screen -> nothing to flash
    ld l,d
    ld a,0x59                    ; attr row 8 (+ShadowOfs)
    push hl
    ld hl,ScrOfs
    add a,(hl)
    pop hl
    ld h,a
    ld a,8
.fr:
    push hl
    ld b,c                       ; width
.fcl:
    ld (hl),0xF8
    inc hl
    djnz .fcl
    pop hl
    ld de,32
    add hl,de
    dec a
    jr nz,.fr
    ret

; DrawPlayedCard: draw (Played) at the table slot just past the table cards (col
; 1+step*TableN, clamped to 26, row 8) -- exactly where the slide left it. Shared by the
; capture-choice paint AND ShowCapture so the played card stays put and visible all the way
; from slide -> choose -> capture (it isn't in Table[] yet because a capture never lands it
; on the table, so PaintAll alone would leave it nowhere).
DrawPlayedCard:
    ld a,(TableN)
    ld c,a                       ; index of the played card = TableN
    call TableStep
    ld e,a                       ; E = step
    ld b,c
    ld a,1
    inc b
.col:
    dec b
    jr z,.cold
    add a,e
    jr .col
.cold:
    cp 27
    jr c,.cok
    ld a,26
.cok:
    ld d,a
    ld a,(Played)
    ld e,8
    call BlitCard
    ret

; FlashCaptured: flash every captured table card (CapSel set) via the hardware FLASH bit,
; held by the caller's Delay. Shared by the crowded-table in-place capture displays.
FlashCaptured:
    ld a,(TableN)
    ld c,a
    ld e,0
.fc:
    ld a,e
    cp c
    jr nc,.fcd
    ld hl,CapSel
    ld a,e
    call addHLA
    ld a,(hl)
    or a
    jr z,.fcn
    ld a,e
    push bc
    push de
    call FlashTableCard
    pop de
    pop bc
.fcn:
    inc e
    jr .fc
.fcd:
    ret

; FlashCardRegion: D=col, E=char-row -> OR the FLASH bit into a 6x8 card's attribute cells
; (so a card drawn straight to the screen flashes in place). Cleared by the next PaintAll.
FlashCardRegion:
    ld h,0
    ld l,e
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl                    ; E*32
    ld a,l
    add a,d
    ld l,a
    ld a,h
    adc a,0x58
    ld h,a                       ; HL = 0x5800 + E*32 + col
    ld c,8
.fr_row:
    ld b,6
    push hl
.fr_col:
    ld a,(hl)
    or 0x80
    ld (hl),a
    inc hl
    djnz .fr_col
    pop hl
    push bc
    ld bc,32
    add hl,bc
    pop bc
    dec c
    jr nz,.fr_row
    ret

; ShowCapture: draw the played card onto the table, flash it + the captured
; set (CapSel), then pause -- so you SEE what was taken before it moves to a pile.
ShowCapture:
    call PaintAll
    call DrawPlayedCard          ; played card sits just past the table cards
    ld a,(TableN)
    call FlashTableCard          ; flash the just-played card's slot
    ld a,(TableN)
    ld c,a
    ld e,0
.fl:
    ld a,e
    cp c
    jr nc,.pause
    ld hl,CapSel
    ld a,e
    call addHLA
    ld a,(hl)
    or a
    jr z,.fln
    ld a,e
    push bc
    push de
    call FlashTableCard
    pop de
    pop bc
.fln:
    inc e
    jr .fl
.pause:
    ld hl,CaptureJingle
    call PlayJingle
    ld b,2
    call Delay
    ret

; ShowScopa: flash a SCOPA! banner across the middle.
ShowScopa:
    call PaintAll
    ld hl,ScopaBanner            ; big TrueType "SCOPA!" banner across the middle
    ld a,9
    call BlitBanner
    ld hl,ScopaJingle
    call PlayJingle
    ld b,3
    call Delay
    ret

; BlitBanner: HL = banner source (256x32 linear bitmap + 128 attr), A = top char-row.
BlitBanner:
    push af                      ; keep the row for the attr pass
    ld e,a                       ; screen bitmap addr (col 0, char-row A) -> DE
    and 0x18
    or 0x40
    ld d,a
    ld a,e
    and 7
    rrca
    rrca
    rrca
    ld e,a
    ld c,32                      ; 32 pixel rows
.brow:
    push bc
    push de
    ld bc,32
    ldir                         ; copy one 32-byte pixel row (HL advances linearly)
    pop de
    inc d                        ; next pixel row down (ZX interleave)
    ld a,d
    and 7
    jr nz,.nx
    ld a,e
    add a,0x20
    ld e,a
    jr c,.nx
    ld a,d
    sub 8
    ld d,a
.nx:
    pop bc
    dec c
    jr nz,.brow
    pop af                       ; A = top char-row
    push hl                      ; HL = source attr data (after the 1024 bitmap bytes)
    ld h,0
    ld l,a
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl                    ; HL = row*32
    ld de,0x5800
    add hl,de                    ; HL = attr dest = 0x5800 + row*32
    ex de,hl
    pop hl                       ; HL = source attr ptr
    ld bc,128                    ; 4 rows x 32, contiguous
    ldir
    ret

StrCPU:      defb "CPU",0
StrYOU:      defb "YOU",0
StrScopaBang: defb "SCOPA!",0

; BlitCard: A=cardid, D=col, E=row
; INTERLEAVED per char-row: each char-row's 8 pixel lines are followed immediately by that
; row's colour (6 cells = 0x78), top-to-bottom, so the colour stays locked to the pixels ahead
; of the raster (no colour tearing during the card slide). The attr address is carried in IX,
; which is push/pop-preserved because RenderShadow keeps the Table pointer in IX across calls.
BlitCard:
    push ix
    push de
    ld hl,CARDS
    or a
    jr z,.noff
    ld b,a
    ld de,384
.mul:
    add hl,de
    djnz .mul
.noff:
    pop de                       ; D=col, E=char-row
    ; -- IX = colour (attr) address of the top char-row (+ ScrOfs) --
    push hl                      ; save card source
    ld h,0
    ld l,e
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl                    ; char-row * 32
    ld a,l
    add a,d
    ld l,a
    ld a,h
    adc a,0x58
    ld h,a                       ; 0x5800 + char-row*32 + col
    ld a,(ScrOfs)
    add a,h
    ld h,a                       ; + ScrOfs (screen 0x5800 / shadow 0x7800)
    push hl
    pop ix                       ; IX = attr address
    pop hl                       ; restore card source
    ; -- bitmap destination -> DE --
    push de                      ; save col/char-row
    push hl                      ; save card source
    ld a,e
    and 0x18
    or 0x40
    push hl
    ld hl,ScrOfs
    add a,(hl)
    pop hl
    ld b,a                       ; dst high byte
    ld a,e
    and 7
    rrca
    rrca
    rrca
    or d
    ld c,a                       ; dst low byte
    pop hl                       ; card source
    ld d,b
    ld e,c                       ; DE = screen bitmap dst (top-left cell)
    ; INTERLEAVED per char-row (8 char-rows): 8 pixel lines THEN the 6 colour cells, so colour
    ; stays locked to the pixels ahead of the raster (the colour-tear fix). The 8 lines are
    ; unrolled with LDI (no inner counter, no per-line boundary test) and the char-row count is
    ; held in memory because LDI clobbers BC -- ~40% faster than the old LDIR-per-line loop, so
    ; the whole erase+draw now finishes before the raster reaches the top of the screen.
    ld a,8
    ld (BlitCrow),a
.crow:
    DUP 8                        ; 8 pixel lines of this char-row
    push de                      ; line start
    ldi
    ldi
    ldi
    ldi
    ldi
    ldi                          ; 6 bytes card src (HL) -> screen (DE)
    pop de
    inc d                        ; next pixel line (+0x100, same low byte)
    EDUP
    ld (ix+0),0x78               ; this char-row's 6 colour cells
    ld (ix+1),0x78
    ld (ix+2),0x78
    ld (ix+3),0x78
    ld (ix+4),0x78
    ld (ix+5),0x78
    ld bc,32
    add ix,bc                    ; attr ptr -> next char-row
    ld a,e                       ; step the bitmap dst to the next char-row
    add a,0x20
    ld e,a
    jr c,.nx                     ; crossed a third boundary -> keep the +8 in D
    ld a,d
    sub 8                        ; else undo the 8 inc-d's, stay in this third
    ld d,a
.nx:
    ld a,(BlitCrow)
    dec a
    ld (BlitCrow),a
    jp nz,.crow                  ; jp (not jr): the unrolled body is > 127 bytes
    pop de                       ; discard saved col/char-row
    pop ix
    ret

; ===================== title-screen music (Funiculi Funicula) =====================
; Two square-wave phase-accumulator channels (melody + bass) mixed onto the 1-bit
; speaker by XOR -> two voices at once. Interrupts OFF while playing (tight timing).

; PlayTitleMusic: play the tune once; SPACE skips. Returns A=1 if skipped, A=0 if finished.
PlayTitleMusic:
    call SoundEnabled
    jr nz,.play
    xor a                        ; silent -> behave as "music finished" (A=0)
    ret
.play:
    di                           ; the sample loop is timing-critical
    ld hl,0
    ld (Acc1),hl
    ld (Acc2),hl
    ld hl,FunicTune
    call PlayTune
    push af
    ld a,(BorderC)               ; restore the border (black at the title)
    out (254),a
.drain:
    ld a,0x7F                    ; if SPACE skipped, wait for release so it doesn't leak
    in a,(0xFE)
    rra
    jr nc,.drain
    pop af
    ei
    ret

; PlayTune: HL -> frames of (melodyIdx, bassIdx, ticks); 0xFF ends. A=1 skipped / 0 done.
PlayTune:
.frame:
    ld a,(hl)
    cp 0xFF
    jr z,.fin
    inc hl
    push hl                      ; melody increment <- NoteInc[idx]
    call NoteToInc
    ld (Inc1),de
    pop hl
    ld a,(hl)
    inc hl
    push hl                      ; bass increment
    call NoteToInc
    ld (Inc2),de
    pop hl
    ld a,(hl)                    ; ticks
    inc hl
    ld b,a
    push hl
.tick:
    push bc
    ld de,3150                   ; iterations per tick (~112 ms at 28226 Hz; keeps v2 tempo)
    call PlaySamples
    pop bc
    ld a,0x7F                    ; poll SPACE (0x7FFE bit 0; 0 = pressed)
    in a,(0xFE)
    rra
    jr nc,.skip
    ld a,0xBF                    ; poll H (0xBFFE bit 4) -> how-to-play
    in a,(0xFE)
    bit 4,a
    jr z,.help
    djnz .tick
    pop hl
    jr .frame
.skip:
    pop hl
    ld a,1                       ; SPACE
    ret
.help:
    pop hl
    ld a,2                       ; H
    ret
.fin:
    xor a                        ; tune finished
    ret

; NoteToInc: A = note index -> DE = NoteInc[A] (16-bit increment; index 0 = rest = 0)
NoteToInc:
    ld l,a
    ld h,0
    add hl,hl                    ; *2
    ld de,NoteInc
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ret

; PlaySamples: DE = iteration count. TWO clean square-wave voices (melody + bass) by
; TIME-DIVISION: each loop the speaker is driven by the melody bit, then the bass bit --
; two PURE tones interleaved (never XOR-mixed, so no dial-tone). Melody acc/inc in the main
; HL/BC, bass in the alternate HL'/BC'. Loop = 124 T -> 28226 Hz per voice. Accs persist.
; (Single-voice fallback: drop the exx/bass half, loop 71 T, NoteInc *1.3294, tick 5500.)
PlaySamples:
    push de
    ld hl,(Acc1)
    ld bc,(Inc1)
    exx
    ld hl,(Acc2)
    ld bc,(Inc2)
    exx
    pop de
.smp:
    add hl,bc                    ; melody phase += inc
    ld a,h
    and 0x80
    rrca
    rrca
    rrca
    out (254),a                  ; melody bit -> speaker
    exx
    add hl,bc                    ; bass phase += inc
    ld a,h
    and 0x80
    rrca
    rrca
    rrca
    out (254),a                  ; bass bit -> speaker
    exx
    dec de
    ld a,d
    or e
    jr nz,.smp
    ld (Acc1),hl
    exx
    ld (Acc2),hl
    exx
    ret

; increments = freq * 65536 / 28226 (~= freq * 2.3219). idx0 rest; 1=C3 .. 37=C6.
NoteInc:
    defw 0                                                   ; 0  rest
    defw 304,322,341,361,383,405,430,455,482,511,541,573     ; 1-12  C3..B3
    defw 608,644,682,722,765,811,859,910,964,1022,1082,1147  ; 13-24 C4..B4
    defw 1215,1287,1364,1445,1531,1622,1718,1820,1929,2043,2165,2293 ; 25-36 C5..B5
    defw 2430                                                ; 37 C6

; Funiculi Funicula -- RECONSTRUCTED in C major (verse + refrain), tarantella bass.
; NOTE: notes/tempo to be confirmed by ear (can't audition headless). Easy to edit: each
; row = melodyIdx, bassIdx, ticks.  C4=13 D4=15 E4=17 F4=18 G4=20 A4=22 B4=24
;   C5=25 D5=27 E5=29 F5=30 G5=32 A5=34 ; bass C3=1 D3=3 E3=5 F3=6 G3=8 A3=10 ; rest=0
FunicTune:
    defb 20,1,2,  25,8,2,  25,1,2,  25,8,2              ; G4 C5 C5 C5
    defb 27,1,2,  29,8,4,  27,1,2,  25,8,2              ; D5 E5(q) D5 C5
    defb 24,1,2,  25,8,4,  0,0,2                        ; B4 C5(q) rest
    defb 22,3,2,  27,10,2, 27,3,2,  27,10,2             ; A4 D5 D5 D5
    defb 25,3,2,  29,10,4, 25,3,2,  24,10,2             ; C5 E5(q) C5 B4
    defb 22,3,2,  24,10,4, 0,0,2                        ; A4 B4(q) rest
    ; refrain: "funiculi funicula"
    defb 25,1,2,  25,8,2,  25,1,2,  29,8,4              ; C5 C5 C5 E5(q)
    defb 27,3,2,  27,10,2, 27,3,2,  30,10,4             ; D5 D5 D5 F5(q)
    defb 29,5,2,  29,8,2,  27,5,2,  25,8,2              ; E5 E5 D5 C5
    defb 27,8,2,  24,8,2,  25,1,6,  0,0,2               ; D5 B4 C5(dotted) rest
    defb 0xFF

; PlayScale: ascending C major (engine pitch check). HL -> ScaleTune.
ScaleTune:                       ; bass muted, rests between notes -> isolated pure tones
    defb 13,0,4, 0,0,2, 15,0,4, 0,0,2, 17,0,4, 0,0,2, 18,0,4, 0,0,2
    defb 20,0,4, 0,0,2, 22,0,4, 0,0,2, 24,0,4, 0,0,2, 25,0,6
    defb 0xFF

; PlayJingle: HL = jingle data -> play it with the 2-voice engine (interrupts off for
; timing, like the title music). Short event fanfares.
PlayJingle:
    call SoundEnabled
    ret z
    di
    push hl
    ld hl,0
    ld (Acc1),hl
    ld (Acc2),hl
    pop hl
    call PlayTune
    ld a,(BorderC)               ; restore the game's border (was forced black by the outs)
    out (254),a
    ei
    ret

; event jingles (melodyIdx, bassIdx, ticks). C4=13 E4=17 G4=20 C5=25 E5=29 G5=32; bass
; C3=1 E3=5 G3=8 ; rest=0. ticks ~112 ms each.
ScopaJingle:                     ; bright rising arpeggio -> the signature SCOPA flourish
    defb 13,1,1, 17,5,1, 20,8,1, 25,1,1, 29,8,2, 32,1,2
    defb 0xFF
CaptureJingle:                   ; quick two-note lift (frequent -> kept very short)
    defb 25,8,1, 29,1,1
    defb 0xFF
WinTune:                         ; victory fanfare
    defb 20,1,1, 20,1,1, 20,1,2, 17,5,2, 20,8,1, 25,1,2, 32,1,4
    defb 0xFF
LoseTune:                        ; deflated chromatic sag
    defb 20,8,2, 19,8,2, 18,6,2, 17,5,4
    defb 0xFF

ScopaBanner:
    INCBIN "scopa_banner.bin"    ; 1024 bitmap + 128 attr = the big "SCOPA!" wordmark
NeapolitanBanner:
    INCBIN "neapolitan_banner.bin"
ScopaFlag:
    INCBIN "scopa_flag.bin"      ; SCOPA over the Italian tricolore (scores-screen header)

CodeEnd:
    ; Compressed title parked in the shadow-buffer region: ShowTitle expands it to the
    ; screen at boot, then the first gameplay frame reuses 0x6000 as the shadow buffer.
    ; This frees the whole 0x9400 region (code can now grow up to the state block @0xB000).
    ORG 0x6000
TitleRle:
    INCBIN "title.rle"           ; screen 1: Ace of Swords
Title2Rle:
    INCBIN "title2.rle"          ; screen 2: Ace of Coins (both fit below 0x8000; ShowTitle picks one)
    ORG 0xC000
    INCBIN "deck.bin"

    SAVESNA "scopa.sna", Start
    SAVEBIN "scopa_code.bin", 0x8000, CodeEnd-0x8000
