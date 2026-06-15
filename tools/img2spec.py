#!/usr/bin/env python3
"""High-quality image -> ZX Spectrum converter for card art.
Per 8x8 cell: choose the best (bright, paper, ink) pair minimising colour error,
then ordered-dither pixels between the two -> captures shading/detail faithfully."""
import math
from PIL import Image
PAL_BYBRIGHT={
 0:[(0,0,0),(0,0,205),(205,0,0),(205,0,205),(0,205,0),(0,205,205),(205,205,0),(205,205,205)],
 1:[(0,0,0),(0,0,255),(255,0,0),(255,0,255),(0,255,0),(0,255,255),(255,255,0),(255,255,255)],
}
INKCH='kbrmgcyw'
# Bayer 8x8 ordered-dither matrix, normalised to (0,1)
_B=[[0,32,8,40,2,34,10,42],[48,16,56,24,50,18,58,26],[12,44,4,36,14,46,6,38],
[60,28,52,20,62,30,54,22],[3,35,11,43,1,33,9,41],[51,19,59,27,49,17,57,25],
[15,47,7,39,13,45,5,37],[63,31,55,23,61,29,53,21]]
BAYER=[[(v+0.5)/64 for v in row] for row in _B]
def d2(a,b): return (a[0]-b[0])**2+(a[1]-b[1])**2+(a[2]-b[2])**2

class Conv:
    def __init__(s,cw,ch): s.cw,s.ch=cw,ch;s.W,s.H=cw*8,ch*8
    def convert(s,img):
        img=img.convert("RGB").resize((s.W,s.H),Image.LANCZOS); px=img.load()
        bmp=[[0]*s.W for _ in range(s.H)]; attr=[[0]*s.cw for _ in range(s.ch)]
        for cy in range(s.ch):
            for cx in range(s.cw):
                cell=[px[cx*8+x,cy*8+y] for y in range(8) for x in range(8)]
                best=None
                for br in (0,1):
                    pal=PAL_BYBRIGHT[br]
                    # quantise the cell's pixels to this palette, take present colours
                    present=sorted(set(min(range(8),key=lambda i:d2(p,pal[i])) for p in cell))
                    cand=present if len(present)>=2 else list(range(8))
                    for ii in range(len(cand)):
                        for jj in range(ii+1,len(cand)):
                            a,b=cand[ii],cand[jj]
                            err=sum(min(d2(p,pal[a]),d2(p,pal[b])) for p in cell)
                            if best is None or err<best[0]: best=(err,br,a,b)
                err,br,a,b=best; pal=PAL_BYBRIGHT[br]
                # paper = the colour MORE pixels are near (background); ink = other
                na=sum(1 for p in cell if d2(p,pal[a])<=d2(p,pal[b]))
                if na>=32: paper,ink=a,b
                else: paper,ink=b,a
                attr[cy][cx]=(br<<6)|(paper<<3)|ink
                cpaper,cink=pal[paper],pal[ink]
                for y in range(8):
                    for x in range(8):
                        p=cell[y*8+x]; da=d2(p,cpaper); db=d2(p,cink)
                        t=0.0 if da+db==0 else da/(da+db)   # 0=paper .. 1=ink
                        if t>BAYER[(cy*8+y)&7][(cx*8+x)&7]: bmp[cy*8+y][cx*8+x]=1
        return bmp,attr

def fit_white(jpg,W,H):
    im=Image.open(jpg).convert("RGB")
    if im.getbbox(): im=im.crop(im.getbbox())
    iw,ih=im.size; sc=min(W/iw,H/ih); nw,nh=int(iw*sc),int(ih*sc)
    im=im.resize((nw,nh),Image.LANCZOS)
    canvas=Image.new("RGB",(W,H),(255,255,255)); canvas.paste(im,((W-nw)//2,(H-nh)//2))
    return canvas

def preview_png(bmp,attr,cw,ch,path,scale=5):
    out=Image.new("RGB",(cw*8,ch*8)); o=out.load()
    for y in range(ch*8):
        for x in range(cw*8):
            at=attr[y//8][x//8]; br=(at>>6)&1; paper=(at>>3)&7; ink=at&7
            pal=PAL_BYBRIGHT[br]
            o[x,y]=pal[ink] if bmp[y][x] else pal[paper]
    out.resize((cw*8*scale,ch*8*scale),Image.NEAREST).save(path)

def blob(bmp,attr,cw,ch):
    out=bytearray()
    for y in range(ch*8):
        for cx in range(cw):
            v=0
            for bit in range(8):
                if bmp[y][cx*8+bit]: v|=0x80>>bit
            out.append(v)
    for cy in range(ch):
        for cx in range(cw): out.append(attr[cy][cx])
    return bytes(out)

if __name__=="__main__":
    REF="/Volumes/SSD1/code/scopa_spectrum/reference_cards/"
    CW,CH=8,12     # 64x96 card
    jobs=[("30_Dieci_di_spade.jpg","king"),("07_Sette_di_denari.jpg","sette"),
          ("29_Nove_di_spade.jpg","cav"),("11_Asso_di_coppe.jpg","acecup")]
    c=Conv(CW,CH); blobs=bytearray()
    from PIL import Image as I
    montage=[]
    for jpg,name in jobs:
        img=fit_white(REF+jpg,CW*8,CH*8)
        bmp,attr=c.convert(img)
        preview_png(bmp,attr,CW,CH,f"/tmp/q_{name}.png")
        blobs+=blob(bmp,attr,CW,CH); montage.append(f"/tmp/q_{name}.png")
        print("converted",name)
    open("q_cards.bin","wb").write(blobs)
    print("q_cards.bin",len(blobs),"bytes;",CW,"x",CH,"cells")
    ims=[I.open(p) for p in montage];w,h=ims[0].size;gap=18
    m=I.new("RGB",(w*len(ims)+gap*(len(ims)-1),h),(20,20,40))
    for i,im in enumerate(ims):m.paste(im,(i*(w+gap),0))
    m.save("/tmp/q_compare.png")
