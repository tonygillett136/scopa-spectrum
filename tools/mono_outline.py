#!/usr/bin/env python3
"""Monochrome card art the proper 8-bit way: SOLID black outlines (kept crisp) +
ordered-dither ONLY for interior shading. White paper, black ink -> zero clash."""
import math
from PIL import Image, ImageFilter
_B=[[0,32,8,40,2,34,10,42],[48,16,56,24,50,18,58,26],[12,44,4,36,14,46,6,38],
[60,28,52,20,62,30,54,22],[3,35,11,43,1,33,9,41],[51,19,59,27,49,17,57,25],
[15,47,7,39,13,45,5,37],[63,31,55,23,61,29,53,21]]
BAYER=[[(v+0.5)/64 for v in row] for row in _B]

def fit(jpg,W,H,margin):
    im=Image.open(jpg).convert("L")
    bb=im.getbbox()
    if bb: im=im.crop(bb)
    iw,ih=im.size; aw,ah=W-2*margin,H-2*margin
    sc=min(aw/iw,ah/ih); nw,nh=int(iw*sc),int(ih*sc)
    im=im.resize((nw,nh),Image.LANCZOS)
    canvas=Image.new("L",(W,H),255); canvas.paste(im,((W-nw)//2,(H-nh)//2))
    return canvas

def convert(jpg,cw,ch,margin=6,outline=95,blur=0.5,gamma=1.0):
    W,H=cw*8,ch*8
    g=fit(jpg,W,H,margin)
    edges=g.filter(ImageFilter.FIND_EDGES)            # gradient edges
    sm=g.filter(ImageFilter.GaussianBlur(blur))
    lp=sm.load(); ep=edges.load()
    bmp=[[0]*W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            lum=lp[x,y]; edge=ep[x,y]
            if lum<outline or edge>110:                # solid outline (dark linework or strong edge)
                bmp[y][x]=1
            else:                                       # interior: dither by darkness
                t=((255-lum)/255.0)**gamma
                if t>BAYER[y&7][x&7]: bmp[y][x]=1
    # frame (rounded)
    for x in range(W): bmp[0][x]=1;bmp[H-1][x]=1
    for y in range(H): bmp[y][0]=1;bmp[y][W-1]=1
    for x,yv in[(0,0),(1,0),(0,1),(W-1,0),(W-2,0),(W-1,1),(0,H-1),(1,H-1),(0,H-2),(W-1,H-1),(W-2,H-1),(W-1,H-2)]:
        bmp[yv][x]=0
    return bmp
def png(bmp,W,H,path,scale=5):
    im=Image.new("L",(W,H))
    p=im.load()
    for y in range(H):
        for x in range(W): p[x,y]=0 if bmp[y][x] else 255
    im.resize((W*scale,H*scale),Image.NEAREST).save(path)
def blob(bmp,cw,ch):
    out=bytearray()
    for y in range(ch*8):
        for cx in range(cw):
            v=0
            for bit in range(8):
                if bmp[y][cx*8+bit]: v|=0x80>>bit
            out.append(v)
    for _ in range(cw*ch): out.append(0x78)   # all cells: white paper, black ink, bright
    return bytes(out)

if __name__=="__main__":
    REF="/Volumes/SSD1/code/scopa_spectrum/reference_cards/"
    CW,CH=8,12
    jobs=[("30_Dieci_di_spade.jpg","king"),("07_Sette_di_denari.jpg","sette"),
          ("23_Tre_di_spade.jpg","tre_sw"),("11_Asso_di_coppe.jpg","acecup")]
    blobs=bytearray(); names=[]
    for jpg,name in jobs:
        b=convert(REF+jpg,CW,CH)
        png(b,CW*8,CH*8,f"/tmp/m_{name}.png"); blobs+=blob(b,CW,CH); names.append(f"/tmp/m_{name}.png")
        print("mono",name)
    open("m_cards.bin","wb").write(blobs)
    ims=[Image.open(p) for p in names];w,h=ims[0].size;g=18
    m=Image.new("RGB",(w*4+g*3,h),(60,60,60))
    for i,im in enumerate(ims):m.paste(im.convert("RGB"),(i*(w+g),0))
    m.save("/tmp/m_compare.png")
