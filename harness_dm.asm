    DEVICE ZXSPECTRUM48
CSIZE = 864          ; 96*8 bitmap + 12*8 attr
    ORG 0xC000
    INCBIN "dm_cards.bin"
    ORG 0x8000
Start:
    di
    ld sp,0xBFF0
    ld a,1
    out (254),a
    ld hl,0x4000
    ld de,0x4001
    ld bc,0x17FF
    ld (hl),0
    ldir
    ld hl,0x5800
    ld de,0x5801
    ld bc,0x2FF
    ld (hl),0x08                ; navy paper, subtle
    ldir
    ld hl,0xC000
    ld b,0
    ld c,6
    call BlitCard
    ld hl,0xC000+CSIZE
    ld b,8
    ld c,6
    call BlitCard
    ld hl,0xC000+2*CSIZE
    ld b,16
    ld c,6
    call BlitCard
    ld hl,0xC000+3*CSIZE
    ld b,24
    ld c,6
    call BlitCard
.hang:
    jr .hang

; BlitCard: HL=card data, B=cell col, C=cell row. 8 cells wide, 12 tall.
BlitCard:
    push bc                     ; save col/row for attr step
    ; DE = screen addr of (col=B,row=C) top line
    ld a,c
    and 0x18
    or 0x40
    ld d,a
    ld a,c
    and 7
    rrca
    rrca
    rrca
    or b
    ld e,a
    ld b,96                     ; pixel rows
.brow:
    push de
    ld c,8
    ld a,b                      ; preserve row counter (B clobbered by LDIR? no, BC is count)
    push af
    ld b,0
    ldir                        ; copy 8 bytes HL->DE (BC=8)
    pop af
    ld b,a
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
    djnz .brow
    ; attrs: HL now at attr section (96 bytes). base = 0x5800 + C*32 + B
    pop bc                      ; B=col, C=row
    push hl                     ; save attr src
    ld h,0
    ld l,c
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl                   ; C*32
    ld a,l
    add a,b
    ld e,a
    ld a,h
    adc a,0x58
    ld d,a                      ; DE = attr base
    pop hl                      ; HL = attr src
    ld a,12
.arow:
    push de
    ld bc,8
    ldir                        ; copy 8 attr bytes HL->DE
    pop de
    ex de,hl
    ld bc,32
    add hl,bc
    ex de,hl                    ; DE += 32 (next attr row)
    dec a
    jr nz,.arow
    ret
    SAVESNA "harness_dm.sna", Start
