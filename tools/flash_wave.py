#!/usr/bin/env python3
"""Refine the CHOSEN card-flash looks as GIFs (no game code touched):
  cursor_glow   -- the selected card's field pulses white<->gold (sustained highlight)
  capture_wave  -- a gold glint sweeps DOWN each captured card, each card a few frames DELAYED so the
                   gold ripples left->right across the row (Tony's staggered wave).
Attributes only -- exactly what a Z80 software flash would do. RUN FROM scopa/. Output -> flash_proto/."""
import os, math
from PIL import Image
HERE=os.path.dirname(os.path.abspath(__file__))
DECK=os.path.join(HERE,"..","deck.bin"); OUT=os.path.join(HERE,"..","flash_proto")
os.makedirs(OUT,exist_ok=True)
PAL =[(0,0,0),(0,0,205),(205,0,0),(205,0,205),(0,205,0),(0,205,205),(205,205,0),(205,205,205)]
PALB=[(0,0,0),(0,0,255),(255,0,0),(255,0,255),(0,255,0),(0,255,255),(255,255,0),(255,255,255)]
def ink_paper(a):
    p=PALB if (a>>6)&1 else PAL; return p[a&7],p[(a>>3)&7]
deck=open(DECK,"rb").read()
def bit(cid,px,py): return (deck[cid*384+py*6+(px>>3)]>>(7-(px&7)))&1
FELT=0x28; WHITE=0x78; GOLD=0x70

def render(cards, attr_of, COLS, ROWS, scale):
    def card_at(cx,cy):
        for (c,r,cid) in cards:
            if c<=cx<c+6 and r<=cy<r+8: return (cid,cx-c,cy-r)
        return None
    W,H=COLS*8,ROWS*8; im=Image.new("RGB",(W,H)); px=im.load()
    for cy in range(ROWS):
        for cx in range(COLS):
            ink,paper=ink_paper(attr_of(cx,cy)); ca=card_at(cx,cy)
            for yy in range(8):
                for xx in range(8):
                    px[cx*8+xx,cy*8+yy] = ink if (ca and bit(ca[0],ca[1]*8+xx,ca[2]*8+yy)) else paper
    return im.resize((W*scale,H*scale),Image.NEAREST)

def save(name,frames,dur):
    frames[0].save(f"{OUT}/{name}.gif",save_all=True,append_images=frames[1:],duration=dur,loop=0,disposal=2)
    sm=[f.resize((f.width//2,f.height//2),Image.NEAREST) for f in frames]; n=len(frames)
    idx=[round(i*(n-1)/5) for i in range(6)]
    strip=Image.new("RGB",(sm[0].width*6+40,sm[0].height),(15,15,15))
    for k,fi in enumerate(idx): strip.paste(sm[fi],(k*(sm[0].width+8),0))
    strip.save(f"{OUT}/strip_{name}.png")

# ---- cursor_glow: one card, paper white<->gold, sustained gentle pulse (2 cycles/loop) ----
COLS,ROWS=10,12; CUR=(2,2,9)
def in_cur(cx,cy): return CUR[0]<=cx<CUR[0]+6 and CUR[1]<=cy<CUR[1]+8
N=32; gf=[]
for i in range(N):
    on=(0.5+0.5*math.sin(i/N*2*math.pi*2 - math.pi/2))>0.5
    gf.append(render([CUR], (lambda cx,cy,on=on:(GOLD if on else WHITE) if in_cur(cx,cy) else FELT), COLS,ROWS,6))
save("cursor_glow",gf,80)

# ---- capture_wave: 4 captured table cards, gold glint sweeps down each, staggered left->right ----
COLS2,ROWS2=30,12
CARDS=[(1,2,6),(8,2,0),(15,2,9),(22,2,18)]   # 7-coins, ace-coins, king-coins, knight-cups; table step 7
SWEEP=12; STAG=4; PAUSE=12                    # STAG = the "bit out of sync" per-card delay
TOTAL=(len(CARDS)-1)*STAG+SWEEP+PAUSE
def owner(cx):
    for k,(c,r,cid) in enumerate(CARDS):
        if c<=cx<c+6: return k
    return None
wf=[]
for f in range(TOTAL):
    def af(cx,cy,f=f):
        k=owner(cx)
        if k is None or not (2<=cy<10): return FELT
        local=f-k*STAG
        if 0<=local<SWEEP and abs(cy-(2+local/SWEEP*8))<1.0: return GOLD
        return WHITE
    wf.append(render(CARDS,af,COLS2,ROWS2,4))
save("capture_wave",wf,70)
print("wrote cursor_glow.gif + capture_wave.gif (+ filmstrips) to",os.path.realpath(OUT))
