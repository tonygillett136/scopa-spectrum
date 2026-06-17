#!/usr/bin/env python3
"""Ace of Swords title WITH the full title text (dedication + SPACE/H). Two layouts.
Renders Spectrum-accurate PNGs AND measures the rle-compressed .scr size."""
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

def dedication(img, y0, keys_y):
    d=ImageDraw.Draw(img); cf=arial(9,False)
    for i,line in enumerate(DED):
        text_c(d,128,y0+i*9,line,cf,(190,190,190))
    text_c(d,128,keys_y,KEYS,arial(9,False),(255,255,255))

# ---------- Option A: full-bleed sword, SCOPA on top plate, dedication on bottom plate ----------
def optionA():
    img=fill("21_Asso_di_spade.jpg",(0.18,0.12,0.92,0.56),sat=1.25,con=1.08)
    d=ImageDraw.Draw(img)
    d.rectangle([0,0,255,39],fill=(0,0,0))               # top SCOPA plate (rows 0-4)
    wordmark(img,4,sz=30,plate=False)
    d.rectangle([0,144,255,191],fill=(0,0,0))            # bottom text plate (rows 18-23)
    dedication(img,146,179)
    return img

# ---------- Option B: SCOPA top, sword middle band on black, text bottom (framed) ----------
def optionB():
    img=Image.new('RGB',(256,192),(0,0,0))
    sw=fill("21_Asso_di_spade.jpg",(0.16,0.16,0.95,0.52),sat=1.25,con=1.08)
    img.paste(sw.resize((256,104)),(0,40))               # sword band rows 5-17
    d=ImageDraw.Draw(img)
    d.rectangle([0,0,255,39],fill=(0,0,0))               # top SCOPA plate
    wordmark(img,4,sz=30,plate=False)
    d.rectangle([0,144,255,191],fill=(0,0,0))            # bottom text plate
    dedication(img,146,179)
    return img

for name,fn in (("A",optionA),("B",optionB)):
    img=fn(); scr=img_to_scr(img); scr_to_png(scr,f"/tmp/sword_{name}.png")
    comp=rle_compress(scr)
    print(f"option {name}: title.rle would be {len(comp)} bytes ({100*len(comp)//6912}% of 6912)")
