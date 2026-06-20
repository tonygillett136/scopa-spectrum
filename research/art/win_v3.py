#!/usr/bin/env python3
"""Win/lose screens — v3: DESIGNED victory compositions (not just a cropped photo).
Concepts: glory sunburst + portrait medallion + banner; a drawn gold-crown emblem; the cup as a
trophy on rays; a fanned winning hand. Native Spectrum design elements + the optimal-quantize +
dither engine. Run: .venv/bin/python art/win_v3.py
"""
import os, math
from collections import Counter
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

REF = "/Volumes/SSD1/code/scopa_spectrum/reference_cards"
OUT = os.path.dirname(os.path.abspath(__file__))
GRN,WHT,RED,YEL,GLD,BLU,BLK = (0,205,0),(255,255,255),(205,0,0),(205,205,0),(255,215,0),(0,0,205),(0,0,0)

# ---------- Spectrum engine (optimal 2-colour/cell + brightness + Bayer dither) ----------
def pal(i,b):
    c=0xFF if b else 0xCD
    return (c if i&2 else 0, c if i&4 else 0, c if i&1 else 0)
CAND={b:[pal(i,b) for i in range(8)] for b in (0,1)}
BAYER=[[0,32,8,40,2,34,10,42],[48,16,56,24,50,18,58,26],[12,44,4,36,14,46,6,38],
       [60,28,52,20,62,30,54,22],[3,35,11,43,1,33,9,41],[51,19,59,27,49,17,57,25],
       [15,47,7,39,13,45,5,37],[63,31,55,23,61,29,53,21]]
def img_to_scr(img, dither=True):
    px=img.convert('RGB').load(); bm=bytearray(6144); at=bytearray(768)
    for cy in range(24):
        for cx in range(32):
            pix=[px[cx*8+x,cy*8+y] for y in range(8) for x in range(8)]
            best=(1e30,0,0,1)
            for br in (0,1):
                cd=CAND[br]
                dl=[[(p[0]-c[0])**2+(p[1]-c[1])**2+(p[2]-c[2])**2 for c in cd] for p in pix]
                for a in range(8):
                    for b in range(a+1,8):
                        e=0
                        for dr in dl:
                            da,db=dr[a],dr[b]; e+= da if da<db else db
                        if e<best[0]: best=(e,a,b,br)
            _,ia,ib,br=best; ca,cb=CAND[br][ia],CAND[br][ib]
            na=sum(1 for p in pix if (p[0]-ca[0])**2+(p[1]-ca[1])**2+(p[2]-ca[2])**2<=(p[0]-cb[0])**2+(p[1]-cb[1])**2+(p[2]-cb[2])**2)
            paper,ink=(ia,ib) if na>=32 else (ib,ia)
            pr,ik=CAND[br][paper],CAND[br][ink]
            nink=sum(1 for c in pix if (c[0]-ik[0])**2+(c[1]-ik[1])**2+(c[2]-ik[2])**2 < (c[0]-pr[0])**2+(c[1]-pr[1])**2+(c[2]-pr[2])**2)
            if nink<3:                          # near-uniform cell -> SOLID paper, no sprinkled stray colour
                at[cy*32+cx]=(br<<6)|(paper<<3)|paper
                continue
            for y in range(8):
                for x in range(8):
                    c=pix[y*8+x]
                    di=(c[0]-ik[0])**2+(c[1]-ik[1])**2+(c[2]-ik[2])**2
                    dp=(c[0]-pr[0])**2+(c[1]-pr[1])**2+(c[2]-pr[2])**2
                    if (dp/(di+dp+1)*64>BAYER[y&7][x&7]+0.5) if dither else (di<dp):
                        Y,X=cy*8+y,cx*8+x
                        bm[((Y&0xC0)<<5)|((Y&7)<<8)|((Y&0x38)<<2)|(X>>3)]|=(0x80>>(X&7))
            at[cy*32+cx]=(br<<6)|(paper<<3)|ink
    return bytes(bm)+bytes(at)
def despeckle(scr,thr=5):
    orig=scr[6144:]; ba=bytearray(scr)
    for cy in range(24):
        for cx in range(32):
            cur=orig[cy*32+cx]; cnt=Counter()
            for dy in(-1,0,1):
                for dx in(-1,0,1):
                    if dx==0 and dy==0: continue
                    ny,nx=cy+dy,cx+dx
                    if 0<=ny<24 and 0<=nx<32: cnt[orig[ny*32+nx]]+=1
            m,mc=cnt.most_common(1)[0]
            if mc>=thr and m!=cur: ba[6144+cy*32+cx]=m
    return bytes(ba)
def scr_to_png(scr,path,scale=2):
    im=Image.new('RGB',(256,192)); px=im.load(); bm,at=scr[:6144],scr[6144:]
    for Y in range(192):
        for X in range(256):
            off=((Y&0xC0)<<5)|((Y&7)<<8)|((Y&0x38)<<2)|(X>>3)
            bit=(bm[off]>>(7-(X&7)))&1; a=at[(Y>>3)*32+(X>>3)]
            px[X,Y]=pal(a&7,(a>>6)&1) if bit else pal((a>>3)&7,(a>>6)&1)
    im.resize((256*scale,192*scale),Image.NEAREST).save(path)

# ---------- design elements ----------
def bodoni(s): return ImageFont.truetype("/System/Library/Fonts/Supplemental/Bodoni 72.ttc",s)
def arial(s): return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf",s)
def tc(d,cx,y,s,f,fill,outline=None):
    bb=d.textbbox((0,0),s,font=f); x=cx-(bb[2]-bb[0])//2-bb[0]; yy=y-bb[1]
    if outline:
        for ox in(-2,-1,1,2):
            for oy in(-2,-1,1,2): d.text((x+ox,yy+oy),s,font=f,fill=outline)
    d.text((x,yy),s,font=f,fill=fill)
def crisp_text(img,cx,y,word,size,col,maxw=224,thr=80,sp=2):
    """Wordmark in ROCKWELL (classic geometric slab serif) — traditional/period, but uniform
    strokes that survive Spectrum res (Bodoni's hairlines shatter; Arial Black blobs). Rendered
    with letter-spacing so glyphs never merge, auto-fit, then HARD-thresholded -> crisp letters."""
    F="/System/Library/Fonts/Supplemental/Rockwell.ttc"
    probe=ImageDraw.Draw(Image.new('L',(4,4)))
    def fit(sz):
        f=ImageFont.truetype(F,sz,index=0)
        ws=[probe.textbbox((0,0),ch,font=f)[2] for ch in word]
        return f,ws,sum(ws)+sp*(len(word)-1)
    f,ws,tw=fit(size)
    while size>12 and tw>maxw: size-=1; f,ws,tw=fit(size)
    mask=Image.new('L',img.size,0); md=ImageDraw.Draw(mask); x=cx-tw//2
    for ch,w in zip(word,ws):
        bb=md.textbbox((0,0),ch,font=f); md.text((x-bb[0], y-bb[1]),ch,font=f,fill=255); x+=w+sp
    mask=mask.point(lambda v:255 if v>=thr else 0)            # hard edges
    img.paste(Image.new('RGB',img.size,col),(0,0),mask)
def sunburst(d,cx,cy,R=340,n=15,c1=(255,255,0),c2=(120,120,0)):
    for i in range(n*2):
        a0=(i/(n*2))*2*math.pi+0.04; a1=((i+1)/(n*2))*2*math.pi+0.04
        d.polygon([(cx,cy),(cx+R*math.cos(a0),cy+R*math.sin(a0)),(cx+R*math.cos(a1),cy+R*math.sin(a1))],
                  fill=c1 if i%2==0 else c2)
def card_top(jpg, w, h, crop=0.60):
    im=Image.open(f"{REF}/{jpg}").convert('RGB'); iw,ih=im.size
    im=im.crop((0,0,iw,int(ih*crop)))
    im=ImageEnhance.Color(im).enhance(1.7); im=ImageEnhance.Contrast(im).enhance(1.18)
    im=im.resize((w,h),Image.LANCZOS).filter(ImageFilter.SHARPEN)
    ImageDraw.Draw(im).rectangle([0,0,w-1,h-1],outline=WHT,width=2)
    return im
def fan_card(img,c,x,y,ang):
    r=c.rotate(ang,expand=True,fillcolor=BLK,resample=Image.BICUBIC)
    m=Image.new('L',c.size,255).rotate(ang,expand=True,fillcolor=0,resample=Image.BICUBIC)
    img.paste(r,(x,y),m)
def crown(d,cx,by,bw=104,sh=38,metal=GLD):
    bx0=cx-bw//2; bh=24
    d.rectangle([bx0,by,bx0+bw,by+bh],fill=metal)
    d.rectangle([bx0,by,bx0+bw,by+3],fill=WHT)                  # rim highlight
    xs=[bx0+6,bx0+bw//4,cx,bx0+3*bw//4,bx0+bw-6]
    for i,x in enumerate(xs):
        h=sh if i in(0,2,4) else sh-14
        d.polygon([(x-14,by+2),(x,by-h),(x+14,by+2)],fill=metal)
        d.ellipse([x-5,by-h-7,x+5,by-h+3],fill=WHT); d.ellipse([x-5,by-h-7,x+5,by-h+3],outline=metal)
    for jx,jc in [(cx-34,RED),(cx,BLU),(cx+34,RED)]:
        d.ellipse([jx-8,by+6,jx+8,by+19],fill=jc); d.ellipse([jx-8,by+6,jx+8,by+19],outline=WHT)
def laurel(d,cx,cy,rx=86,ry=70,col=GRN):
    for side in(-1,1):
        for deg in range(18,168,9):
            a=math.radians(deg); x=cx+side*int(rx*math.sin(a)); y=cy+int(ry*math.cos(a))
            d.ellipse([x-6,y-3,x+6,y+4],fill=col); d.ellipse([x-6,y-3,x+6,y+4],outline=BLK)
def banner(d,word,col,bg,y0=160):
    d.rectangle([0,y0,255,191],fill=BLK)
    d.polygon([(20,y0),(236,y0),(248,(y0+191)//2),(236,191),(20,191),(8,(y0+191)//2)],fill=bg)
    d.line([(8,(y0+191)//2),(20,y0),(236,y0),(248,(y0+191)//2),(236,191),(20,191),(8,(y0+191)//2)],fill=col,width=2)
    tc(d,128,y0+3,word,bodoni(23),col,outline=BLK)
def star(d,cx,cy,r,col=WHT):
    d.polygon([(cx,cy-r),(cx+r*.28,cy-r*.28),(cx+r,cy),(cx+r*.28,cy+r*.28),(cx,cy+r),
               (cx-r*.28,cy+r*.28),(cx-r,cy),(cx-r*.28,cy-r*.28)],fill=col)
def portrait(jpg,box,sat=1.5):
    im=Image.open(f"{REF}/{jpg}").convert('RGB'); iw,ih=im.size
    x0,y0,x1,y1=box; c=im.crop((int(iw*x0),int(ih*y0),int(iw*x1),int(ih*y1)))
    c=ImageEnhance.Color(c).enhance(sat); c=ImageEnhance.Contrast(c).enhance(1.18)
    c=ImageEnhance.Brightness(c).enhance(1.06)
    return c.filter(ImageFilter.SHARPEN)
def save(name,img):
    scr=despeckle(img_to_scr(img)); scr_to_png(scr,f"{OUT}/{name}.png"); open(f"{OUT}/{name}.scr","wb").write(scr)
    print(" ",name)

# ---------- CONCEPT 1: glory sunburst + portrait medallion + banner ----------
def stamp_banner(scr, word, ink_idx, BY=152, thr=80, sp=2):
    """Render the bottom banner (scroll outline + word) as a 1-bit INK mask and stamp it DIRECTLY
    into the SCR cells (paper=black, ink=ink_idx, bright) for char-rows BY/8..23 -- bypassing the
    photo quantizer/despeckle entirely, so the text is exactly as drawn (no holes, no clash). BY
    is a char-row boundary so banner cells never share with the picture above."""
    band=Image.new('L',(256,192),0); d=ImageDraw.Draw(band)
    d.line([(10,175),(24,BY+2),(232,BY+2),(246,175),(232,189),(24,189),(10,175)],fill=255,width=2)  # scroll
    F="/System/Library/Fonts/Supplemental/Rockwell.ttc"; size=30
    probe=ImageDraw.Draw(Image.new('L',(4,4)))
    def fit(sz):
        f=ImageFont.truetype(F,sz,index=0); ws=[probe.textbbox((0,0),ch,font=f)[2] for ch in word]
        return f,ws,sum(ws)+sp*(len(word)-1)
    f,ws,tw=fit(size)
    while size>12 and tw>222: size-=1; f,ws,tw=fit(size)
    x=128-tw//2
    for ch,w in zip(word,ws):
        bb=d.textbbox((0,0),ch,font=f); d.text((x-bb[0],164-bb[1]),ch,font=f,fill=255); x+=w+sp
    band=band.point(lambda v:255 if v>=thr else 0); bp=band.load()
    ba=bytearray(scr)
    for cy in range(BY//8,24):
        for cx in range(32):
            ba[6144+cy*32+cx]=(1<<6)|(0<<3)|ink_idx          # bright, black paper, ink_idx ink
            for ln in range(8):
                Y=cy*8+ln; byte=0
                for bit in range(8):
                    if bp[cx*8+bit,Y]>=128: byte|=(0x80>>bit)
                ba[((Y&0xC0)<<5)|((Y&7)<<8)|((Y&0x38)<<2)|cx]=byte
    return bytes(ba)

def glory(name, jpg, box, word="VINCITORE", ray=(255,255,0), cold=False):
    cx,cy,R=128,76,68
    img=Image.new('RGB',(256,192),BLK); d=ImageDraw.Draw(img)
    sunburst(d,cx,cy,R=300,c1=ray,c2=(50,45,0) if not cold else (10,16,34))
    p=portrait(jpg,box).resize((2*R,2*R),Image.LANCZOS)
    if cold:
        # subdued COLD-BLUE duotone (luminance -> steel blue ramp): defeat = the cool counterpart
        # to the win's warm gold. Clean (the solid-cell quantize fix prevents stray-blue speckle).
        L=ImageEnhance.Contrast(p.convert('L')).enhance(1.18)
        p=Image.merge('RGB',(L.point(lambda v:int(v*0.50)), L.point(lambda v:int(v*0.74)),
                              L.point(lambda v:min(255,int(v*1.05)+30))))
    m=Image.new('L',(2*R,2*R),0); ImageDraw.Draw(m).ellipse([0,0,2*R-1,2*R-1],fill=255)
    img.paste(p,(cx-R,cy-R),m)
    d.ellipse([cx-R-3,cy-R-3,cx+R+3,cy+R+3],outline=WHT,width=2)
    d.ellipse([cx-R-6,cy-R-6,cx+R+6,cy+R+6],outline=ray,width=3)
    for ang in range(0,360,30): star(d,cx+int((R+18)*math.cos(math.radians(ang))),cy+int((R+18)*math.sin(math.radians(ang))),2,WHT)
    # picture only -> quantize+despeckle; THEN stamp banner+word as clean cells (immune to both)
    scr=stamp_banner(despeckle(img_to_scr(img)), word, 6 if not cold else 7)
    scr_to_png(scr,f"{OUT}/{name}.png"); open(f"{OUT}/{name}.scr","wb").write(scr)
    print(" ",name)

# ---------- CONCEPT 2: drawn gold-crown emblem + laurel (clean iconic graphic) ----------
def emblem(name, word, cold=False):
    bg=(0,0,205) if not cold else (0,0,90)
    img=Image.new('RGB',(256,192),bg); d=ImageDraw.Draw(img)
    metal=GLD if not cold else (170,170,190)
    laurel(d,128,96,col=GRN if not cold else (90,100,120))
    crown(d,128,70,bw=120,sh=46,metal=metal)
    for sx,sy,sr in [(34,40,4),(222,42,4),(46,128,3),(210,126,3),(128,18,3)]:
        star(d,sx,sy,sr,WHT)
    banner(d,word,metal,(60,0,0) if not cold else (10,10,46))
    save(name,img)

# ---------- CONCEPT 3: fanned winning hand + crown + gold rays ----------
def fanned(name, cards, word, cold=False):
    img=Image.new('RGB',(256,192),BLK); d=ImageDraw.Draw(img)
    sunburst(d,128,92,R=270,c1=(190,150,0),c2=(45,36,0))
    cw,ch=62,90
    xs=[40,82,124,166]; angs=[26,9,-9,-26]; ys=[64,50,50,64]
    for c,x,y,a in zip(cards,xs,ys,angs): fan_card(img,card_top(c,cw,ch),x,y,a)
    crown(d,128,30,bw=64,sh=22,metal=GLD)
    banner(d,word,GLD,(60,0,0))
    save(name,img)

print("v3 batch:")
print(" concept 1 glory medallion:")
glory("v3_glory_king",  "10_Dieci_di_denari.jpg",(0.16,0.05,0.86,0.60))
glory("v3_glory_knight","29_Nove_di_spade.jpg",  (0.18,0.04,0.94,0.58))
glory("v3_glory_cup",   "11_Asso_di_coppe.jpg",  (0.10,0.02,0.92,0.66))
glory("v3_lose_knave",  "28_Otto_di_spade.jpg",  (0.14,0.05,0.90,0.62),word="PECCATO",ray=(0,140,155),cold=True)
print(" concept 2 crown emblem:")
emblem("v3_emblem_win",  "VINCITORE")
emblem("v3_emblem_lose", "PECCATO", cold=True)
print(" concept 3 fanned hand:")
fanned("v3_fan_win", ["07_Sette_di_denari.jpg","17_Sette_di_coppe.jpg","27_Sette_di_spade.jpg","37_Sette_di_bastoni.jpg"], "VINCITORE")
print("done")
