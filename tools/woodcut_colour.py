#!/usr/bin/env python3
"""FAITHFUL colour woodcut: per cell, paper = the region's flat colour, ink = black,
bitmap = the reference's own black OUTLINES. Reproduces the woodcut look (flat bright
colour + crisp black linework) with no attribute clash."""
from PIL import Image, ImageFilter
from collections import Counter
PAL={  # idx -> (bright,inkindex,rgb)
 ('k',0):(0,0,0),('k',1):(0,0,0),('b',0):(0,0,180),('b',1):(40,40,255),
 ('r',0):(180,0,0),('r',1):(255,40,40),('m',0):(180,0,180),('m',1):(255,60,255),
 ('g',0):(0,160,0),('g',1):(40,255,40),('c',0):(0,170,170),('c',1):(60,255,255),
 ('y',0):(190,170,0),('y',1):(255,255,60),('w',0):(190,190,190),('w',1):(255,255,255)}
IDX={'k':0,'b':1,'r':2,'m':3,'g':4,'c':5,'y':6,'w':7}
def d2(a,b): return (a[0]-b[0])**2+(a[1]-b[1])**2+(a[2]-b[2])**2
def fit(jpg,W,H,margin):
    im=Image.open(jpg).convert("RGB")
    bb=im.getbbox()
    if bb: im=im.crop(bb)
    iw,ih=im.size; aw,ah=W-2*margin,H-2*margin
    sc=min(aw/iw,ah/ih); nw,nh=int(iw*sc),int(ih*sc)
    im=im.resize((nw,nh),Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.5))
    c=Image.new("RGB",(W,H),(255,255,255)); c.paste(im,((W-nw)//2,(H-nh)//2)); return c
def lum(p): return 0.3*p[0]+0.59*p[1]+0.11*p[2]
def woodcut(jpg,cw,ch,margin=5,linethr=68):
    W,H=cw*8,ch*8; src=fit(jpg,W,H,margin); px=src.load()
    bmp=[[0]*W for _ in range(H)]; attr=[[0]*cw for _ in range(ch)]
    keys=list(PAL.keys())
    for cy in range(ch):
        for cx in range(cw):
            cnt=Counter()
            for y in range(8):
                for x in range(8):
                    p=px[cx*8+x,cy*8+y]
                    if lum(p)>=linethr:                  # non-outline -> contributes to fill colour
                        k=min(keys,key=lambda kk:d2(p,PAL[kk]))
                        cnt[k]+=1
            if cnt:
                (fc,fb),_=cnt.most_common(1)[0]
            else:
                fc,fb='w',1
            attr[cy][cx]=(fb<<6)|(IDX[fc]<<3)|0          # paper=fill colour, ink=black
            for y in range(8):
                for x in range(8):
                    if lum(px[cx*8+x,cy*8+y])<linethr: bmp[cy*8+y][cx*8+x]=1   # outline
    # frame: white paper, black ink, rounded
    for cy in range(ch):
        for cx in range(cw):
            if cx in(0,cw-1) or cy in(0,ch-1): attr[cy][cx]=(1<<6)|(7<<3)|0
    for x in range(W): bmp[0][x]=1;bmp[H-1][x]=1
    for y in range(H): bmp[y][0]=1;bmp[y][W-1]=1
    for x,yv in[(0,0),(1,0),(0,1),(W-1,0),(W-2,0),(W-1,1),(0,H-1),(1,H-1),(0,H-2),(W-1,H-1),(W-2,H-1),(W-1,H-2)]: bmp[yv][x]=0
    return bmp,attr,W,H
def png(bmp,attr,cw,ch,path,scale=5):
    W,H=cw*8,ch*8; im=Image.new("RGB",(W,H)); o=im.load()
    for y in range(H):
        for x in range(W):
            at=attr[y//8][x//8]; br=(at>>6)&1; paper=(at>>3)&7; ink=at&7
            inv={v:k for k,v in IDX.items()}
            o[x,y]=PAL[(inv[ink],br)] if bmp[y][x] else PAL[(inv[paper],br)]
    out=im.resize((W*scale,H*scale),Image.NEAREST); out.save(path); return out
