#!/usr/bin/env python3
"""Hand-crafted 1-bit ZX Spectrum art: Re di Spade (King of Swords), Napoletane deck.
64x96 px (8x12 cells). Black ink on white paper. Bold solid outlines + interior
ordered-dither shading. Built region-by-region, back-to-front, with explicit row
spans (no fragile flood fills) so dither never leaks into the background.

Figure: crowned bearded king, frontal, holding an UPRIGHT sword in his right hand
(viewer's left), other arm out to the side, cape draping behind, tunic body+skirt,
medallion on chest, legs in tights, feet on a base. Woodcut feel.
"""
import math
from PIL import Image

W, H = 64, 96
bmp = [[0]*W for _ in range(H)]   # 1 = black ink, 0 = white paper

# ---------------------------------------------------------------- dither fields
def d_solid(x, y):  return True
def d_75(x, y):     return (x + y*3) % 4 != 0
def d_50(x, y):     return (x + y) % 2 == 0
def d_25(x, y):     return (x % 2 == 0) and (y % 2 == 0)
def d_12(x, y):     return (x % 4 == 0) and (y % 2 == 0)
def d_white(x, y):  return False

# ----------------------------------------------------------------- primitives
def setp(x, y, v=1):
    if 0 <= x < W and 0 <= y < H:
        bmp[y][x] = v

def getp(x, y):
    if 0 <= x < W and 0 <= y < H: return bmp[y][x]
    return 0

def hline(x0, x1, y, v=1):
    if x0 > x1: x0, x1 = x1, x0
    for x in range(x0, x1+1): setp(x, y, v)

def vline(x, y0, y1, v=1):
    if y0 > y1: y0, y1 = y1, y0
    for y in range(y0, y1+1): setp(x, y, v)

def line(x0, y0, x1, y1, v=1):
    dx = abs(x1-x0); dy = abs(y1-y0)
    sx = 1 if x0 < x1 else -1; sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        setp(x0, y0, v)
        if x0 == x1 and y0 == y1: break
        e2 = 2*err
        if e2 > -dy: err -= dy; x0 += sx
        if e2 < dx:  err += dx; y0 += sy

def poly_outline(pts, v=1):
    for i in range(len(pts)):
        x0,y0=pts[i]; x1,y1=pts[(i+1)%len(pts)]
        line(x0,y0,x1,y1,v)

def fill_poly(pts, dfn):
    """Scanline polygon fill with a dither function. Interior only (edges
    drawn separately by poly_outline if wanted)."""
    ys=[p[1] for p in pts]; y0,y1=min(ys),max(ys)
    for y in range(y0,y1+1):
        xs=[]
        n=len(pts)
        for i in range(n):
            ax,ay=pts[i]; bx,by=pts[(i+1)%n]
            if ay==by: continue
            if (ay<=y<by) or (by<=y<ay):
                t=(y-ay)/(by-ay); xs.append(ax+t*(bx-ax))
        xs.sort()
        for k in range(0,len(xs)-1,2):
            xl=int(math.ceil(xs[k])); xr=int(math.floor(xs[k+1]))
            for x in range(xl,xr+1):
                if dfn(x,y): setp(x,y,1)

def shade_region(spans, dfn):
    for y,(xl,xr) in spans.items():
        for x in range(xl,xr+1):
            if dfn(x,y): setp(x,y,1)

# =====================================================================
def build():
    global bmp
    bmp = [[0]*W for _ in range(H)]
    cx = 32

    # =============================================================
    # LAYER 0: CAPE (behind everything) as TWO side panels that stay
    # OUTSIDE the body silhouette, plus a hem dipping below the skirt.
    # Dithered 75% (dark fabric). Drawn back-to-front so body covers any overlap.
    # =============================================================
    # left cape panel: from left shoulder out & down to lower-left, back in
    cape_l = [(28,31),(20,35),(16,52),(17,70),(22,79),(28,73),(28,50)]
    fill_poly(cape_l, d_50); poly_outline(cape_l)
    # right cape panel
    cape_r = [(36,31),(44,35),(48,52),(47,70),(42,79),(36,73),(36,50)]
    fill_poly(cape_r, d_50); poly_outline(cape_r)
    # a single soft fold line per panel (sparse, woodcut)
    line(20,42,19,68); line(44,42,45,68)

    # =============================================================
    # LAYER 1: BODY TUNIC (over cape). body (mid tone 25%) + skirt (50%)
    # =============================================================
    # tunic body (chest). Clear a 1px-larger white region first (a moat) so the
    # body silhouette pops crisply against the dithered cape, then dither inside.
    body_moat=[(26,29),(38,29),(41,47),(23,47)]
    body=[(27,30),(37,30),(40,46),(24,46)]
    fill_poly(body_moat, d_white)   # white moat
    fill_poly(body, d_25)           # mid tone interior
    poly_outline(body)
    # skirt (below belt) - flares; LIGHT tone (25%) so it reads distinct from the
    # 50% cape behind it, with a 1px white moat at the sides.
    skirt_moat=[(23,46),(41,46),(44,64),(20,64)]
    skirt=[(24,47),(40,47),(43,63),(21,63)]
    fill_poly(skirt_moat, d_white)
    fill_poly(skirt, d_25)
    poly_outline(skirt)
    # belt - solid band
    hline(24,40,46); hline(24,40,47)
    # skirt vertical pleat folds (woodcut)
    for fx in (27,30,34,37): line(fx,48,fx+ (1 if fx>32 else -1),62)
    # skirt hem (solid) with little scallops
    hline(21,43,63)
    for hx in range(22,43,3): setp(hx,64)

    # =============================================================
    # LAYER 2: NECK + HEAD + CROWN
    # =============================================================
    # neck: keep it white, defined by two short side strokes (no top/bottom box,
    # so it doesn't clash with the beard above or the collar below)
    neck=[(30,26),(35,26),(36,30),(29,30)]
    fill_poly(neck, d_white)
    line(30,27,29,30)        # left side of neck
    line(35,27,36,30)        # right side of neck
    # collar / ermine trim across the shoulders (solid with a couple of nicks)
    line(29,30,22,32); line(36,30,43,32)
    line(22,32,28,31); line(43,32,37,31)
    setp(25,31,0); setp(40,31,0)   # white nicks in the trim

    # HEAD: oval, connected to neck. Kept LIGHT (white skin) with crisp features.
    # Bottom kept open (no solid jaw line) so the beard alone defines the chin.
    head_pts=[(28,15),(27,17),(27,20),(28,23),(30,25),(33,26),(36,25),(38,23),
              (39,20),(39,17),(38,15),(33,14)]
    fill_poly(head_pts, d_white)
    # draw only the upper/side outline of the head (skip the bottom, beard owns it)
    line(33,14,28,15); line(28,15,27,17); line(27,17,27,20); line(27,20,28,23)
    line(33,14,38,15); line(38,15,39,17); line(39,17,39,20); line(39,20,38,23)

    # --- FACE (drawn light, single deliberate strokes; cheeks stay white) ---
    # hair: short locks at the temples only
    setp(27,16); setp(27,17); setp(28,16)          # left lock
    setp(39,16); setp(39,17); setp(38,16)          # right lock
    # brow line (two brows with a gap)
    hline(30,32,18); hline(34,36,18)
    # eyes (pupils set below the brows, in white)
    setp(31,20); setp(35,20)
    # nose: a vertical ridge down the centre
    vline(33,19,22)
    # moustache: two short whiskers directly under the nose
    setp(31,23); setp(32,23); setp(34,23); setp(35,23)
    # mouth: a single short line with white lips above
    hline(32,34,24)
    # neat pointed beard at the chin (the only mass below the mouth)
    setp(31,25); setp(35,25)
    setp(32,25); setp(33,25); setp(34,25)
    setp(33,26); setp(32,26); setp(34,26)
    setp(33,27)   # beard tip

    # CROWN over top of head: a solid jewelled band + a row of pointed peaks
    # with little balls (the Napoletane spiky crown).
    cb_y=13  # crown band baseline (sits just above the brow/head top)
    # band: two solid rails with a WHITE jewel row between (so it reads as a band)
    hline(25,39,cb_y); hline(25,39,cb_y+2)
    vline(25,cb_y,cb_y+2); vline(39,cb_y,cb_y+2)
    hline(26,38,cb_y+1,0)                  # clear the middle to white
    for jx in (27,29,32,35,37): setp(jx,cb_y+1)   # jewel dots in the band
    # five spiky peaks rising from the top rail (centre tallest), each tipped
    peaks=[(26,8),(29,7),(32,5),(35,7),(38,8)]
    for (px,ty) in peaks:
        vline(px,ty,cb_y-1)
        setp(px-1,ty+1); setp(px+1,ty+1)   # little flare at base of spike
        setp(px,ty-1)                       # ball on tip
    # scallop the rail between spikes (small dips)
    for dx in (27,28,30,31,33,34,36,37):
        pass

    # =============================================================
    # LAYER 3: MEDALLION on chest (over tunic)
    # =============================================================
    mcx,mcy=32,37
    # clear a white disc then ring
    for yy in range(mcy-3,mcy+4):
        for xx in range(mcx-3,mcx+4):
            if (xx-mcx)**2+(yy-mcy)**2<=9: setp(xx,yy,0)
    for ang in range(0,360,20):
        x=round(mcx+3*math.cos(math.radians(ang))); y=round(mcy+3*math.sin(math.radians(ang)))
        setp(x,y)
    # tiny face dots inside
    setp(31,36); setp(33,36); setp(32,38)

    # =============================================================
    # LAYER 4: ARMS (over cape & body)
    # =============================================================
    # RIGHT arm (viewer-right) extended out & slightly down, sleeve puffy then bare.
    # Made bolder so the open-hand gesture (as in the reference) reads clearly.
    rsleeve=[(37,31),(45,32),(49,37),(46,41),(38,36)]
    fill_poly(rsleeve, d_white); fill_poly(rsleeve, d_25); poly_outline(rsleeve)
    # bare forearm (two solid edges, a tone between)
    line(49,37,56,41); line(46,41,55,45)
    forearm=[(49,37),(56,41),(55,45),(46,41)]
    fill_poly(forearm, d_white); poly_outline(forearm)
    # hand (open) at far right
    hand=[(56,41),(59,40),(60,44),(57,47),(54,45)]
    fill_poly(hand, d_white); poly_outline(hand)
    # fingers hint (thumb + splayed fingers)
    setp(60,42); setp(58,46); setp(56,46)

    # LEFT arm (viewer-left) bent UP, fist gripping sword
    lsleeve=[(28,31),(22,33),(20,40),(25,42),(28,36)]
    fill_poly(lsleeve, d_white); fill_poly(lsleeve, d_25); poly_outline(lsleeve)
    # forearm down to fist
    line(20,40,19,52); line(25,42,24,52)
    # fist (gloved): clean white moat then a solid-bordered 50%-toned grip hand
    fist_moat=[(16,50),(27,50),(27,59),(16,59)]
    fill_poly(fist_moat, d_white)
    fist=[(18,51),(25,51),(25,58),(18,58)]
    fill_poly(fist, d_50); poly_outline(fist)
    # knuckle lines across the fist
    hline(19,24,53); hline(19,24,56)

    # =============================================================
    # LAYER 5: SWORD (upright, in left fist) — drawn ON TOP
    # =============================================================
    sbx=21   # blade centre x (aligned with fist)
    # white moat so the steel pops crisply against the cape dither behind it
    for y in range(10,53):
        for x in range(sbx-3,sbx+4): setp(x,y,0)
    for x in range(sbx-8,sbx+9): setp(x,51,0); setp(x,52,0); setp(x,53,0)
    # point
    line(sbx,11,sbx-2,15); line(sbx,11,sbx+2,15)
    # blade edges
    vline(sbx-2,15,50); vline(sbx+2,15,50)
    # fuller (sparse centre) — implies the metal ridge/highlight
    for y in range(16,50,3): setp(sbx,y)
    # crossguard
    hline(sbx-6,sbx+6,51); hline(sbx-6,sbx+6,52)
    setp(sbx-7,51); setp(sbx+7,51)
    # grip + pommel below the fist — clear a clean moat first so they read
    for y in range(58,66):
        for x in range(sbx-4,sbx+5): setp(x,y,0)
    # grip (bound, short)
    vline(sbx-1,58,61); vline(sbx+1,58,61); setp(sbx,59); setp(sbx,61)
    # round pommel
    for (px,py) in [(sbx-1,62),(sbx,62),(sbx+1,62),
                    (sbx-2,63),(sbx-1,63),(sbx,63),(sbx+1,63),(sbx+2,63),
                    (sbx-1,64),(sbx,64),(sbx+1,64)]:
        setp(px,py)

    # =============================================================
    # LAYER 6: LEGS (tights) + FEET + BASE
    # =============================================================
    # legs: clear one wide white moat behind both, then dither each leg lightly
    legs_moat=[(24,62),(40,62),(42,86),(22,86)]
    fill_poly(legs_moat, d_white)
    # left leg
    lleg=[(28,63),(31,63),(30,84),(26,84)]
    fill_poly(lleg, d_12); poly_outline(lleg)
    # right leg
    rleg=[(33,63),(36,63),(38,84),(34,84)]
    fill_poly(rleg, d_12); poly_outline(rleg)
    # knee garters
    hline(26,31,72); hline(34,38,72)
    # shoes
    sh_l=[(24,84),(31,84),(31,88),(22,88)]
    fill_poly(sh_l,d_white); fill_poly(sh_l,d_50); poly_outline(sh_l)
    sh_r=[(33,84),(40,84),(42,88),(33,88)]
    fill_poly(sh_r,d_white); fill_poly(sh_r,d_50); poly_outline(sh_r)
    # base / platform
    base=[(16,89),(48,89),(48,93),(16,93)]
    fill_poly(base, d_white); fill_poly(base, d_25); poly_outline(base)
    # base vertical staves (woodcut)
    for bx in range(18,48,3): vline(bx,90,92)

    # =============================================================
    # CARD BORDER (rounded) — last, on top, with white margin
    # =============================================================
    hline(2,W-3,1); hline(2,W-3,H-2)
    vline(1,2,H-3); vline(W-2,2,H-3)
    for (x,y) in [(1,1),(2,1),(1,2),(W-2,1),(W-3,1),(W-2,2),
                  (1,H-2),(2,H-2),(1,H-3),(W-2,H-2),(W-3,H-2),(W-2,H-3)]:
        setp(x,y,0)
    setp(2,2); setp(W-3,2); setp(2,H-3); setp(W-3,H-3)
    return bmp

build()

def png(path, scale=6):
    im=Image.new("L",(W,H)); p=im.load()
    for y in range(H):
        for x in range(W): p[x,y]=0 if bmp[y][x] else 255
    im.resize((W*scale,H*scale),Image.NEAREST).save(path)

def blob():
    out=bytearray()
    for y in range(H):
        for c in range(8):
            v=0
            for bit in range(8):
                if bmp[y][c*8+bit]: v|=0x80>>bit
            out.append(v)
    for _ in range(8*12): out.append(0x78)
    return bytes(out)

if __name__=="__main__":
    import sys
    if len(sys.argv)>1:
        # ad-hoc preview path (used during iteration)
        png(sys.argv[1]); print("rendered", sys.argv[1])
    else:
        # final deliverables
        base="/Volumes/SSD1/code/retro_computing/zxspectrum/scopa/"
        png(base+"king_hand.png", scale=6)
        data=blob()
        assert len(data)==768+96, len(data)
        open(base+"king_hand.bin","wb").write(data)
        print("wrote king_hand.bin (%d bytes) + king_hand.png" % len(data))
