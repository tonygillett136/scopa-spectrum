#!/usr/bin/env python3
"""Ace of Coins (eagle) title WITH full text. Keep the eagle full-bleed 'as now',
push SCOPA up into the eagle, dedication + keys on a bottom plate. Spectrum-accurate."""
import sys; sys.path.insert(0,'/tmp')
from title_lib import *
from PIL import Image, ImageDraw

def rle_compress(data):
    out=bytearray(); i=0; n=len(data)
    while i<n:
        run=1
        while i+run<n and data[i+run]==data[i] and run<127: run+=1
        if run>=3: out.append(0x80|run); out.append(data[i]); i+=run
        else:
            start=i
            while i<n:
                r=1
                while i+r<n and data[i+r]==data[i] and r<127: r+=1
                if r>=3: break
                i+=1
                if i-start==127: break
            out.append(i-start); out+=data[start:i]
    return bytes(out)

DED=["Based on an original ZX Spectrum","game by Angelo Colucci","© Tony Gillett 2026"]
KEYS="SPACE = START    H = HOW TO PLAY"
def dedication(img,y0,keys_y):
    d=ImageDraw.Draw(img); cf=arial(9,False)
    for i,l in enumerate(DED): text_c(d,128,y0+i*9,l,cf,(190,190,190))
    text_c(d,128,keys_y,KEYS,arial(9,False),(255,255,255))

# V1: eagle full-bleed (as proto_2), SCOPA pushed up, dedication band at bottom
def v1(scopa_y):
    img=fill("01_Asso_di_denari.jpg",(0.0,0.02,1.0,0.50),sat=1.2,con=1.05)
    wordmark(img,scopa_y,sz=34,plate=True)               # SCOPA + black plate, pushed up
    d=ImageDraw.Draw(img); d.rectangle([0,144,255,191],fill=(0,0,0))  # bottom text band
    dedication(img,146,179)
    return img

for tag,sy in (("hi",70),("mid",88)):
    img=v1(sy); scr=img_to_scr(img); scr_to_png(scr,f"/tmp/eagle_{tag}.png")
    print(f"eagle SCOPA@{sy}: title.rle {len(rle_compress(scr))} bytes")
