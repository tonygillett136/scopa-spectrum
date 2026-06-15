#!/usr/bin/env python3
"""Convert all 40 Napoletane cards to defined-monochrome 48x64 (6x8 cells).
Card id 0..39: id=(filenum-1); value=id%10+1; suit=id//10 (0 denari,1 coppe,2 spade,3 bastoni).
deck.bin = 40 cards x 384 bitmap bytes (attrs are constant 0x78, set by the engine)."""
import sys, os, glob
sys.path.insert(0,os.path.dirname(__file__))
from PIL import Image, ImageFilter, ImageOps
import mono_outline as M
CW,CH=6,8

def _tighten(im,thr=215):
    g=ImageOps.grayscale(im); bb=ImageOps.invert(g.point(lambda p:0 if p<thr else 255)).getbbox()
    return im.crop(bb) if bb else im

def cup_badge(src_jpg, bw=12, bh=15, hires=5, silthr=185, margin=1):
    """Trace the two-handled coppe goblet's OUTLINE from the reference 2-of-coppe and
    render it as a small line-art suit pip. Stamped on the coppe figure cards so the
    suit reads clearly (the figures themselves don't show an obvious cup)."""
    im=Image.open(src_jpg).convert('RGB'); W,H=im.size
    src=_tighten(im.crop((0,int(.02*H),W,int(.46*H))))           # top goblet of the card
    g=ImageOps.grayscale(src); aw,ah=(bw-2*margin)*hires,(bh-2*margin)*hires
    iw,ih=g.size; sc=min(aw/iw,ah/ih); gh=g.resize((int(iw*sc),int(ih*sc)),Image.LANCZOS); nw,nh=gh.size
    sil=[[1 if gh.getpixel((x,y))<silthr else 0 for x in range(nw)] for y in range(nh)]
    cont=Image.new('L',(nw,nh),0); cp=cont.load()                # boundary of the silhouette = hollow outline
    for y in range(nh):
        for x in range(nw):
            if sil[y][x] and (x==0 or x==nw-1 or y==0 or y==nh-1 or not(sil[y-1][x] and sil[y+1][x] and sil[y][x-1] and sil[y][x+1])): cp[x,y]=255
    cont=cont.filter(ImageFilter.MaxFilter(3))
    inner=cont.resize((bw-2*margin,bh-2*margin),Image.LANCZOS).point(lambda p:1 if p>85 else 0); ip=inner.load()
    bits=[[0]*bw for _ in range(bh)]
    for y in range(bh-2*margin):
        for x in range(bw-2*margin): bits[y+margin][x+margin]=ip[x,y]
    return bits

def stamp_badge(b, bits, bx=2, by=2):
    """Stamp a suit pip into the top-left corner with a 1px white moat. Placed at (2,2)
    so the moat never touches the card frame (row/col 0)."""
    bh=len(bits); bw=len(bits[0])
    for y in range(by-1,by+bh+1):
        for x in range(bx-1,bx+bw+1):
            if 0<=x<CW*8 and 0<=y<CH*8: b[y][x]=0               # clear moat to white
    for y in range(bh):
        for x in range(bw):
            if bits[y][x] and 0<=bx+x<CW*8 and 0<=by+y<CH*8: b[by+y][bx+x]=1
    return b
def dm(jpg,margin=4,darkthr=42,edgethr=82,blur=0.6,gamma=1.5):
    W,H=CW*8,CH*8; g=M.fit(jpg,W,H,margin)
    e=g.filter(ImageFilter.FIND_EDGES); s=g.filter(ImageFilter.GaussianBlur(blur))
    lp=s.load(); ep=e.load(); b=[[0]*W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if lp[x,y]<darkthr or ep[x,y]>edgethr: b[y][x]=1
            else:
                t=((255-lp[x,y])/255.0)**gamma
                if t>M.BAYER[y&7][x&7]: b[y][x]=1
    for x in range(W): b[0][x]=1;b[H-1][x]=1
    for y in range(H): b[y][0]=1;b[y][W-1]=1
    for x,yv in[(0,0),(1,0),(0,1),(W-1,0),(W-2,0),(W-1,1),(0,H-1),(1,H-1),(0,H-2),(W-1,H-1),(W-2,H-1),(W-1,H-2)]: b[yv][x]=0
    return b
def bmpblob(b):
    out=bytearray()
    for y in range(CH*8):
        for cx in range(CW):
            v=0
            for bit in range(8):
                if b[y][cx*8+bit]: v|=0x80>>bit
            out.append(v)
    return bytes(out)
REF="/Volumes/SSD1/code/scopa_spectrum/reference_cards/"
files=sorted(glob.glob(REF+"*.jpg"))
assert len(files)==40, len(files)
CUP_BITS=cup_badge(files[11])   # source goblet = "12_Due_di_coppe.jpg"
deck=bytearray(); imgs=[]
for i,f in enumerate(files):
    value=(i%10)+1; suit=i//10
    b=dm(f,darkthr=58,gamma=2.4) if value>=8 else dm(f)   # lighter for dense figures
    if suit==1 and value>=8:        # coppe figures (Fante/Cavallo/Re): add cup suit pip
        stamp_badge(b,CUP_BITS)
    deck+=bmpblob(b)
    M.png(b,CW*8,CH*8,f"/tmp/deck_{i:02d}.png",scale=4); imgs.append(f"/tmp/deck_{i:02d}.png")
# card back: lattice pattern + border
bk=[[0]*(CW*8) for _ in range(CH*8)]
for y in range(CH*8):
    for x in range(CW*8):
        if (x+y)%4==0 or (x-y)%4==0: bk[y][x]=1
for x in range(CW*8): bk[0][x]=1;bk[CH*8-1][x]=1
for y in range(CH*8): bk[y][0]=1;bk[y][CW*8-1]=1
for yy in range(2,CH*8-2):
    for xx in range(2,CW*8-2): pass
deck+=bmpblob(bk)
open("deck.bin","wb").write(deck)
print("deck.bin",len(deck),"bytes (40 cards + 1 back, 384B each)")
# montage 8 cols x 5 rows
cols=8; rows=5; w,h=Image.open(imgs[0]).size; gap=6
m=Image.new("RGB",(cols*(w+gap)+gap,rows*(h+gap)+gap),(0,160,160))
for i,p in enumerate(imgs):
    r,c=divmod(i,cols); m.paste(Image.open(p).convert("RGB"),(gap+c*(w+gap),gap+r*(h+gap)))
m.save("/tmp/deck_all.png"); print("montage /tmp/deck_all.png")
