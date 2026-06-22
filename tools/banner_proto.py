#!/usr/bin/env python3
"""PROTOTYPE the prettified celebration banners + golden light-sweep shimmer, BEFORE any Z80.
Renders each wordmark in Rockwell at the real banner resolution (256x32, 1bpp letters), then
simulates the shimmer the way the ULA actually does it -- colour is per 8x8 CHAR CELL, so the
'light sweep' is a bright band of character-columns moving left->right, not smooth pixels.
Outputs filmstrips to /tmp for review. Two colour variants to choose from."""
import os
from PIL import Image, ImageDraw, ImageFont

ROCK = "/System/Library/Fonts/Supplemental/Rockwell.ttc"
W, H = 256, 32                      # banner = 32 char-cols x 4 char-rows
# Spectrum CRT-ish colours
BLACK = (0, 0, 0)
YEL   = (200, 200, 0)              # ink 6        (normal "gold")
BYEL  = (255, 255, 0)             # ink 6 BRIGHT (bright gold)
WHT   = (255, 255, 255)           # ink 7 BRIGHT (the glint)

def render_mask(word):
    """Rockwell, fit to the 256x32 banner (max cap height, must also fit width), 1-bit mask."""
    md = ImageDraw.Draw(Image.new("L", (4, 4)))
    sz = 40
    while sz > 8:
        f = ImageFont.truetype(ROCK, sz, index=0)
        bb = md.textbbox((0, 0), word, font=f)
        w, h = bb[2]-bb[0], bb[3]-bb[1]
        if w <= W-6 and h <= H-2:
            break
        sz -= 1
    f = ImageFont.truetype(ROCK, sz, index=0)
    bb = md.textbbox((0, 0), word, font=f)
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    x = (W - (bb[2]-bb[0]))//2 - bb[0]
    y = (H - (bb[3]-bb[1]))//2 - bb[1]
    d.text((x, y), word, font=f, fill=255)
    return img.point(lambda v: 1 if v >= 110 else 0)   # threshold to 1-bit

def cell_colour(c, band, variant):
    """colour for char-column c (0..31) given the sweep-band centre, per the chosen variant."""
    dist = abs(c - band)
    if variant == "A":             # bright-gold base, 1-cell WHITE glint
        return WHT if dist == 0 else BYEL
    elif variant == "C":           # bright-gold base, 3-cell WHITE sweep (always-bright letters, bolder glint)
        return WHT if dist <= 1 else BYEL
    else:                          # "B": warm gold base, 3-cell graded sweep (yellow->white->yellow)
        if dist == 0: return WHT
        if dist == 1: return BYEL
        return YEL

def frame(mask, band, variant):
    out = Image.new("RGB", (W, H), BLACK); px = out.load(); m = mask.load()
    for y in range(H):
        for x in range(W):
            if m[x, y]:
                px[x, y] = cell_colour(x//8, band, variant)
    return out

def filmstrip(word, variant, nframes=11, scale=2):
    mask = render_mask(word)
    bands = [int(-2 + (34)*i/(nframes-1)) for i in range(nframes)]   # sweep centre -2 .. 32
    strip = Image.new("RGB", (W*scale, (H+4)*nframes*scale), (30, 30, 30))
    for i, b in enumerate(bands):
        fr = frame(mask, b, variant).resize((W*scale, H*scale), Image.NEAREST)
        strip.paste(fr, (0, i*(H+4)*scale))
    return strip

OUT = "/tmp"
for word, tag in [("SCOPA!", "scopa"), ("NEAPOLITAN", "neap"), ("SCOPA", "header")]:
    # static (font only, flat bright gold) so the Rockwell shape is clear
    s = frame(render_mask(word), -99, "A").resize((W*3, H*3), Image.NEAREST)
    s.save(f"{OUT}/banner_{tag}_static.png")
for word, tag in [("SCOPA!", "scopa"), ("NEAPOLITAN", "neap")]:
    for v in ("A", "B", "C"):
        filmstrip(word, v).save(f"{OUT}/sweep_{tag}_{v}.png")
print("wrote /tmp/banner_*_static.png (Rockwell font) + /tmp/sweep_{scopa,neap}_{A,B}.png (shimmer filmstrips)")
print("variant A = bright-gold + 1-cell white glint;  variant B = warm-gold + 3-cell graded sweep")
