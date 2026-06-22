#!/usr/bin/env python3
"""PROTOTYPE attribute-only shimmer effects for the VINCITORE win screen, BEFORE any Z80.
Loads the real win.scr, finds the GOLD RAY cells (sunburst), and animates ONLY their attributes
(gold<->white) -- exactly what a Z80 attr-shimmer would do (bitmap untouched -> tear-free, ~cheap).
Renders faithful animated GIFs + filmstrips to win_proto/. RUN FROM scopa/."""
import os, math
from PIL import Image

SCR = "win.scr"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "win_proto")
os.makedirs(OUT, exist_ok=True)
PAL  = [(0,0,0),(0,0,205),(205,0,0),(205,0,205),(0,205,0),(0,205,205),(205,205,0),(205,205,205)]
PALB = [(0,0,0),(0,0,255),(255,0,0),(255,0,255),(0,255,0),(0,255,255),(255,255,0),(255,255,255)]
d = open(SCR,"rb").read()
BMP = d[:6144]; ATTR = list(d[6144:6912])

def scr_addr(x,y): return ((y&0xC0)<<5) | ((y&7)<<8) | ((y&0x38)<<2) | (x>>3)

# centre of the sunburst (the halo/king centre), in CELL coords, + halo radius to exclude the figure
CX, CY, R_HALO = 16.0, 11.0, 9.3

def is_gold(a):
    ink=a&7; paper=(a>>3)&7; br=(a>>6)&1
    return br and (ink==6 or paper==6)

# precompute the ray cells (gold, outside the halo, ABOVE the VINCITORE banner) + polar coords
BANNER_TOP = 20                   # rows 20-23 = the VINCITORE banner -> keep it static gold
RAYS = {}
for cy in range(24):
    for cx in range(32):
        a = ATTR[cy*32+cx]
        dist = math.hypot(cx-CX, cy-CY)
        if is_gold(a) and dist > R_HALO and cy < BANNER_TOP:
            RAYS[(cx,cy)] = (dist, math.atan2(cy-CY, cx-CX))

def lit(a):                       # gold cell -> white version (ink/paper 6 -> 7, keep bright)
    ink=a&7; paper=(a>>3)&7
    if ink==6: ink=7
    if paper==6: paper=7
    return 0x40 | (paper<<3) | ink

# the VINCITORE banner cells (gold, rows 20-23) -> get the SCOPA-style L->R light sweep
BANNER = [(cx,cy) for cy in range(BANNER_TOP,24) for cx in range(32) if is_gold(ATTR[cy*32+cx])]
BMIN = min(cx for cx,cy in BANNER); BMAX = max(cx for cx,cy in BANNER)

def litbanner(a):                 # banner gold -> bright white glint
    ink=a&7; paper=(a>>3)&7
    if ink==6: ink=7
    if paper==6: paper=7
    return 0x40 | (paper<<3) | ink

# star cells: sparse white-ink-on-dark dots in the black gaps between rays (outside the halo)
def pixcount(cx,cy):
    n=0
    for yy in range(8):
        b=BMP[scr_addr(cx*8, cy*8+yy)]; n+=bin(b).count("1")
    return n
STARS={}
for cy in range(24):
    for cx in range(32):
        a=ATTR[cy*32+cx]
        dist=math.hypot(cx-CX,cy-CY)
        # black-gap cells (NOT gold rays) outside the halo that hold a few sparkle pixels
        if dist>R_HALO and cy<BANNER_TOP and not is_gold(a) and 1<=pixcount(cx,cy)<=26:
            STARS[(cx,cy)] = ((cx*7+cy*13)%17)/17.0      # per-cell twinkle phase
def staroff(a): return a & 0xF8                          # clear ink -> the white dot vanishes
def staron(a):  return (a & 0x38) | 0x47                 # keep paper, bright white ink (dot glows)

def render(attr):
    im = Image.new("RGB",(256,192)); px=im.load()
    for y in range(192):
        ay=y>>3
        for x in range(256):
            b=BMP[scr_addr(x,y)]; bit=(b>>(7-(x&7)))&1
            a=attr[ay*32+(x>>3)]; ink=a&7; paper=(a>>3)&7; pal=PALB if (a>>6)&1 else PAL
            px[x,y]=pal[ink] if bit else pal[paper]
    return im.resize((512,384),Image.NEAREST)

def frame(effect, t):
    """t in [0,1). returns a modified attr list with the ray cells shimmered."""
    a = ATTR[:]
    maxd = max(v[0] for v in RAYS.values())
    for (cx,cy),(dist,ang) in RAYS.items():
        i = cy*32+cx
        if effect=="radial":                      # expanding rings of light from the centre
            R = R_HALO + t*(maxd-R_HALO+3)
            near = abs(dist - R) < 1.6
            if near: a[i] = lit(ATTR[i])
        elif effect=="rotate":                     # a beam of light sweeping around the rays
            beam = t*2*math.pi
            da = abs((ang-beam+math.pi)%(2*math.pi)-math.pi)
            if da < 0.55: a[i] = lit(ATTR[i])
        elif effect=="breathe":                    # all rays pulse gold<->white together
            if (math.sin(t*2*math.pi)*0.5+0.5) > 0.6: a[i] = lit(ATTR[i])
    return a

EFFECTS = ["radial","rotate","breathe"]
N = 36
for eff in EFFECTS:
    frames=[render(frame(eff,i/N)) for i in range(N)]
    frames[0].save(f"{OUT}/win_{eff}.gif", save_all=True, append_images=frames[1:], duration=70, loop=0, disposal=2)
    # compact filmstrip: 4 evenly-spaced frames at 1x, side by side (fits a viewer)
    small=[f.resize((256,192),Image.NEAREST) for f in frames]
    strip=Image.new("RGB",(256*4+6*3,192),(20,20,20))
    for k in range(4):
        strip.paste(small[k*N//4],(k*(256+6),0))
    strip.save(f"{OUT}/strip_{eff}.png")
render(ATTR).save(f"{OUT}/win_base.png")

# ---- the DELUXE combined sequence: one-time BURST then SETTLE (radial rays + banner sweep + twinkle)
maxd = max(v[0] for v in RAYS.values())
def frame_deluxe(i, N, burst=14):
    a = ATTR[:]
    if i < burst:                                   # BURST: fast bright ring + banner flash + stars on
        p = i/burst
        R = R_HALO + p*(maxd-R_HALO+4); bw = 2.6
        for (cx,cy),(dist,ang) in RAYS.items():
            if abs(dist-R) < bw: a[cy*32+cx]=lit(ATTR[cy*32+cx])
        for (cx,cy) in BANNER: a[cy*32+cx]=litbanner(ATTR[cy*32+cx])
        for (cx,cy) in STARS:  a[cy*32+cx]=staron(ATTR[cy*32+cx])
    else:                                           # SETTLE: slow pulse + banner sweep + twinkle
        s = (i-burst)/(N-burst)
        R = R_HALO + (math.sin(s*2*math.pi - math.pi/2)*0.5+0.5)*(maxd-R_HALO+3)
        for (cx,cy),(dist,ang) in RAYS.items():
            if abs(dist-R) < 1.5: a[cy*32+cx]=lit(ATTR[cy*32+cx])
        sweepx = (s*1.8 % 1.0)*(BMAX-BMIN+4) + BMIN - 2
        for (cx,cy) in BANNER:
            if abs(cx-sweepx) < 1.5: a[cy*32+cx]=litbanner(ATTR[cy*32+cx])
        for (cx,cy),ph in STARS.items():
            a[cy*32+cx] = staron(ATTR[cy*32+cx]) if math.sin((s*6+ph)*2*math.pi)>0.2 else staroff(ATTR[cy*32+cx])
    return a
ND=64
dframes=[render(frame_deluxe(i,ND)) for i in range(ND)]
dframes[0].save(f"{OUT}/win_deluxe.gif", save_all=True, append_images=dframes[1:], duration=70, loop=0, disposal=2)
small=[f.resize((256,192),Image.NEAREST) for f in dframes]
strip=Image.new("RGB",(256*4+18,192),(20,20,20))
for k,fr in enumerate([4,12,28,48]):                # 2 burst frames + 2 settle frames
    strip.paste(small[fr],(k*(256+6),0))
strip.save(f"{OUT}/strip_deluxe.png")

print(f"ray cells: {len(RAYS)}  banner cells: {len(BANNER)}  star cells: {len(STARS)}")
print(f"-> {os.path.realpath(OUT)}/  : win_{{radial,rotate,breathe,deluxe}}.gif + strip_*.png + win_base.png")
