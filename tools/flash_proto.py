#!/usr/bin/env python3
"""Prototype SOFTWARE card-flash / highlight styles (vs the current hardware FLASH bit 0xF8), as
animated GIFs + filmstrips. Renders the real crowned King-of-Coins on cyan felt and animates ONLY the
ATTRIBUTES over time -- exactly what a Z80 software flash would do (bitmap untouched). No game code is
touched. Outputs to flash_proto/. RUN FROM scopa/."""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DECK = os.path.join(HERE, "..", "deck.bin")
OUT  = os.path.join(HERE, "..", "flash_proto")
os.makedirs(OUT, exist_ok=True)

PAL  = [(0,0,0),(0,0,205),(205,0,0),(205,0,205),(0,205,0),(0,205,205),(205,205,0),(205,205,205)]
PALB = [(0,0,0),(0,0,255),(255,0,0),(255,0,255),(0,255,0),(0,255,255),(255,255,0),(255,255,255)]

def ink_paper(a):
    p = PALB if (a>>6)&1 else PAL
    return p[a&7], p[(a>>3)&7]

deck = open(DECK,"rb").read()
CARD = 9; CBASE = CARD*384                 # crowned King of Coins
def card_bit(px,py): return (deck[CBASE+py*6+(px>>3)] >> (7-(px&7))) & 1

COLS,ROWS = 12,12
CX,CY = 3,2                                # card top-left cell (card is 6x8 cells)
SCALE = 5
FELT  = 0x28                               # board: non-bright cyan paper, black ink
CARDA = 0x78                               # card: bright white paper, black ink
GOLD  = 0x70                               # bright yellow paper
CYANP = 0x68                               # bright cyan paper
INVRT = 0x47                               # bright, black paper, white ink (the hardware-FLASH look)

def is_card(cx,cy): return CX<=cx<CX+6 and CY<=cy<CY+8
def in_ring(cx,cy):                        # 1-cell halo just outside the card (cols 2..9, rows 1..10)
    if CX-1<=cx<=CX+6 and CY-1<=cy<=CY+8:
        return not (CX<=cx<CX+6 and CY<=cy<CY+8)
    return False

def render(attr_of):
    W,H = COLS*8, ROWS*8
    im = Image.new("RGB",(W,H)); px=im.load()
    for cy in range(ROWS):
        for cx in range(COLS):
            ink,paper = ink_paper(attr_of(cx,cy))
            for yy in range(8):
                for xx in range(8):
                    if is_card(cx,cy) and card_bit((cx-CX)*8+xx,(cy-CY)*8+yy):
                        px[cx*8+xx,cy*8+yy]=ink
                    else:
                        px[cx*8+xx,cy*8+yy]=paper
    return im.resize((W*SCALE,H*SCALE),Image.NEAREST)

def base(cx,cy): return CARDA if is_card(cx,cy) else FELT
def pulse(t,n,duty=0.5): return ((t*n)%1.0) < duty

# ---- the styles: each is f(t)->attr_of(cx,cy), t in [0,1) ----
def gold_glow(t):
    on=pulse(t,3)
    return lambda cx,cy: (GOLD if on else CARDA) if is_card(cx,cy) else FELT
def cyan_glow(t):
    on=pulse(t,3)
    return lambda cx,cy: (CYANP if on else CARDA) if is_card(cx,cy) else FELT
def bright_pulse(t):
    on=pulse(t,4)
    return lambda cx,cy: (0x38 if on else CARDA) if is_card(cx,cy) else FELT     # bright off<->on
def invert_blink(t):
    on=pulse(t,3,0.4)
    return lambda cx,cy: (INVRT if on else CARDA) if is_card(cx,cy) else FELT
def gold_frame(t):
    on=pulse(t,3)
    return lambda cx,cy: (GOLD if (on and in_ring(cx,cy)) else base(cx,cy))
def white_frame(t):
    on=pulse(t,3)
    return lambda cx,cy: (0x78 if (on and in_ring(cx,cy)) else base(cx,cy))      # bright white halo
def sweep(t):
    band = CY-1 + (t*1.5%1.0)*(8+2)        # glint travels top->below, ~1.5 passes/loop
    def f(cx,cy):
        if is_card(cx,cy) and abs(cy-band)<1.0: return GOLD
        return base(cx,cy)
    return f
def regal(t):                              # gold halo + gold card-wash together (max classy)
    on=pulse(t,3)
    def f(cx,cy):
        if in_ring(cx,cy): return GOLD if on else FELT
        if is_card(cx,cy): return GOLD if on else CARDA
        return FELT
    return f

STYLES = [("gold_glow",gold_glow),("cyan_glow",cyan_glow),("bright_pulse",bright_pulse),
          ("invert_blink",invert_blink),("gold_frame",gold_frame),("white_frame",white_frame),
          ("sweep",sweep),("regal",regal)]
N=30
lit_frames=[]
for name,fn in STYLES:
    frames=[render(fn(i/N)) for i in range(N)]
    frames[0].save(f"{OUT}/flash_{name}.gif",save_all=True,append_images=frames[1:],
                   duration=70,loop=0,disposal=2)
    # filmstrip: 6 frames at half scale (for a quick static look)
    small=[f.resize((COLS*8*2,ROWS*8*2),Image.NEAREST) for f in frames]
    strip=Image.new("RGB",(small[0].width*6+5*8, small[0].height),(15,15,15))
    for k in range(6): strip.paste(small[k*N//6],(k*(small[0].width+8),0))
    strip.save(f"{OUT}/strip_{name}.png")
    lit_frames.append((name,frames[N//4]))   # a representative "lit" frame for the contact sheet

# reference (normal) + hardware-FLASH look (full invert) for comparison
render(lambda cx,cy:base(cx,cy)).save(f"{OUT}/_normal.png")
render(lambda cx,cy:(INVRT if is_card(cx,cy) else FELT)).save(f"{OUT}/_hardware_invert.png")

# contact sheet: a lit frame of every style, labelled, 4 across
from PIL import ImageDraw
cw,ch=lit_frames[0][1].width,lit_frames[0][1].height
cols=4; rows=(len(lit_frames)+cols-1)//cols
sheet=Image.new("RGB",(cols*cw+(cols+1)*8, rows*(ch+18)+8),(20,20,20)); d=ImageDraw.Draw(sheet)
for i,(name,fr) in enumerate(lit_frames):
    r,c=divmod(i,cols); x=8+c*(cw+8); y=8+r*(ch+18)
    sheet.paste(fr,(x,y)); d.text((x+2,y+ch+3),name,fill=(230,230,230))
sheet.save(f"{OUT}/_contact.png")
print(f"wrote {len(STYLES)} GIFs + filmstrips + _contact.png + _normal/_hardware_invert to {os.path.realpath(OUT)}")
