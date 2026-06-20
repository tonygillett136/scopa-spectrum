    DEVICE ZXSPECTRUM48
CARDS = 0xC000          ; deck.bin: 41 cards x 384 bytes (40 + back at index 40)
    ORG 0xC000
    INCBIN "deck.bin"
    ORG 0x8000
Start:
    di
    ld sp,0xBFF0
    ld a,5
    out (254),a                 ; cyan border
    ld hl,0x4000                 ; clear bitmap
    ld de,0x4001
    ld bc,0x17FF
    ld (hl),0
    ldir
    ld hl,0x5800                 ; muted cyan field (paper cyan, non-bright)
    ld de,0x5801
    ld bc,0x2FF
    ld (hl),0x28
    ldir
    ; draw the layout from DrawList (cardid, col, row), 0xFF=end
    ld ix,DrawList
.loop:
    ld a,(ix+0)
    cp 0xFF
    jr z,.done
    ld d,(ix+1)                  ; col
    ld e,(ix+2)                  ; row
    call BlitCard                ; A=cardid
    ld bc,3
    add ix,bc
    jr .loop
.done:
    jr .done

; BlitCard: A=cardid, D=cell col, E=cell row. card = 6x8 cells (48x64).
BlitCard:
    push de
    ld hl,CARDS                  ; HL = CARDS + A*384
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
    push hl                      ; save card src
    ; DE = screen addr of (col=D,row=E)
    ld a,e
    and 0x18
    or 0x40
    ld b,a                       ; B = high byte
    ld a,e
    and 7
    rrca
    rrca
    rrca
    or d
    ld c,a                       ; C = low byte  (BC = screen addr)
    pop hl                       ; HL = card src
    ld d,b
    ld e,c                       ; DE = screen
    ld a,64                      ; pixel rows
.brow:
    push af
    push de
    ld bc,6
    ldir                         ; copy 6 bytes HL(src)->DE(screen)
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
    ; attrs: 6x8 cells = white card (0x78). base = 0x5800 + row*32 + col
    pop de                       ; D=col, E=row
    ld h,0
    ld l,e
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl                    ; row*32
    ld a,l
    add a,d
    ld l,a
    ld a,h
    adc a,0x58
    ld h,a                       ; HL = attr base
    ld a,8                       ; 8 cell rows
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

DrawList:
    ; opponent hand: 3 backs (id 40), top
    defb 40,6,0
    defb 40,13,0
    defb 40,20,0
    ; table: 4 cards, middle (ace coins=0, 4 swords=23, 5 cups=14, 2 clubs=31)
    defb 0,3,8
    defb 23,10,8
    defb 14,17,8
    defb 31,24,8
    ; player hand: settebello(6), king swords(29), 3 cups(12), bottom
    defb 6,6,16
    defb 29,13,16
    defb 12,20,16
    defb 0xFF
    SAVESNA "harness_game.sna", Start
