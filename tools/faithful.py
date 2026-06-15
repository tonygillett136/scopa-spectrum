#!/usr/bin/env python3
"""FAITHFUL mono trace: keep the reference card's OWN black linework as clean
outlines; add only LIGHT interior dither for the coloured fills so it stays true
to the source and never becomes a dark blob."""
from PIL import Image, ImageFilter
_B=[[0,32,8,40,2,34,10,42],[48,16,56,24,50,18,58,26],[12,44,4,36,14,46,6,38],
[60,28,52,20,62,30,54,22],[3,35,11,43,1,33,9,41],[51,19,59,27,49,17,57,25],
[15,47,7,39,13,45,5,37],[63,31,55,23,61,29,53,21]]
BAYER=[[(v+0.5)/64 for v in r] for r in _B]
def fit(jpg,W,H,margin):
    im=Image.open(jpg).convert("L")
    bb=im.getbbox()
    if bb: im=im.crop(bb)
    iw,ih=im.size; aw,ah=W-2*margin,H-2*margin
    sc=min(aw/iw,ah/ih); nw,nh=int(iw*sc),int(ih*sc)
    im=im.resize((nw,nh),Image.LANCZOS)
    c=Image.new("L",(W,H),255); c.paste(im,((W-nw)//2,(H-nh)//2)); return c
def trace(jpg,cw,ch,margin=5,linethr=70,blur=0.4,fillmax=0.55,gamma=1.15):
    W,H=cw*8,ch*8
    g=fit(jpg,W,H,margin)
    sm=g.filter(ImageFilter.GaussianBlur(blur)); lp=sm.load()
    bmp=[[0]*W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            lum=lp[x,y]
            if lum<linethr:                 # the card's OWN black lines -> solid outline
                bmp[y][x]=1
            else:                           # fills: LIGHT dither, capped so never solid
                t=(((255-lum)/(255-linethr))**gamma)*fillmax
                if t>BAYER[y&7][x&7]: bmp[y][x]=1
    for x in range(W): bmp[0][x]=1;bmp[H-1][x]=1
    for y in range(H): bmp[y][0]=1;bmp[y][W-1]=1
    for x,yv in[(0,0),(1,0),(0,1),(W-1,0),(W-2,0),(W-1,1),(0,H-1),(1,H-1),(0,H-2),(W-1,H-1),(W-2,H-1),(W-1,H-2)]: bmp[yv][x]=0
    return bmp,W,H
def png(bmp,W,H,path,scale=5):
    im=Image.new("L",(W,H)); p=im.load()
    for y in range(H):
        for x in range(W): p[x,y]=0 if bmp[y][x] else 255
    im.resize((W*scale,H*scale),Image.NEAREST).save(path); return im.resize((W*scale,H*scale),Image.NEAREST)
