#!/usr/bin/env python3
"""Compare traditional fonts for the banner wordmark at Spectrum res. Renders VINCITORE on a
black band in each candidate (letter-spaced + hard-thresholded), quantizes, stacks for review."""
import os
from PIL import Image, ImageDraw, ImageFont
OUT=os.path.dirname(os.path.abspath(__file__)); SUP="/System/Library/Fonts/Supplemental/"
def pal(i,b):
    c=0xFF if b else 0xCD
    return (c if i&2 else 0,c if i&4 else 0,c if i&1 else 0)
CAND={b:[pal(i,b) for i in range(8)] for b in (0,1)}
def q(img):  # quantize any 256xH (H%8==0) to a flat-2-colour preview image
    W,H=img.size; px=img.convert('RGB').load(); out=Image.new('RGB',(W,H)); op=out.load()
    for cy in range(H//8):
        for cx in range(W//8):
            pix=[px[cx*8+x,cy*8+y] for y in range(8) for x in range(8)]
            best=(1e30,0,0,1)
            for br in(0,1):
                cd=CAND[br]; dl=[[(p[0]-c[0])**2+(p[1]-c[1])**2+(p[2]-c[2])**2 for c in cd] for p in pix]
                for a in range(8):
                    for b in range(a+1,8):
                        e=sum(min(dr[a],dr[b]) for dr in dl)
                        if e<best[0]: best=(e,a,b,br)
            _,ia,ib,br=best; pr,ik=CAND[br][ia],CAND[br][ib]
            for y in range(8):
                for x in range(8):
                    c=pix[y*8+x]
                    op[cx*8+x,cy*8+y]= ik if (c[0]-ik[0])**2+(c[1]-ik[1])**2+(c[2]-ik[2])**2 < (c[0]-pr[0])**2+(c[1]-pr[1])**2+(c[2]-pr[2])**2 else pr
    return out
def tracked(md,word,font,sp):
    ws=[md.textbbox((0,0),ch,font=font)[2] for ch in word]; return sum(ws)+sp*(len(word)-1),ws
def strip(word,path,idx,size,sp,thr=80,maxw=226):
    f=ImageFont.truetype(path,size,index=idx)
    md=ImageDraw.Draw(Image.new('L',(4,4)))
    while size>10:
        tw,_=tracked(md,word,f,sp)
        if tw<=maxw: break
        size-=1; f=ImageFont.truetype(path,size,index=idx)
    img=Image.new('L',(256,32),0); d=ImageDraw.Draw(img)
    tw,ws=tracked(md,word,f,sp); x=128-tw//2
    asc=f.getmetrics()[0]
    for ch,w in zip(word,ws):
        bb=d.textbbox((0,0),ch,font=f); d.text((x-bb[0],4),ch,font=f,fill=255); x+=w+sp
    m=img.point(lambda v:255 if v>=thr else 0)
    band=Image.new('RGB',(256,32),(0,0,0)); band.paste(Image.new('RGB',(256,32),(255,255,0)),(0,0),m)
    return q(band)

fonts=[("Rockwell",SUP+"Rockwell.ttc",0,2),("Rockwell-bold?",SUP+"Rockwell.ttc",1,2),
       ("SuperClarendon",SUP+"SuperClarendon.ttc",1,2),("AmTypewriter-bold",SUP+"AmericanTypewriter.ttc",2,1),
       ("Georgia-bold",SUP+"Georgia Bold.ttf",0,2),("Courier-bold",SUP+"Courier New Bold.ttf",0,0)]
rows=[]
for name,path,idx,sp in fonts:
    try: rows.append((name,strip("VINCITORE",path,idx,28,sp)))
    except Exception as e: print("skip",name,e)
big=Image.new('RGB',(256,32*len(rows)),(40,40,40))
for i,(name,s) in enumerate(rows): big.paste(s,(0,i*32))
big.resize((256*3,32*len(rows)*3),Image.NEAREST).save(f"{OUT}/font_test.png")
print("fonts:", [r[0] for r in rows]); print("-> font_test.png")
