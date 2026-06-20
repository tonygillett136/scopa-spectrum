; scopa-beam-race — sandbox for ZX0 decode-on-draw + beam racing.
; MODE selects the milestone harness (set by the build script via -DMODE=n).
;   MODE 2 = decode all 41 cards into 0xC000.. and halt (host verifies byte-exact vs deck.bin)
    DEVICE ZXSPECTRUM48

    IFNDEF MODE
MODE = 2
    ENDIF
    IFNDEF DEC                  ; which ZX0 decoder: 0=standard(68B) 1=turbo(126B) 2=mega(673B)
DEC = 0
    ENDIF

DECODE_TARGET = 0xC000          ; M2: 41 cards x 384B decoded here (mirrors the raw deck layout)
CARD = 384
DecodeBuf = 0xBA00              ; single 384B scratch buffer for decode-on-draw (no card cache)

    ORG 0x8000
Start:
    di
    ld sp,0xBFF0
    ld a,2                      ; border red = working
    out (254),a

    IF MODE == 2
    call DecodeAllCards
    ld a,4                      ; border green = all decoded, idle
    out (254),a
.idle:
    jr .idle
    ENDIF

    IF MODE == 21
    ; TIMING: decode cards round-robin into one buffer for exactly 250 frames, counting
    ; each card decoded. per-card T-states ~= 250*69888 / count (a slight OVERestimate: the
    ; ROM IM1 ISR steals <~1% per frame, so pure decode is a touch faster -> budget-safe).
    ei
    im 1
    xor a
    ld (TmCard),a
    ld hl,0
    ld (TmCount),hl
    ld hl,(0x5C78)              ; FRAMES (ROM frame counter)
    ld (TmStart),hl
.tloop:
    ld a,(TmCard)              ; src = DeckZX0 + Index[card]
    ld l,a
    ld h,0
    add hl,hl
    ld bc,Index
    add hl,bc
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld hl,DeckZX0
    add hl,bc                  ; HL = source
    ld de,0xC000               ; one fixed scratch buffer
    call DecodeSel
    ld hl,(TmCount)            ; count this card
    inc hl
    ld (TmCount),hl
    ld a,(TmCard)              ; advance card 0..40 cyclic
    inc a
    cp 41
    jr c,.tkeep
    xor a
.tkeep:
    ld (TmCard),a
    ld hl,(0x5C78)            ; elapsed = FRAMES - start
    ld de,(TmStart)
    or a
    sbc hl,de
    ld de,250
    or a
    sbc hl,de
    jr c,.tloop               ; elapsed < 250 frames -> keep decoding
    di
    ld a,2
    out (254),a
.th:
    jr .th
    ENDIF

    IF MODE == 3
    ; DECODE-ON-DRAW static board: clear, then for each (cardid,col,row) decode the card into
    ; the single DecodeBuf and BlitCardBuf it. Proves the rendering path works straight from a
    ; freshly-decompressed buffer with NO persistent decoded-card cache. (No beam sync yet.)
    xor a
    ld (ScrOfs),a
    call ClsBlack
    call DrawBoard
    ld a,4
    out (254),a
.h3:
    jr .h3
    ENDIF

    IF MODE == 4
    ; BEAM-RACED DECODE-ON-DRAW (the PIPELINE). A card at the TOP of the screen riffles through
    ; all 41 faces, one per frame, each freshly decompressed. Per frame:
    ;   HALT (sync to frame top) -> blit the ALREADY-decoded card at the top in the top-border
    ;   window (tear-free, ahead of the beam, ~9.7k T) -> THEN decompress the NEXT card into the
    ;   buffer during the frame's slack (~60k T, runs in uncontended RAM so the beam doesn't slow
    ;   it). So decode lags display by one frame; the tear-critical blit always fits the top border.
    ; Border timing markers (visible on a CRT): CYAN = blit, RED = decode, BLACK = idle.
    xor a
    ld (ScrOfs),a
    call ClsBlack
    ei
    im 1
    xor a
    ld (AnimId),a
    call DecodeCur               ; pre-decode card 0 into DecodeBuf
.loop4:
    halt                        ; sync to the frame interrupt (~start of the top border)
    ld a,5                      ; CYAN: tear-critical blit (must finish before the beam)
    out (254),a
    ld d,13
    ld e,0                      ; top-centre, char-row 0 (tightest beam case)
    call BlitCardBuf            ; blit the card decoded last frame (ahead of the beam)
    ld a,2                      ; RED: decode the NEXT card during the frame's slack
    out (254),a
    ld a,(AnimId)
    inc a
    cp 41
    jr c,.k4
    xor a
.k4:
    ld (AnimId),a
    call DecodeCur              ; decompress next card into DecodeBuf (for next frame)
    xor a                       ; BLACK: idle until the next frame
    out (254),a
    jr .loop4
    ENDIF

    IF MODE == 5
    ; SLIDE (the definitive tear test): the settebello slides left<->right across the table band
    ; (char-row 12), 8px/frame, redrawn EVERY frame from a fresh decompression. Per frame:
    ;   HALT -> [CYAN] erase old rect + blit new rect (tear-critical, must beat the beam to row 96
    ;   @ ~35,840 T; ~18-25k T of work -> fits) -> [RED] decode the card again (full per-frame load,
    ;   ~21k T, in uncontended RAM) -> [BLACK] idle. Motion makes any tearing/lag visible on a CRT.
    xor a
    ld (ScrOfs),a
    call ClsBlack
    ei
    im 1
    ld a,6                       ; settebello (7 of denari)
    ld (AnimId),a
    call DecodeCur               ; pre-decode into DecodeBuf
    ld a,1
    ld (SlideX),a
    ld (SlideDir),a
    ld (PrevX),a
.loop5:
    halt
    ld a,5                       ; CYAN: tear-critical erase+blit
    out (254),a
    ld a,(PrevX)
    ld d,a
    ld e,12
    call EraseRect               ; clear the old position
    ld a,(SlideX)
    ld d,a
    ld e,12
    call BlitCardBuf             ; draw at the new position (from last frame's decode)
    ld a,2                       ; RED: re-decode (the full per-frame decode-on-draw load)
    out (254),a
    call DecodeCur
    xor a                        ; BLACK: idle
    out (254),a
    ; advance position, bounce between col 1 and 25
    ld a,(SlideX)
    ld (PrevX),a
    ld c,a
    ld a,(SlideDir)
    add a,c
    ld (SlideX),a
    cp 25
    jr nz,.cl5
    ld a,0xFF                    ; hit right edge -> move left
    ld (SlideDir),a
    jr .loop5
.cl5:
    cp 1
    jr nz,.loop5
    ld a,1                       ; hit left edge -> move right
    ld (SlideDir),a
    jr .loop5
    ENDIF

; ---------------------------------------------------------------------------
; DecodeAllCards: for card 0..40, decompress its ZX0 stream into 0xC000 + card*384.
; dzx0_standard leaves DE = dest+384 after each card (exactly one card), so DE flows
; straight into the next slot — we only need to reset HL (source) each iteration.
; ---------------------------------------------------------------------------
DecodeAllCards:
    ld de,DECODE_TARGET
    xor a
    ld (CurCard),a
.loop:
    ld a,(CurCard)
    ld l,a
    ld h,0
    add hl,hl                   ; card*2 (index entry is 2 bytes)
    ld bc,Index
    add hl,bc
    ld c,(hl)
    inc hl
    ld b,(hl)                   ; BC = byte offset of this card's stream in deck.zx0
    ld hl,DeckZX0
    add hl,bc                   ; HL = source (compressed stream)
    push de                     ; (DE flows, but guard against any future change)
    call DecodeSel              ; decode 384 bytes to (DE); DE -> DE+384
    pop bc                      ; discard old dest
    ld a,(CurCard)
    inc a
    ld (CurCard),a
    cp 41
    jr nz,.loop
    ret

; DecodeSel: jp to the ZX0 decoder selected by DEC (entry: HL=src, DE=dst).
DecodeSel:
    IF DEC == 0
    jp dzx0_standard
    ELSE
    IF DEC == 1
    jp dzx0_turbo
    ELSE
    jp dzx0_mega
    ENDIF
    ENDIF

; ===========================================================================
; ZX0 decoder by Einar Saukas & Urusergi — "Standard" version (68 bytes).
; VERBATIM from github.com/einar-saukas/ZX0 (z80/dzx0_standard.asm).
;   HL = source (compressed), DE = destination. Self-terminates at the end marker.
; ===========================================================================
dzx0_standard:
    ld      bc, $ffff           ; preserve default offset 1
    push    bc
    inc     bc
    ld      a, $80
dzx0s_literals:
    call    dzx0s_elias         ; obtain length
    ldir                        ; copy literals
    add     a, a                ; copy from last offset or new offset?
    jr      c, dzx0s_new_offset
    call    dzx0s_elias         ; obtain length
dzx0s_copy:
    ex      (sp), hl            ; preserve source, restore offset
    push    hl                  ; preserve offset
    add     hl, de              ; calculate destination - offset
    ldir                        ; copy from offset
    pop     hl                  ; restore offset
    ex      (sp), hl            ; preserve offset, restore source
    add     a, a                ; copy from literals or new offset?
    jr      nc, dzx0s_literals
dzx0s_new_offset:
    pop     bc                  ; discard last offset
    ld      c, $fe              ; prepare negative offset
    call    dzx0s_elias_loop    ; obtain offset MSB
    inc     c
    ret     z                   ; check end marker
    ld      b, c
    ld      c, (hl)             ; obtain offset LSB
    inc     hl
    rr      b                   ; last offset bit becomes first length bit
    rr      c
    push    bc                  ; preserve new offset
    ld      bc, 1               ; obtain length
    call    nc, dzx0s_elias_backtrack
    inc     bc
    jr      dzx0s_copy
dzx0s_elias:
    inc     c                   ; interlaced Elias gamma coding
dzx0s_elias_loop:
    add     a, a
    jr      nz, dzx0s_elias_skip
    ld      a, (hl)             ; load another group of 8 bits
    inc     hl
    rla
dzx0s_elias_skip:
    ret     c
dzx0s_elias_backtrack:
    add     a, a
    rl      c
    rl      b
    jr      dzx0s_elias_loop

    IF DEC == 1
    INCLUDE "dzx0_turbo.asm"
    ENDIF
    IF DEC == 2
    INCLUDE "dzx0_mega.asm"
    ENDIF

; ===========================================================================
; Rendering (decode-on-draw): decode a card into the single DecodeBuf, then BlitCardBuf
; it to the screen. BlitCardBuf is scopa's tear-free BlitCard with the source fixed to
; DecodeBuf (no CARDS+id*384 cache lookup) — interleaved 8 pixel-lines + 6 attr cells per
; char-row, unrolled LDI. 48x64 card = 6 cols x 8 char-rows, attr 0x78 (bright white/black).
; ===========================================================================
DecodeCur:                       ; decode the card whose id is in AnimId into DecodeBuf
    ld a,(AnimId)
DecodeInto:                      ; A = cardid -> decompress into DecodeBuf
    ld l,a
    ld h,0
    add hl,hl
    ld bc,Index
    add hl,bc
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld hl,DeckZX0
    add hl,bc                    ; HL = compressed source
    ld de,DecodeBuf
    jp DecodeSel                 ; tail-call: decoder's ret returns to DecodeInto's caller

DrawBoard:                       ; walk BoardData: (cardid,col,row) triples, 0xFF ends
    ld hl,BoardData
.b:
    ld a,(hl)
    cp 0xFF
    ret z
    inc hl
    ld d,(hl)
    inc hl
    ld e,(hl)
    inc hl                       ; A=cardid, D=col, E=char-row
    push hl                      ; save data ptr
    push de                      ; save col/row
    call DecodeInto              ; A=cardid -> DecodeBuf
    pop de
    call BlitCardBuf             ; draw DecodeBuf at (col,row)
    pop hl
    jr .b

BlitCardBuf:                     ; D=col, E=char-row -> draw DecodeBuf to the screen
    push ix
    ld hl,DecodeBuf              ; source = freshly decoded card (vs scopa's CARDS+id*384)
    push hl
    ld h,0
    ld l,e
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl                    ; char-row*32
    ld a,l
    add a,d
    ld l,a
    ld a,h
    adc a,0x58
    ld h,a                       ; 0x5800 + row*32 + col
    ld a,(ScrOfs)
    add a,h
    ld h,a
    push hl
    pop ix                       ; IX = attr address
    pop hl
    push de
    push hl
    ld a,e
    and 0x18
    or 0x40
    push hl
    ld hl,ScrOfs
    add a,(hl)
    pop hl
    ld b,a
    ld a,e
    and 7
    rrca
    rrca
    rrca
    or d
    ld c,a
    pop hl
    ld d,b
    ld e,c                       ; DE = screen bitmap dst (top-left cell)
    ld a,8
    ld (BlitCrow),a
.crow:
    DUP 8
    push de
    ldi
    ldi
    ldi
    ldi
    ldi
    ldi
    pop de
    inc d
    EDUP
    ld (ix+0),0x78
    ld (ix+1),0x78
    ld (ix+2),0x78
    ld (ix+3),0x78
    ld (ix+4),0x78
    ld (ix+5),0x78
    ld bc,32
    add ix,bc
    ld a,e
    add a,0x20
    ld e,a
    jr c,.nx
    ld a,d
    sub 8
    ld d,a
.nx:
    ld a,(BlitCrow)
    dec a
    ld (BlitCrow),a
    jp nz,.crow
    pop de
    pop ix
    ret

EraseRect:                       ; D=col, E=char-row -> clear a 6x8-cell region to black
    ld a,8
    ld (BlitCrow),a
.er_row:
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
    ld l,a                       ; HL = bitmap (col,row) line 0
    ld b,8
.er_line:
    push hl
    ld (hl),0
    inc l
    ld (hl),0
    inc l
    ld (hl),0
    inc l
    ld (hl),0
    inc l
    ld (hl),0
    inc l
    ld (hl),0
    pop hl
    inc h
    djnz .er_line
    push de                      ; attrs: 6 cells at 0x5800 + row*32 + col
    ld h,0
    ld l,e
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    ld a,l
    add a,d
    ld l,a
    ld a,h
    adc a,0x58
    ld h,a
    ld (hl),0
    inc hl
    ld (hl),0
    inc hl
    ld (hl),0
    inc hl
    ld (hl),0
    inc hl
    ld (hl),0
    inc hl
    ld (hl),0
    pop de
    inc e
    ld a,(BlitCrow)
    dec a
    ld (BlitCrow),a
    jr nz,.er_row
    ret

ClsBlack:                        ; bitmap -> 0, attrs -> 0 (black background)
    ld hl,0x4000
    ld de,0x4001
    ld bc,6143
    ld (hl),0
    ldir
    ld hl,0x5800
    ld de,0x5801
    ld bc,767
    ld (hl),0
    ldir
    ret

BoardData:                       ; a Scopa-ish board: (cardid, col, char-row)
    defb 9, 4, 0                 ; opp:    Re denari
    defb 18, 12, 0               ;         Cavallo coppe
    defb 26, 20, 0               ;         7 spade
    defb 6, 1, 8                 ; table:  settebello (7 denari)
    defb 19, 8, 8                ;         Re coppe
    defb 20, 15, 8               ;         Asso spade
    defb 34, 22, 8               ;         5 bastoni
    defb 7, 4, 16                ; player: Fante denari
    defb 39, 12, 16              ;         Re bastoni
    defb 11, 20, 16              ;         2 coppe
    defb 0xFF

; ---------------------------------------------------------------------------
ScrOfs:     defb 0
BlitCrow:   defb 0
AnimId:     defb 0
SlideX:     defb 0
PrevX:      defb 0
SlideDir:   defb 0
CurCard:    defb 0
TmCard:     defb 0
TmCount:    defw 0
TmStart:    defw 0

; ---- data ----
    ORG 0x9000
DeckZX0:
    INCBIN "deck.zx0"
Index:
    INCBIN "deck_index.bin"
EndData:

    SAVESNA "main.sna", Start
    SAVEBIN "main_code.bin", Start, EndData-Start    ; 0x8000..end-of-index, for the .tap loader
