; -----------------------------------------------------------------------------
; ZX0 decoder by Einar Saukas & Urusergi — "Standard" version (68 bytes).
; VERBATIM from github.com/einar-saukas/ZX0 (z80/dzx0_standard.asm).
;   HL = source (compressed), DE = destination. Self-terminates at the end marker.
;   Clobbers AF, BC, DE, HL. Preserves IX/IY.
; -----------------------------------------------------------------------------
dzx0_standard:
    ld      bc, $ffff
    push    bc
    inc     bc
    ld      a, $80
dzx0s_literals:
    call    dzx0s_elias
    ldir
    add     a, a
    jr      c, dzx0s_new_offset
    call    dzx0s_elias
dzx0s_copy:
    ex      (sp), hl
    push    hl
    add     hl, de
    ldir
    pop     hl
    ex      (sp), hl
    add     a, a
    jr      nc, dzx0s_literals
dzx0s_new_offset:
    pop     bc
    ld      c, $fe
    call    dzx0s_elias_loop
    inc     c
    ret     z
    ld      b, c
    ld      c, (hl)
    inc     hl
    rr      b
    rr      c
    push    bc
    ld      bc, 1
    call    nc, dzx0s_elias_backtrack
    inc     bc
    jr      dzx0s_copy
dzx0s_elias:
    inc     c
dzx0s_elias_loop:
    add     a, a
    jr      nz, dzx0s_elias_skip
    ld      a, (hl)
    inc     hl
    rla
dzx0s_elias_skip:
    ret     c
dzx0s_elias_backtrack:
    add     a, a
    rl      c
    rl      b
    jr      dzx0s_elias_loop
