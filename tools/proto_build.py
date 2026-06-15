#!/usr/bin/env python3
"""Build the 4 prototype cards, export a Spectrum data blob + montage PNG.
Card = 5x7 cells (40x56). Blob per card: 56*5 bitmap bytes + 7*5 attr bytes."""
import math
from PIL import Image
from collections import Counter
PAL={('k',0):(0,0,0),('k',1):(0,0,0),('b',0):(0,0,192),('b',1):(0,0,238),
('r',0):(192,0,0),('r',1):(255,0,0),('m',0):(192,0,192),('m',1):(255,0,255),
('g',0):(0,192,0),('g',1):(0,238,0),('c',0):(0,192,192),('c',1):(0,255,255),
('y',0):(192,192,0),('y',1):(255,255,0),('w',0):(192,192,192),('w',1):(255,255,255)}
INK={'k':0,'b':1,'r':2,'m':3,'g':4,'c':5,'y':6,'w':7}
class Card:
    def __init__(s,cw=5,ch=7):
        s.cw,s.ch=cw,ch;s.W,s.H=cw*8,ch*8
        s.bmp=[[0]*s.W for _ in range(s.H)]
        s.attr=[[('w','k',1) for _ in range(cw)] for _ in range(ch)]
    def px(s,x,y,v=1):
        if 0<=x<s.W and 0<=y<s.H:s.bmp[y][x]=v
    def cell(s,cx,cy,p,i,b=1):
        if 0<=cx<s.cw and 0<=cy<s.ch:s.attr[cy][cx]=(p,i,b)
    def fill(s,p,i='k',b=1):
        for cy in range(s.ch):
            for cx in range(s.cw):s.attr[cy][cx]=(p,i,b)
    def dither(s,x0,y0,x1,y1,phase=0):     # checkerboard ink (for shades)
        for y in range(y0,y1):
            for x in range(x0,x1):
                if (x+y)&1==phase: s.px(x,y)
    def frame(s):
        for x in range(s.W):s.px(x,0);s.px(x,s.H-1)
        for y in range(s.H):s.px(0,y);s.px(s.W-1,y)
        for x,y in[(0,0),(s.W-1,0),(0,s.H-1),(s.W-1,s.H-1)]:s.bmp[y][x]=0
    def png(s,path,scale=6):
        im=Image.new("RGB",(s.W,s.H));p=im.load()
        for y in range(s.H):
            for x in range(s.W):
                pa,ik,br=s.attr[y//8][x//8]
                p[x,y]=PAL[(ik,br)] if s.bmp[y][x] else PAL[(pa,br)]
        im.resize((s.W*scale,s.H*scale),Image.NEAREST).save(path)
    def blob(s):
        out=bytearray()
        for y in range(s.H):
            for cx in range(s.cw):
                b=0
                for bit in range(8):
                    if s.bmp[y][cx*8+bit]:b|=0x80>>bit
                out.append(b)
        for cy in range(s.ch):
            for cx in range(s.cw):
                pa,ik,br=s.attr[cy][cx]
                out.append((0x40 if br else 0)|(INK[pa]<<3)|INK[ik])
        return bytes(out)

def goldcoin(c,cx,cy):           # gold tile + black sun engraving
    c.cell(cx,cy,'y','k');ox,oy=cx*8,cy*8
    for py in range(8):
        for px in range(8):
            dx=px-3.5;dy=py-3.5;r=math.hypot(dx,dy);a=math.atan2(dy,dx)
            spike=1.7+1.9*max(0,math.cos(8*a))
            if r<=3.4 and not(r<=spike): c.px(ox+px,oy+py)
def bigcoin(c,cx,cy,n):
    for dy in range(n):
        for dx in range(n):c.cell(cx+dx,cy+dy,'y','k')
    N=n*8;ox,oy=cx*8,cy*8;cc=(N-1)/2
    for py in range(N):
        for px in range(N):
            dx=px-cc;dy=py-cc;r=math.hypot(dx,dy);a=math.atan2(dy,dx)
            spike=cc*0.55+cc*0.42*max(0,math.cos(8*a))
            if (cc*0.9<r<=cc*0.99) or (r<=spike and r>cc*0.16): c.px(ox+px,oy+py)
def cup(c,cx,cy):
    c.cell(cx,cy,'w','r');ox,oy=cx*8,cy*8
    g=[".######.","########",".######.","..####..","...##...","..####..",".######.","........"]
    for py,row in enumerate(g):
        for px,ch in enumerate(row):
            if ch=='#':c.px(ox+px,oy+py)
def woodcut(c,jpg,darkthr=80,sat=55,need=28,inset=1):
    src=Image.open(jpg).convert("RGB")
    if src.getbbox():src=src.crop(src.getbbox())
    iw,ih=c.W-2*inset,c.H-2*inset;src=src.resize((iw,ih),Image.LANCZOS);sp=src.load()
    def cl(rr,gg,bb):
        if max(rr,gg,bb)-min(rr,gg,bb)<sat:return None
        if rr>=gg and rr>=bb:return 'y' if gg>140 else 'r'
        if bb>=rr and bb>=gg:return 'b'
        return 'g'
    for cy in range(c.ch):
        for cx in range(c.cw):
            cnt=Counter()
            for py in range(8):
                for px in range(8):
                    sx=cx*8+px-inset;sy=cy*8+py-inset
                    if 0<=sx<iw and 0<=sy<ih:
                        k=cl(*sp[sx,sy])
                        if k:cnt[k]+=1
            paper='w'
            if cnt:
                k,nn=cnt.most_common(1)[0]
                if nn>=need:paper=k
            c.cell(cx,cy,paper,'k')
    for py in range(c.H):
        for px in range(c.W):
            sx=px-inset;sy=py-inset
            if 0<=sx<iw and 0<=sy<ih and sum(sp[sx,sy])/3<darkthr:c.px(px,py)
    c.frame()

REF="/Volumes/SSD1/code/scopa_spectrum/reference_cards/"
# settebello
sb=Card();sb.fill('w','k');sb.frame()
for cx,cy in [(1,1),(3,1),(2,2),(1,3),(3,3),(1,4),(3,4)]:goldcoin(sb,cx,cy)
# ace
ac=Card();ac.fill('w','k');ac.frame();bigcoin(ac,1,2,3)
# 3 cups
cp=Card();cp.fill('w','k');cp.frame()
for cx,cy in [(1,1),(3,1),(2,4)]:cup(cp,cx,cy)
# king of swords (woodcut)
ks=Card();ks.fill('w','k');woodcut(ks,REF+"30_Dieci_di_spade.jpg")
cards=[sb,ac,cp,ks]
blob=bytearray()
for c in cards: blob+=c.blob()
open("proto_cards.bin","wb").write(blob)
print("proto_cards.bin",len(blob),"bytes (4 cards x 315)")
# montage
for i,c in enumerate(cards): c.png(f"/tmp/pc{i}.png")
ims=[Image.open(f"/tmp/pc{i}.png") for i in range(4)];w,h=ims[0].size;gap=18
m=Image.new("RGB",(w*4+gap*3,h),(0,90,40))
for i,im in enumerate(ims):m.paste(im,(i*(w+gap),0))
m.save("/tmp/proto_final.png");print("montage /tmp/proto_final.png")
