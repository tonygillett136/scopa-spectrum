    DEVICE ZXSPECTRUM48
CARDS = 0xC000          ; 4 cards x 315 bytes
CSIZE = 315
    ORG 0xC000
    INCBIN "proto_cards.bin"
    ORG 0x8000
Start:
    di
    ld sp,0xBFF0
    ld a,4
    out (254),a                 ; green border
    ; dithered green felt: bitmap = 25% black dots, attrs = green paper/black ink
    ld hl,0x4000
    ld b,0
.clr:
    ld (hl),0x22                ; sparse dither pattern byte (00100010) -> dots
    inc hl
    ld a,h
    cp 0x58
    jr nz,.clr
    ld hl,0x5800                ; attrs: green paper(4), black ink, non-bright
    ld de,0x5801
    ld bc,0x2FF
    ld (hl),0x20
    ldir
    ; blit 4 cards at (col,row): 1,8 / 8,8 / 15,8 / 22,8
    ld ix,CARDS+0*CSIZE
    ld d,1
    ld e,8
    call BlitCard
    ld ix,CARDS+1*CSIZE
    ld d,8
    ld e,8
    call BlitCard
    ld ix,CARDS+2*CSIZE
    ld d,15
    ld e,8
    call BlitCard
    ld ix,CARDS+3*CSIZE
    ld d,22
    ld e,8
    call BlitCard
.hang:
    jr .hang

; BlitCard: IX=card data, D=cell col, E=cell row. 5x7 cells, 56px tall.
BlitCard:
    push de
    ; HL = screen addr of cell (D,E) top pixel line
    ld a,e
    and 0x18
    or 0x40
    ld h,a
    ld a,e
    and 7
    rrca
    rrca
    rrca                        ; (row&7)<<5
    or d
    ld l,a
    ld b,56                     ; pixel rows
.brow:
    push bc
    push hl
    ld a,(ix+0)
    ld (hl),a
    inc hl
    ld a,(ix+1)
    ld (hl),a
    inc hl
    ld a,(ix+2)
    ld (hl),a
    inc hl
    ld a,(ix+3)
    ld (hl),a
    inc hl
    ld a,(ix+4)
    ld (hl),a
    pop hl
    ld bc,5
    add ix,bc
    inc h                       ; next pixel row down
    ld a,h
    and 7
    jr nz,.nx
    ld a,l
    add a,0x20
    ld l,a
    jr c,.nx
    ld a,h
    sub 8
    ld h,a
.nx:
    pop bc
    djnz .brow
    ; attrs: IX now at attr section (35 bytes). base = 0x5800 + E*32 + D
    pop de
    ld h,0
    ld l,e
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl                   ; E*32
    ld a,l
    add a,d
    ld l,a
    ld a,h
    adc a,0x58
    ld h,a                      ; HL = attr base
    ld a,7
.arow:
    push hl
    ld c,(ix+0)
    ld (hl),c
    inc hl
    ld c,(ix+1)
    ld (hl),c
    inc hl
    ld c,(ix+2)
    ld (hl),c
    inc hl
    ld c,(ix+3)
    ld (hl),c
    inc hl
    ld c,(ix+4)
    ld (hl),c
    ld bc,5
    add ix,bc
    pop hl
    ld bc,32
    add hl,bc
    dec a
    jr nz,.arow
    ret
    SAVESNA "harness_proto.sna", Start
