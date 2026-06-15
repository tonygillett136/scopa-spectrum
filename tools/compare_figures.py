import sys,os; sys.path.insert(0,os.path.dirname(__file__))
from PIL import Image, ImageFilter, ImageDraw
import mono_outline as M
CW,CH=6,8
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
    return b
def render(b,scale=5):
    W,H=CW*8,CH*8; im=Image.new('RGB',(W,H),(255,255,255)); px=im.load()
    for y in range(H):
        for x in range(W):
            if b[y][x]: px[x,y]=(0,0,0)
    return im.resize((W*scale,H*scale),Image.NEAREST)
REF="/Volumes/SSD1/code/scopa_spectrum/reference_cards/"
cards=[("Re spade","30_Dieci_di_spade.jpg"),("Cav coppe","19_Nove_di_coppe.jpg"),
       ("Fante bast","38_Otto_di_bastoni.jpg"),("Re denari","10_Dieci_di_denari.jpg")]
variants=[("CURRENT",dict()),
          ("LIGHTER",dict(darkthr=58,gamma=2.4)),
          ("CLEANER",dict(darkthr=50,edgethr=115,gamma=2.0,blur=0.8))]
scale=5; cw,ch=CW*8*scale,CH*8*scale; gap=10; lblh=18
W=len(variants)*(cw+gap)+gap; Hh=len(cards)*(ch+gap+lblh)+gap+lblh
m=Image.new('RGB',(W,Hh),(40,40,40)); d=ImageDraw.Draw(m)
for vi,(vn,_) in enumerate(variants):
    d.text((gap+vi*(cw+gap)+cw//3,2),vn,fill=(255,255,0))
for ci,(cn,cf) in enumerate(cards):
    y0=lblh+gap+ci*(ch+gap+lblh)
    d.text((4,y0),cn,fill=(0,255,255))
    for vi,(vn,vp) in enumerate(variants):
        b=dm(REF+cf,**vp)
        m.paste(render(b,scale),(gap+vi*(cw+gap),y0+lblh))
m.save("/tmp/figure_compare.png"); print("/tmp/figure_compare.png")
