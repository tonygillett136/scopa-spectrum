#!/usr/bin/env python3
"""Convert all 40 Napoletane cards to defined-monochrome 48x64 (6x8 cells).
Card id 0..39: id=(filenum-1); value=id%10+1; suit=id//10 (0 denari,1 coppe,2 spade,3 bastoni).
deck.bin = 40 cards x 384 bitmap bytes (attrs are constant 0x78, set by the engine)."""
import sys, os, glob, math
sys.path.insert(0,os.path.dirname(__file__))
from PIL import Image, ImageFilter, ImageOps, ImageDraw
import mono_outline as M
CW,CH=6,8

# --- denari figure coins -------------------------------------------------
# The three denari figures (Fante/Cavallo/Re) hold (or, for the Re, stand
# beside) a suit coin that - placed faithfully - renders only ~7px across and
# mushes in the dither. We enlarge it x1.5 and redraw it as a clean ROUND
# checker medallion (clean outline + centre boss + 1px white gap to the figure)
# so the denari suit reads at a glance. Coords are source pixels in the
# reference photos. dx/dy relocate the Cavallo coin up-and-out (its reference
# pose holds it crowded against the head), matching the traditional composition.
# key = file index (i): 7=Fante(08), 8=Cavallo(09), 9=Re(10).
COIN={7:(397,362,137,1.5,0,0), 8:(447,217,117,1.5,-82,-32), 9:(1035,400,137,1.5,0,0)}

def place_coin(im,cx,cy,r,S,dx,dy):
    """Relocate/enlarge the coin disc in the SOURCE photo (only when moving it,
    i.e. the Cavallo); the medallion overlay handles the in-place coins."""
    if dx==0 and dy==0: return im
    hs=int(r*1.18); crop=im.crop((cx-hs,cy-hs,cx+hs,cy+hs))
    ns=int(2*hs*S); big=crop.resize((ns,ns),Image.LANCZOS)
    ImageDraw.Draw(im).ellipse((cx-r-6,cy-r-6,cx+r+6,cy+r+6),fill=(255,255,255))  # erase old
    mask=Image.new('L',(ns,ns),0); c=ns/2
    ImageDraw.Draw(mask).ellipse((c-r*S,c-r*S,c+r*S,c+r*S),fill=255)
    im.paste(big,(int(cx+dx-c),int(cy+dy-c)),mask); return im

def medallion(b,cx,cy,r):
    """Draw a clean round checker-medallion coin onto the final bitmap:
    outline circle, checker interior + centre boss, and a 1px white gap."""
    W,H=CW*8,CH*8
    for y in range(max(1,int(cy-r-3)),min(H-1,int(cy+r+4))):
        for x in range(max(1,int(cx-r-3)),min(W-1,int(cx+r+4))):
            d=math.hypot(x-cx,y-cy)
            if d<=r-0.7:    b[y][x]=1 if (d<=1.15 or M.BAYER[y&7][x&7]<0.5) else 0
            elif d<=r+0.45: b[y][x]=1                       # clean round outline
            elif d<=r+1.5:  b[y][x]=0                       # 1px white gap to figure

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
def _fit(src,W,H,margin):
    """Like mono_outline.fit but accepts a path OR a PIL image, and also returns
    the source->canvas transform (scale + paste offset + bbox-crop origin) so the
    coin medallion can be positioned exactly."""
    im=src if hasattr(src,"convert") else Image.open(src)
    im=im.convert("L"); bb=im.getbbox(); bx,by=(bb[0],bb[1]) if bb else (0,0)
    if bb: im=im.crop(bb)
    iw,ih=im.size; aw,ah=W-2*margin,H-2*margin
    sc=min(aw/iw,ah/ih); nw,nh=int(iw*sc),int(ih*sc)
    im=im.resize((nw,nh),Image.LANCZOS); ox,oy=(W-nw)//2,(H-nh)//2
    canvas=Image.new("L",(W,H),255); canvas.paste(im,(ox,oy))
    return canvas,sc,ox,oy,bx,by

def dm(src,margin=4,darkthr=42,edgethr=82,blur=0.6,gamma=1.5,ret_fit=False):
    W,H=CW*8,CH*8; g,sc,ox,oy,bx,by=_fit(src,W,H,margin)
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
    return (b,sc,ox,oy,bx,by) if ret_fit else b
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
    if i in COIN:                   # denari figures: enlarge/relocate coin + medallion
        cx,cy,r,S,dx,dy=COIN[i]
        src=place_coin(Image.open(f).convert('RGB'),cx,cy,r,S,dx,dy)
        b,sc,ox,oy,bx,by=dm(src,darkthr=58,gamma=2.4,ret_fit=True)
        medallion(b, ox+(cx+dx-bx)*sc, oy+(cy+dy-by)*sc, r*S*sc)
    elif value>=8:
        b=dm(f,darkthr=58,gamma=2.4)         # lighter for dense figures
        if suit==1: stamp_badge(b,CUP_BITS)  # coppe figures: add cup suit pip
    else:
        b=dm(f)
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
