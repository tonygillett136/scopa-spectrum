#!/usr/bin/env python3
"""Win / lose screen pixel art for decode-on-draw Scopa — v2: TOP QUALITY.
Improvements over v1: ordered (Bayer) dithering between each cell's 2 colours for smooth
photographic shading; wordmark moved to a BOTTOM band so the heroes' faces/crowns are in
full view; tuned saturation/contrast for vivid Spectrum colour; despeckle cleanup.
Run: .venv/bin/python art/win_screens.py
"""
import os
from collections import Counter
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

REF = "/Volumes/SSD1/code/scopa_spectrum/reference_cards"
OUT = os.path.dirname(os.path.abspath(__file__))
GRN, WHT, RED, YEL, GLD = (0,205,0), (255,255,255), (205,0,0), (205,205,0), (255,255,0)

def pal(idx, br):
    c = 0xFF if br else 0xCD
    return (c if idx & 2 else 0, c if idx & 4 else 0, c if idx & 1 else 0)
def nearest(rgb):
    best, bd = (0,0), 1e18
    for i in range(8):
        for b in (0,1):
            if i == 0 and b == 1: continue
            p = pal(i,b); d = (rgb[0]-p[0])**2+(rgb[1]-p[1])**2+(rgb[2]-p[2])**2
            if d < bd: bd, best = d, (i,b)
    return best

# 8x8 Bayer matrix (0..63) for ordered dithering between a cell's two colours
BAYER = [[0,32,8,40,2,34,10,42],[48,16,56,24,50,18,58,26],[12,44,4,36,14,46,6,38],
         [60,28,52,20,62,30,54,22],[3,35,11,43,1,33,9,41],[51,19,59,27,49,17,57,25],
         [15,47,7,39,13,45,5,37],[63,31,55,23,61,29,53,21]]

CAND = {b: [pal(i, b) for i in range(8)] for b in (0, 1)}   # 8 palette colours per brightness

def img_to_scr(img, dither=True):
    """Per-cell OPTIMAL 2-colour + optimal brightness (try every colour pair and both bright
    bits, pick min total error) + ordered dithering between the chosen pair. Best use of colour."""
    img = img.convert('RGB'); px = img.load()
    bm = bytearray(6144); at = bytearray(768)
    for cy in range(24):
        for cx in range(32):
            pix = [px[cx*8+x, cy*8+y] for y in range(8) for x in range(8)]
            best = (1e30, 0, 0, 1)
            for br in (0, 1):
                cand = CAND[br]
                dl = [[(p[0]-c[0])**2+(p[1]-c[1])**2+(p[2]-c[2])**2 for c in cand] for p in pix]
                for a in range(8):
                    for b in range(a+1, 8):
                        err = 0
                        for dr in dl:
                            da, db = dr[a], dr[b]
                            err += da if da < db else db
                        if err < best[0]: best = (err, a, b, br)
            _, ia, ib, br = best
            # paper = the index more pixels are nearest to (stable background)
            ca, cb = CAND[br][ia], CAND[br][ib]
            na = sum(1 for p in pix if (p[0]-ca[0])**2+(p[1]-ca[1])**2+(p[2]-ca[2])**2 <=
                                       (p[0]-cb[0])**2+(p[1]-cb[1])**2+(p[2]-cb[2])**2)
            if na >= 32: paper, ink = ia, ib
            else: paper, ink = ib, ia
            pr, ik = CAND[br][paper], CAND[br][ink]
            for y in range(8):
                for x in range(8):
                    c = pix[y*8+x]
                    di = (c[0]-ik[0])**2+(c[1]-ik[1])**2+(c[2]-ik[2])**2
                    dp = (c[0]-pr[0])**2+(c[1]-pr[1])**2+(c[2]-pr[2])**2
                    useink = (dp/(di+dp+1)*64 > BAYER[y&7][x&7]+0.5) if dither else (di < dp)
                    if useink:
                        Y, X = cy*8+y, cx*8+x
                        bm[((Y&0xC0)<<5)|((Y&7)<<8)|((Y&0x38)<<2)|(X>>3)] |= (0x80 >> (X & 7))
            at[cy*32+cx] = (br<<6)|(paper<<3)|ink
    return bytes(bm)+bytes(at)

def despeckle(scr, rows=range(24), threshold=5):
    orig = scr[6144:]; ba = bytearray(scr)
    for cy in rows:
        for cx in range(32):
            cur = orig[cy*32+cx]; cnt = Counter()
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    if dx==0 and dy==0: continue
                    ny,nx = cy+dy, cx+dx
                    if 0<=ny<24 and 0<=nx<32: cnt[orig[ny*32+nx]] += 1
            mode,mc = cnt.most_common(1)[0]
            if mc>=threshold and mode!=cur: ba[6144+cy*32+cx] = mode
    return bytes(ba)

def scr_to_png(scr, path, scale=2):
    img = Image.new('RGB',(256,192)); px = img.load()
    bm, at = scr[:6144], scr[6144:]
    for Y in range(192):
        for X in range(256):
            off = ((Y&0xC0)<<5)|((Y&7)<<8)|((Y&0x38)<<2)|(X>>3)
            bit = (bm[off] >> (7-(X&7))) & 1
            a = at[(Y>>3)*32+(X>>3)]; brp,paper,ink = (a>>6)&1,(a>>3)&7,a&7
            px[X,Y] = pal(ink,brp) if bit else pal(paper,brp)
    img.resize((256*scale,192*scale), Image.NEAREST).save(path)

def bodoni(sz): return ImageFont.truetype("/System/Library/Fonts/Supplemental/Bodoni 72.ttc", sz)
def arial(sz): return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", sz)
def text_c(d,cx,y,s,f,fill):
    bb=d.textbbox((0,0),s,font=f); d.text((cx-(bb[2]-bb[0])//2-bb[0], y-bb[1]),s,font=f,fill=fill)
def tricolore(d, y, h=4):
    # cell-aligned (x on 8px boundaries) so each colour sits in whole cells -> clean quantize
    d.rectangle([56, y, 103, y+h], fill=GRN)
    d.rectangle([104, y, 151, y+h], fill=WHT)
    d.rectangle([152, y, 199, y+h], fill=RED)

def hero(jpg, box, sat=1.45, con=1.18, bri=1.06, cold=False):
    im = Image.open(f"{REF}/{jpg}").convert('RGB'); iw,ih = im.size
    x0,y0,x1,y1 = box
    c = im.crop((int(iw*x0),int(ih*y0),int(iw*x1),int(ih*y1)))
    if cold:
        c = ImageEnhance.Color(c).enhance(0.22)          # near-greyscale
        r,g,b = c.split(); b = b.point(lambda v:min(255,int(v*1.3))); c = Image.merge('RGB',(r,g,b))
        con,bri = 1.12,0.90
    else:
        c = ImageEnhance.Color(c).enhance(sat)
    c = ImageEnhance.Contrast(c).enhance(con); c = ImageEnhance.Brightness(c).enhance(bri)
    return c.resize((256,192), Image.LANCZOS).filter(ImageFilter.SHARPEN)

def make(name, jpg, box, word, wordcol, sub, subcol, cold=False, wsz=23, sat=1.45):
    img = hero(jpg, box, sat=sat, cold=cold)
    d = ImageDraw.Draw(img)
    # BOTTOM black band (rows 144-191): wordmark (cr18-20) / tricolore (cr21) / score (cr22-23),
    # each on its own char-row band so nothing shares a colour cell -> zero attribute clash.
    d.rectangle([0,144,255,191], fill=(0,0,0))
    text_c(d, 128, 145, word, bodoni(wsz), wordcol)   # wordmark, rows ~145-167
    tricolore(d, 170, 4)                              # cell-aligned rule, char-row 21
    text_c(d, 128, 182, sub, arial(9), subcol)        # score, char-rows 22-23
    scr = despeckle(img_to_scr(img, dither=True))
    scr_to_png(scr, f"{OUT}/{name}.png")
    open(f"{OUT}/{name}.scr","wb").write(scr)
    print(f"  {name}")

print("generating v2 (dithered, faces visible)...")
make("win_a_kingcoins",  "10_Dieci_di_denari.jpg", (0.12,0.05,0.90,0.66), "VINCITORE!", GLD, "HAI VINTO  11 - 7", YEL)
make("win_b_knightsword","29_Nove_di_spade.jpg",   (0.05,0.03,0.97,0.66), "VINCITORE!", GLD, "HAI VINTO  11 - 7", YEL)
make("win_c_acecups",    "11_Asso_di_coppe.jpg",   (0.05,0.02,0.95,0.66), "VINCITORE!", GLD, "HAI VINTO  11 - 7", YEL)
make("win_d_kingsword",  "30_Dieci_di_spade.jpg",  (0.10,0.03,0.92,0.66), "VINCITORE!", GLD, "HAI VINTO  11 - 7", YEL)
make("lose_b_knave",     "28_Otto_di_spade.jpg",   (0.08,0.04,0.94,0.66), "PECCATO...", (200,200,200), "HAI PERSO  7 - 11", (170,170,170), cold=True)
print("done")
