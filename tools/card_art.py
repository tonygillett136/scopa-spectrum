#!/usr/bin/env python3
"""ZX Spectrum card-art tool. A card = WxH-cell grid; per-pixel ink bitmap +
per-cell attribute (paper,ink,bright). Renders an EXACT Spectrum-colour PNG so we
iterate art quality in Python, then emit Z80 data once happy."""
from PIL import Image
# Spectrum palette (bright variants used here)
PAL = {
 ('k',0):(0,0,0),('k',1):(0,0,0),
 ('b',0):(0,0,192),('b',1):(0,0,255),
 ('r',0):(192,0,0),('r',1):(255,0,0),
 ('m',0):(192,0,192),('m',1):(255,0,255),
 ('g',0):(0,192,0),('g',1):(0,255,0),
 ('c',0):(0,192,192),('c',1):(0,255,255),
 ('y',0):(192,192,0),('y',1):(255,255,0),
 ('w',0):(192,192,192),('w',1):(255,255,255),
}
INK={'k':0,'b':1,'r':2,'m':3,'g':4,'c':5,'y':6,'w':7}
class Card:
    def __init__(self,cw,ch):
        self.cw,self.ch=cw,ch; self.W,self.H=cw*8,ch*8
        self.bmp=[[0]*self.W for _ in range(self.H)]
        # per cell: (paper_char, ink_char, bright)
        self.attr=[[('w','k',1) for _ in range(cw)] for _ in range(ch)]
    def px(self,x,y,v=1):
        if 0<=x<self.W and 0<=y<self.H: self.bmp[y][x]=v
    def cell(self,cx,cy,paper,ink,bright=1):
        if 0<=cx<self.cw and 0<=cy<self.ch: self.attr[cy][cx]=(paper,ink,bright)
    def fill_paper(self,paper,ink='k',bright=1):
        for cy in range(self.ch):
            for cx in range(self.cw): self.attr[cy][cx]=(paper,ink,bright)
    def frame(self):  # thin black border on white edge cells
        for x in range(self.W): self.px(x,0);self.px(x,self.H-1)
        for y in range(self.H): self.px(0,y);self.px(self.W-1,y)
        # round corners a touch
        for x,y in[(0,0),(1,0),(0,1),(self.W-1,0),(self.W-2,0),(self.W-1,1),
                   (0,self.H-1),(1,self.H-1),(0,self.H-2),
                   (self.W-1,self.H-1),(self.W-2,self.H-1),(self.W-1,self.H-2)]:
            self.bmp[y][x]=0
    def png(self,path,scale=6):
        im=Image.new("RGB",(self.W,self.H))
        p=im.load()
        for y in range(self.H):
            for x in range(self.W):
                paper,ink,br=self.attr[y//8][x//8]
                col=PAL[(ink,br)] if self.bmp[y][x] else PAL[(paper,br)]
                p[x,y]=col
        im=im.resize((self.W*scale,self.H*scale),Image.NEAREST)
        im.save(path)

import math
def sun(card,cx,cy,style):
    """draw a sunburst coin centred in cell (cx,cy) [8x8]. style sets colour scheme."""
    ox,oy=cx*8,cy*8
    # 8-lobed sunburst mask in 8x8
    def instar(px,py):
        dx=px-3.5;dy=py-3.5;r=math.hypot(dx,dy);a=math.atan2(dy,dx)
        spike=1.7+1.9*max(0,math.cos(8*a))
        return r<=spike
    if style=='yw':       # yellow ink sun on white paper (colour-correct, low contrast)
        card.cell(cx,cy,'w','y');  draw=lambda px,py:instar(px,py)
    elif style=='ybk':    # yellow sun on BLACK cell (vivid, faithful medallion, blocky)
        card.cell(cx,cy,'k','y');  draw=lambda px,py:instar(px,py)
    elif style=='medal':  # black round medallion (ink) with white sun cut out (mono, round)
        card.cell(cx,cy,'w','k')
        def draw(px,py):
            dx=px-3.5;dy=py-3.5;r=math.hypot(dx,dy)
            if r>3.4: return False         # outside disc -> white
            return not instar(px,py)        # disc black except sun (white)
    elif style=='goldtile': # yellow paper, black sun engraving (gold tile)
        card.cell(cx,cy,'y','k')
        def draw(px,py):
            dx=px-3.5;dy=py-3.5;r=math.hypot(dx,dy)
            if r>3.4: return False
            return not instar(px,py)
    for py in range(8):
        for px in range(8):
            if draw(px,py): card.px(ox+px,oy+py)

# settebello layout: cells (col,row) for 7 coins (2-1-2-2), interior 3 cols x 5 rows
COINS=[(1,1),(3,1),(2,2),(1,3),(3,3),(1,4),(3,4)]
for style in ('yw','ybk','medal','goldtile'):
    c=Card(5,7); c.fill_paper('w','k'); c.frame()
    for (cx,cy) in COINS: sun(c,cx,cy,style)
    c.png(f"/tmp/sette_{style}.png")
    print("wrote /tmp/sette_"+style+".png")

# ---- Ace of coins: one big ornate gold coin, centred ----
def big_coin(card,cx,cy,cells):
    """gold coin spanning cells x cells, centred at cell (cx,cy) top-left."""
    n=cells*8; ox,oy=cx*8,cy*8; cc=(n-1)/2
    for dy in range(cells):
        for dx in range(cells): card.cell(cx+dx,cy+dy,'y','k')
    for py in range(n):
        for px in range(n):
            ddx=px-cc;ddy=py-cc;r=math.hypot(ddx,ddy);a=math.atan2(ddy,ddx)
            spike=cc*0.55+cc*0.42*max(0,math.cos(8*a))
            ring = (cc*0.92<r<=cc*0.99)
            inner= r<=spike
            centre = r<= cc*0.18
            if ring or (inner and not centre): card.px(ox+px,oy+py)  # black engraving on gold
a=Card(5,7); a.fill_paper('w','k'); a.frame()
big_coin(a,1,2,3)                  # 3x3-cell coin centred
a.png("/tmp/ace_coins.png"); print("wrote /tmp/ace_coins.png")

# ---- 3 of cups (coppe): red cups on white ----
def cup(card,cx,cy):
    card.cell(cx,cy,'w','r')
    g=["..####..",".######.","########",".######.","..####..","...##...","..####..",".######."]
    ox,oy=cx*8,cy*8
    for py,row in enumerate(g):
        for px,ch in enumerate(row):
            if ch=='#': card.px(ox+px,oy+py)
t=Card(5,7); t.fill_paper('w','k'); t.frame()
for (cx,cy) in [(1,1),(3,1),(2,4)]: cup(t,cx,cy)
t.png("/tmp/tre_coppe.png"); print("wrote /tmp/tre_coppe.png")

# ---- Figure: trace Re di spade (auto), colour per cell ----
def trace_figure(card, jpg, thresh=110, sat=60):
    src=Image.open(jpg).convert("RGB")
    src=src.crop(src.getbbox()) if src.getbbox() else src
    src=src.resize((card.W,card.H),Image.LANCZOS)
    sp=src.load()
    # per-cell dominant saturated colour
    def classify(rr,gg,bb):
        mx=max(rr,gg,bb);mn=min(rr,gg,bb)
        if mx-mn<sat: return 'k' if mx<128 else 'w'
        if rr>gg and rr>bb: return 'r'
        if bb>=rr and bb>=gg: return 'b'
        if gg>rr and gg>bb: return 'g'
        if rr>180 and gg>150: return 'y'
        return 'k'
    for cy in range(card.ch):
        for cx in range(card.cw):
            # dominant colour of cell
            from collections import Counter
            cnt=Counter()
            for py in range(8):
                for px in range(8):
                    rr,gg,bb=sp[cx*8+px,cy*8+py]; cnt[classify(rr,gg,bb)]+=1
            col=[c for c,_ in cnt.most_common() if c not in ('k','w')]
            ink=col[0] if col else 'k'
            card.cell(cx,cy,'w',ink)
    # bitmap = dark/edge pixels (the linework + coloured fills become ink)
    for py in range(card.H):
        for px in range(card.W):
            rr,gg,bb=sp[px,py]
            if (rr+gg+bb)/3 < 200:    # any non-near-white pixel = ink
                card.px(px,py)
f=Card(5,7); f.fill_paper('w','k'); f.frame()
trace_figure(f,"/Volumes/SSD1/code/scopa_spectrum/reference_cards/30_Dieci_di_spade.jpg")
f.png("/tmp/re_spade_trace.png"); print("wrote /tmp/re_spade_trace.png")

# ---- Figure WOODCUT style: flat colour = cell PAPER, black INK = outlines only ----
def trace_woodcut(card, jpg, darkthr=85, sat=55, inset=1):
    src=Image.open(jpg).convert("RGB")
    if src.getbbox(): src=src.crop(src.getbbox())
    iw=card.W-2*inset; ih=card.H-2*inset
    src=src.resize((iw,ih),Image.LANCZOS); sp=src.load()
    def classify(rr,gg,bb):
        mx=max(rr,gg,bb);mn=min(rr,gg,bb)
        if mx-mn<sat: return 'w' if mx>150 else ('k' if mx<90 else 'w')
        if rr>=gg and rr>=bb:
            return 'y' if gg>140 else 'r'
        if bb>=rr and bb>=gg: return 'b'
        return 'g'
    from collections import Counter
    # paper per cell = dominant colour over its inset region (white default at edges)
    for cy in range(card.ch):
        for cx in range(card.cw):
            cnt=Counter()
            for py in range(8):
                for px in range(8):
                    sx=cx*8+px-inset; sy=cy*8+py-inset
                    if 0<=sx<iw and 0<=sy<ih:
                        rr,gg,bb=sp[sx,sy]; cnt[classify(rr,gg,bb)]+=1
                    else: cnt['w']+=1
            # prefer a strong colour if present, else white/black
            order=cnt.most_common()
            paper='w'
            for c,n in order:
                if c in ('r','b','g','y') and n>=10: paper=c; break
            else:
                paper=order[0][0] if order else 'w'
            card.cell(cx,cy,paper,'k')
    # ink bitmap = dark outline pixels
    for py in range(card.H):
        for px in range(card.W):
            sx=px-inset; sy=py-inset
            if 0<=sx<iw and 0<=sy<ih:
                rr,gg,bb=sp[sx,sy]
                if (rr+gg+bb)/3 < darkthr: card.px(px,py)
    card.frame()
f2=Card(5,7); f2.fill_paper('w','k')
trace_woodcut(f2,"/Volumes/SSD1/code/scopa_spectrum/reference_cards/30_Dieci_di_spade.jpg")
f2.png("/tmp/re_spade_wood.png"); print("wrote /tmp/re_spade_wood.png")
# also the Cavallo (knight on horse, 9) and Fante (jack, 8) of a suit to see variety
f3=Card(5,7); f3.fill_paper('w','k')
trace_woodcut(f3,"/Volumes/SSD1/code/scopa_spectrum/reference_cards/29_Nove_di_spade.jpg")
f3.png("/tmp/cav_spade_wood.png"); print("wrote /tmp/cav_spade_wood.png")
