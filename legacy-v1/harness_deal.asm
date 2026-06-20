    DEVICE ZXSPECTRUM48
CARDS = 0xC000
BACK  = 40
    ORG 0xB000
Deck:    defs 40
Player:  defs 3
Opp:     defs 3
Table:   defs 12
TableN:  defs 1
DeckPos: defs 1
Seed:    defs 2
    ORG 0xC000
    INCBIN "deck.bin"
    ORG 0x8000
Start:
    di
    ld sp,0xBFF0
    ld a,5
    out (254),a
    ld a,(23672)                 ; seed from FRAMES
    ld (Seed),a
    ld a,(23673)
    ld (Seed+1),a
    call InitDeck
    call Shuffle
    call DealRound
    call Paint
.hang:
    jr .hang

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

; A = next random byte (ROM-walk PRNG)
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

; Fisher-Yates shuffle of Deck[0..39]
Shuffle:
    ld b,39                      ; i = 39 down to 1
.sh:
    call Rnd                     ; A = random
    ld c,b
    inc c                        ; C = i+1
.mod:
    cp c
    jr c,.gotj
    sub c
    jr .mod
.gotj:
    ; swap Deck[i] (=B) and Deck[A=j]
    ld hl,Deck
    ld d,0
    ld e,b
    add hl,de                    ; HL = &Deck[i]
    ld iy,Deck
    ld e,a
    add iy,de                    ; IY = &Deck[j]
    ld a,(hl)
    ld c,(iy+0)
    ld (hl),c
    ld (iy+0),a
    djnz .sh
    ret

; deal 3 player, 3 opp, 4 table
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
    ret
; deal B cards into (HL++) from Deck[DeckPos++]
DealTo:
    push hl
    ld a,(DeckPos)
    ld e,a
    ld d,0
    ld hl,Deck
    add hl,de
    pop de                       ; DE = dest
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

; Paint the table from state
Paint:
    ld hl,0x4000
    ld de,0x4001
    ld bc,0x17FF
    ld (hl),0
    ldir
    ld hl,0x5800
    ld de,0x5801
    ld bc,0x2FF
    ld (hl),0x28
    ldir
    ; opponent: 3 backs at top (cols 6,13,20 row 0)
    ld a,BACK
    ld d,6
    ld e,0
    call BlitCard
    ld a,BACK
    ld d,13
    ld e,0
    call BlitCard
    ld a,BACK
    ld d,20
    ld e,0
    call BlitCard
    ; table: TableN cards, cols start 3 step 7, row 8
    ld a,(TableN)
    ld b,a
    ld ix,Table
    ld d,3
.tb:
    ld a,(ix+0)
    ld e,8
    push bc
    push de
    call BlitCard
    pop de
    pop bc
    inc ix
    ld a,d
    add a,7
    ld d,a
    djnz .tb
    ; player hand: 3 cards cols 6,13,20 row 16
    ld ix,Player
    ld b,3
    ld d,6
.ph:
    ld a,(ix+0)
    ld e,16
    push bc
    push de
    call BlitCard
    pop de
    pop bc
    inc ix
    ld a,d
    add a,7
    ld d,a
    djnz .ph
    ret

; BlitCard: A=cardid, D=col, E=row (6x8 cells)
BlitCard:
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
    pop de
    push de
    push hl
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
    pop hl
    ld d,b
    ld e,c
    ld a,64
.brow:
    push af
    push de
    ld bc,6
    ldir
    pop de
    inc d
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
    pop af
    dec a
    jr nz,.brow
    pop de
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
    ld a,8
.arow:
    push hl
    ld b,6
.acol:
    ld (hl),0x78
    inc hl
    djnz .acol
    pop hl
    ld bc,32
    add hl,bc
    dec a
    jr nz,.arow
    ret
    SAVESNA "harness_deal.sna", Start
