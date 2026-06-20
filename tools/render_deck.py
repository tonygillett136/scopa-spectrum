#!/usr/bin/env python3
"""Render the website montages (deck.png + cards_hero.png) straight from the game's deck.bin,
so they always match the SHIPPED card art (incl. the R42 crowned kings). deck.bin = 41 cards x
384 bytes, each a linear 1bpp 48x64 bitmap (MSB = leftmost pixel; 1 = ink). Card ids: 0-9 denari,
10-19 coppe, 20-29 spade, 30-39 bastoni, 40 = BACK. Theme colours sampled from the live site."""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DECK = os.path.join(HERE, "..", "deck.bin")
IMG  = os.path.join(HERE, "..", "site", "img")
PAPER, INK, FELT = (245, 243, 230), (20, 20, 20), (11, 79, 79)
b = open(DECK, "rb").read()

def card(idx, scale):
    o = idx * 384
    im = Image.new("RGB", (48, 64), PAPER); px = im.load()
    for row in range(64):
        for bx in range(6):
            byte = b[o + row * 6 + bx]
            for bit in range(8):
                if byte & (0x80 >> bit):
                    px[bx * 8 + bit, row] = INK
    return im.resize((48 * scale, 64 * scale), Image.NEAREST)

# --- full deck montage: 8 x 5, ids 0..39 ---
S, COLS, ROWS, GAP = 3, 8, 5, 12
CW, CH = 48 * S, 64 * S
W, H = COLS * CW + (COLS + 1) * GAP, ROWS * CH + (ROWS + 1) * GAP
M = Image.new("RGB", (W, H), FELT)
for idx in range(40):
    r, c = divmod(idx, COLS)
    M.paste(card(idx, S), (GAP + c * (CW + GAP), GAP + r * (CH + GAP)))
M.save(os.path.join(IMG, "deck.png"))
print(f"deck.png  = {W}x{H}  (8x5, ids 0-39)")

# --- hero strip: seven of coins, ace of cups, king of coins, knight of cups, king of clubs ---
HERO = [6, 10, 9, 18, 39]
S2, GAP2 = 7, 20
cw, ch = 48 * S2, 64 * S2
W2, H2 = len(HERO) * cw + (len(HERO) + 1) * GAP2, ch + 2 * GAP2
Hm = Image.new("RGB", (W2, H2), FELT)
for i, idx in enumerate(HERO):
    Hm.paste(card(idx, S2), (GAP2 + i * (cw + GAP2), GAP2))
Hm.save(os.path.join(IMG, "cards_hero.png"))
print(f"cards_hero.png = {W2}x{H2}  (ids {HERO}; kings 9 & 39 crowned)")
