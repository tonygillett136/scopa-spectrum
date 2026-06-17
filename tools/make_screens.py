#!/usr/bin/env python3
"""Scopa loading + title screens: big COLOUR close-ups of three card-tops, fanned,
with a tricolore SCOPA wordmark. The vivid Napoletane palette maps onto the bright
Spectrum colours -> an authentically Italian, vibrant screen."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance

REF = "/Volumes/SSD1/code/scopa_spectrum/reference_cards"
OUT = "/Volumes/SSD1/code/retro_computing/zxspectrum/scopa"

# ---------- Spectrum palette ----------
def pal(idx, br):
    c = 0xFF if br else 0xCD
    return (c if idx & 2 else 0, c if idx & 4 else 0, c if idx & 1 else 0)
def nearest(rgb):
    best, bd = (0, 0), 1e18
    for i in range(8):
        for b in (0, 1):
            if i == 0 and b == 1:   # black has no bright variant
                continue
            p = pal(i, b)
            d = (rgb[0]-p[0])**2 + (rgb[1]-p[1])**2 + (rgb[2]-p[2])**2
            if d < bd: bd, best = d, (i, b)
    return best

def img_to_scr(img):
    img = img.convert('RGB'); px = img.load()
    bm = bytearray(6144); at = bytearray(768)
    for cy in range(24):
        for cx in range(32):
            cnt = {}
            qz = {}
            for y in range(8):
                for x in range(8):
                    rgb = px[cx*8+x, cy*8+y]
                    c = nearest(rgb); cnt[c] = cnt.get(c, 0)+1
            top = sorted(cnt.items(), key=lambda kv: -kv[1])
            cols = [c for c, _ in top]
            paper = cols[0]; ink = cols[1] if len(cols) > 1 else cols[0]
            # one bright bit per cell: bright if either non-black colour is bright
            br = 0
            if paper[0] != 0 and paper[1]: br = 1
            if ink[0] != 0 and ink[1]: br = 1
            pr = pal(paper[0], br); ik = pal(ink[0], br)
            for y in range(8):
                for x in range(8):
                    c = px[cx*8+x, cy*8+y]
                    di = (c[0]-ik[0])**2+(c[1]-ik[1])**2+(c[2]-ik[2])**2
                    dp = (c[0]-pr[0])**2+(c[1]-pr[1])**2+(c[2]-pr[2])**2
                    if di < dp:
                        Y, X = cy*8+y, cx*8+x
                        off = ((Y & 0xC0) << 5) | ((Y & 7) << 8) | ((Y & 0x38) << 2) | (X >> 3)
                        bm[off] |= (0x80 >> (X & 7))
            at[cy*32+cx] = (br << 6) | (paper[0] << 3) | ink[0]
    return bytes(bm)+bytes(at)

def scr_to_png(scr, path, scale=2):
    img = Image.new('RGB', (256, 192)); px = img.load()
    bm, at = scr[:6144], scr[6144:]
    for Y in range(192):
        for X in range(256):
            off = ((Y & 0xC0) << 5) | ((Y & 7) << 8) | ((Y & 0x38) << 2) | (X >> 3)
            bit = (bm[off] >> (7-(X & 7))) & 1
            a = at[(Y >> 3)*32+(X >> 3)]
            brp, paper, ink = (a >> 6) & 1, (a >> 3) & 7, a & 7
            px[X, Y] = pal(ink, brp) if bit else pal(paper, brp)
    img.resize((256*scale, 192*scale), Image.NEAREST).save(path)

# ---------- colour close-up card ----------
def card_top(jpg, w, h, crop=0.60):
    im = Image.open(jpg).convert('RGB')
    iw, ih = im.size
    im = im.crop((0, 0, iw, int(ih*crop)))           # top portion -> close-up
    im = ImageEnhance.Color(im).enhance(1.7)          # punch the Napoletane colours
    im = ImageEnhance.Contrast(im).enhance(1.18)
    im = ImageEnhance.Brightness(im).enhance(1.05)
    im = im.resize((w, h), Image.LANCZOS).filter(ImageFilter.SHARPEN)
    # black keyline frame so the card edge reads against black
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w-1, h-1], outline=(0, 0, 0), width=2)
    return im

def paste_card(scr, card, x, y, ang):
    c = card.rotate(ang, expand=True, fillcolor=(0, 0, 0), resample=Image.BICUBIC)
    m = Image.new('L', card.size, 255).rotate(ang, expand=True, fillcolor=0, resample=Image.BICUBIC)
    scr.paste(c, (x, y), m)

# ---------- text ----------
def font(sz, black=True):
    p = "/System/Library/Fonts/Supplemental/Arial Black.ttf" if black else \
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    return ImageFont.truetype(p, sz)
def text_c(d, cx, y, s, fnt, fill):
    bb = d.textbbox((0, 0), s, font=fnt); d.text((cx-(bb[2]-bb[0])//2-bb[0], y), s, font=fnt, fill=fill)

GRN=(0,205,0); WHT=(255,255,255); RED=(205,0,0); YEL=(205,205,0)

def wordmark(img, cy, sz=40):
    """SCOPA in the tricolore: SC green, O white, PA red."""
    d = ImageDraw.Draw(img); f = font(sz)
    cols = {0:GRN,1:GRN,2:WHT,3:RED,4:RED}
    s = "SCOPA"; gap = 7
    widths = [d.textbbox((0,0),ch,font=f)[2] for ch in s]
    total = sum(widths)+gap*4; x = 128-total//2
    for i, ch in enumerate(s):
        d.text((x, cy), ch, font=f, fill=cols[i]); x += widths[i]+gap

def screen(cards, bottom, btcol):
    img = Image.new('RGB', (256, 192), (0, 0, 0))
    cw, ch = 92, 112
    L = card_top(f"{REF}/{cards[0]}", cw, ch)
    C = card_top(f"{REF}/{cards[1]}", cw, ch)
    R = card_top(f"{REF}/{cards[2]}", cw, ch)
    paste_card(img, L,   2, 42,  15)
    paste_card(img, R, 162, 42, -15)
    paste_card(img, C,  82, 34,   0)
    wordmark(img, 2)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 255, 40], fill=(0, 0, 0))      # clean band behind wordmark
    wordmark(img, 2)
    # bottom credits block. Lines are placed so the GREY credits (rows 18-21) and the
    # WHITE key line (rows 22-23) never share an 8px colour cell -> no attribute clash.
    d.rectangle([0, 144, 255, 191], fill=(0, 0, 0))
    cred = font(9, False)
    text_c(d, 128, 145, "Based on an original ZX Spectrum", cred, (190,190,190))
    text_c(d, 128, 155, "game by Angelo Colucci",           cred, (190,190,190))
    text_c(d, 128, 165, "© Tony Gillett 2026",              cred, (190,190,190))
    text_c(d, 128, 179, bottom, font(10, False), btcol)
    return img

def bodoni(sz):
    return ImageFont.truetype("/System/Library/Fonts/Supplemental/Bodoni 72.ttc", sz)

def tricolore_rule(d, x0, x1, y, h=2):
    w = (x1 - x0) // 3
    d.rectangle([x0,       y, x0+w,    y+h], fill=GRN)
    d.rectangle([x0+w,     y, x0+2*w,  y+h], fill=WHT)
    d.rectangle([x0+2*w,   y, x1,      y+h], fill=RED)

def horseman_loading():
    """Full-bleed close-up of the knight of coins (09_Nove_di_denari) + a stylised SCOPA."""
    im = Image.open(f"{REF}/09_Nove_di_denari.jpg").convert('RGB')
    iw, ih = im.size
    crop = im.crop((int(iw*0.04), int(ih*0.02), int(iw*0.98), int(ih*0.52)))  # tighter: man+horse-head+coin
    crop = ImageEnhance.Color(crop).enhance(1.28)            # easier saturation -> skin reads as skin
    crop = ImageEnhance.Contrast(crop).enhance(1.12)
    crop = ImageEnhance.Brightness(crop).enhance(1.04)
    crop = crop.resize((256, 192), Image.LANCZOS).filter(ImageFilter.SHARPEN)
    img = crop.convert('RGB')
    d = ImageDraw.Draw(img)
    # elegant SCOPA on a tight dark plate, bottom-centre
    f = bodoni(40)
    s = "SCOPA"
    bb = d.textbbox((0,0), s, font=f); tw, th = bb[2]-bb[0], bb[3]-bb[1]
    cx, by = 128, 150
    pad = 10
    d.rectangle([cx-tw//2-pad, by-6, cx+tw//2+pad, by+th+12], fill=(0,0,0))
    d.text((cx-tw//2-bb[0], by-bb[1]), s, font=f, fill=(255,255,0))   # bright yellow
    tricolore_rule(d, cx-tw//2, cx+tw//2, by+th+6, 3)
    return img

# ---- per-screen attribute clean-up ----
from collections import Counter
def despeckle(scr, rows, threshold=5):
    """Conform an ISOLATED anomalous cell (e.g. a stray bright square in the grey horse,
    or a yellow cell in the grey face) to its neighbours' dominant attribute. Only touches
    attributes (line detail in the bitmap is untouched), and leaves uniform regions alone."""
    orig = scr[6144:]
    ba = bytearray(scr)
    for cy in rows:
        for cx in range(32):
            cur = orig[cy*32+cx]; cnt = Counter()
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    if dx==0 and dy==0: continue
                    ny,nx = cy+dy, cx+dx
                    if 0<=ny<24 and 0<=nx<32: cnt[orig[ny*32+nx]] += 1
            mode,mc = cnt.most_common(1)[0]
            if mc>=threshold and mode!=cur:
                ba[6144+cy*32+cx] = mode
    return bytes(ba)

def fix_mane_specks(scr, rows):
    """Isolated BRIGHT-white cells (few bright-white neighbours) -> non-bright. Catches
    the stray bright squares in the busy grey mane while leaving the white background
    (which is a large block of bright-white cells) alone."""
    orig = scr[6144:]; ba = bytearray(scr)
    def is_bw(a): return ((a>>6)&1) and (((a>>3)&7)==7 or (a&7)==7)
    for cy in rows:
        for cx in range(32):
            a = orig[cy*32+cx]
            if not is_bw(a): continue
            bw = 0
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    if dx==0 and dy==0: continue
                    ny,nx = cy+dy, cx+dx
                    if 0<=ny<24 and 0<=nx<32 and is_bw(orig[ny*32+nx]): bw += 1
            if bw < 3:
                ba[6144+cy*32+cx] = a & ~0x40
    return bytes(ba)

def fix_white_bright(scr, rows):
    """White cells in `rows` -> force BRIGHT (uniform bright-white text)."""
    ba = bytearray(scr)
    for cy in rows:
        for cx in range(32):
            a = ba[6144+cy*32+cx]; paper=(a>>3)&7; ink=a&7
            if paper==7 or ink==7:
                ba[6144+cy*32+cx] = a | 0x40
    return bytes(ba)

def patch_cell(scr, cx, cy, attr):
    ba = bytearray(scr); ba[6144+cy*32+cx] = attr; return bytes(ba)

def rle_compress(data):
    """SCOMPACT-style byte RLE. Control byte: high bit set -> run of (c&0x7F) of the next
    byte; else literal of c bytes. Decompressor expands to exactly 6912 bytes."""
    out = bytearray(); i = 0; n = len(data)
    while i < n:
        run = 1
        while i+run < n and data[i+run] == data[i] and run < 127: run += 1
        if run >= 3:
            out.append(0x80 | run); out.append(data[i]); i += run
        else:
            start = i
            while i < n:
                r = 1
                while i+r < n and data[i+r] == data[i] and r < 127: r += 1
                if r >= 3: break
                i += 1
                if i-start == 127: break
            out.append(i-start); out += data[start:i]
    return bytes(out)

# ---- two rotating title screens (full-bleed card hero + Bodoni SCOPA + dedication) ----
def _fill(jpg, box, sat=1.28, con=1.12, bri=1.05):
    im = Image.open(f"{REF}/{jpg}").convert('RGB'); iw, ih = im.size
    x0, y0, x1, y1 = box
    c = im.crop((int(iw*x0), int(ih*y0), int(iw*x1), int(ih*y1)))
    c = ImageEnhance.Color(c).enhance(sat)
    c = ImageEnhance.Contrast(c).enhance(con)
    c = ImageEnhance.Brightness(c).enhance(bri)
    return c.resize((256, 192), Image.LANCZOS).filter(ImageFilter.SHARPEN)

def _bwordmark(img, cy, sz=34, plate=True):           # solid-yellow Bodoni SCOPA + tricolore (loading-screen style)
    d = ImageDraw.Draw(img); f = bodoni(sz); s = "SCOPA"
    bb = d.textbbox((0, 0), s, font=f); tw, th = bb[2]-bb[0], bb[3]-bb[1]; cx = 128; pad = 12
    if plate: d.rectangle([cx-tw//2-pad, cy-6, cx+tw//2+pad, cy+th+13], fill=(0, 0, 0))
    d.text((cx-tw//2-bb[0], cy-bb[1]), s, font=f, fill=(255, 255, 0))
    tricolore_rule(d, cx-tw//2, cx+tw//2, cy+th+6, 3)

_DED = ["Based on an original ZX Spectrum", "game by Angelo Colucci", "© Tony Gillett 2026"]
def _dedication(img, y0=146, keys_y=179):             # grey credits (rows 18-20) + white keys (row 22)
    d = ImageDraw.Draw(img); cf = font(9, False)
    for i, l in enumerate(_DED): text_c(d, 128, y0+i*9, l, cf, (190, 190, 190))
    text_c(d, 128, keys_y, "SPACE = START    H = HOW TO PLAY", font(9, False), (255, 255, 255))

def title_sword():                                    # screen 1: Ace of Swords, SCOPA top, dedication bottom
    img = _fill("21_Asso_di_spade.jpg", (0.18, 0.12, 0.92, 0.56), sat=1.25, con=1.08)
    d = ImageDraw.Draw(img); d.rectangle([0, 0, 255, 39], fill=(0, 0, 0))
    _bwordmark(img, 4, sz=30, plate=False)
    d.rectangle([0, 144, 255, 191], fill=(0, 0, 0)); _dedication(img)
    return img

def title_eagle():                                    # screen 2: Ace of Coins, full wings, SCOPA in the coin
    img = _fill("01_Asso_di_denari.jpg", (0.0, 0.02, 1.0, 0.50), sat=1.2, con=1.05)
    _bwordmark(img, 88, sz=34, plate=True)
    d = ImageDraw.Draw(img); d.rectangle([0, 144, 255, 191], fill=(0, 0, 0)); _dedication(img)
    return img

# two title screens (rotated at random in-game) + the loading screen
for name, im in (("title", title_sword()), ("title2", title_eagle()), ("loading", horseman_loading())):
    scr = img_to_scr(im)
    if name == "loading":
        scr = despeckle(scr, range(0, 18))              # remove stray bright squares + yellow eye cell
        scr = fix_mane_specks(scr, range(0, 18))        # isolated bright-white specks in the mane -> grey
    if name in ("title", "title2"):
        scr = fix_white_bright(scr, range(22, 24))      # the SPACE/H key line -> all bright white
    open(f"{OUT}/{name}.scr", "wb").write(scr)
    scr_to_png(scr, f"/tmp/scopa_{name}.png")
    print(f"{name}.scr -> /tmp/scopa_{name}.png")
    if name in ("title", "title2"):
        comp = rle_compress(scr)                        # SCOMPACT-packed; expands to 0x4000 at boot
        open(f"{OUT}/{name}.rle", "wb").write(comp)
        print(f"{name}.rle -> {len(comp)} bytes ({100*len(comp)//6912}% of 6912)")

# ---- big TrueType event banners (4 char rows tall, gold Arial Black on black) ----
def make_banner(name, text, fontsize=None, max_w=246, flag=False):
    HC = 4                                              # char rows
    img = Image.new('RGB', (256, HC*8), (0, 0, 0))
    d = ImageDraw.Draw(img)
    if fontsize is None:                                # auto-fit the width
        fontsize = 8
        while fontsize < 40:
            bb = d.textbbox((0, 0), text, font=font(fontsize+1))
            if bb[2]-bb[0] > max_w or bb[3]-bb[1] > HC*8-2: break
            fontsize += 1
    f = font(fontsize)
    bb = d.textbbox((0, 0), text, font=f)
    ty = (HC*8 - (bb[3]-bb[1])) // 2 - bb[1]            # vertical centre
    text_c(d, 128, ty, text, f, YEL)
    bm = bytearray()                                    # linear: 32 pixel-rows x 32 bytes
    for py in range(HC*8):
        for cx in range(32):
            b = 0
            for bit in range(8):
                r, g, bl = img.getpixel((cx*8+bit, py))
                if r+g+bl > 180: b |= (0x80 >> bit)
            bm.append(b)
    if flag:                                            # tricolore band: black letters (ink)
        at = bytearray()                                # over green/white/red PAPER thirds
        for cy in range(HC):
            for cx in range(32):
                at.append(0x60 if cx < 11 else 0x78 if cx < 22 else 0x50)
    else:
        at = bytes([0x46]) * (HC*32)                    # bright yellow ink on black
    open(f"{OUT}/{name}.bin", "wb").write(bytes(bm)+bytes(at))
    img.resize((512, HC*16), Image.NEAREST).save(f"/tmp/{name}.png")
    print(f"{name}.bin -> {len(bm)+len(at)} bytes (font {fontsize}, preview /tmp/{name}.png)")
make_banner("scopa_banner", "SCOPA!", 26)               # gold, for the in-game scopa event
make_banner("neapolitan_banner", "NEAPOLITAN")          # gold, auto-fit (longer word)
make_banner("scopa_flag", "SCOPA", 26, flag=True)       # Italian tricolore, for the scores header
