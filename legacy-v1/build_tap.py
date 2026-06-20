T={'CLEAR':0xFD,'LOAD':0xEF,'CODE':0xAF,'SCREEN$':0xAA,'RESTORE':0xE5,'FOR':0xEB,
   'TO':0xCC,'READ':0xE3,'POKE':0xF4,'NEXT':0xF3,'RANDOMIZE':0xF9,'USR':0xC0,'DATA':0xE4}
def num(n): return str(int(n)).encode()+bytes([0x0E,0x00,0x00,int(n)&0xFF,(int(n)>>8)&0xFF,0x00])
def tok(spec):
    out=bytearray()
    for k,v in spec:
        if k=='k': out.append(T[v])
        elif k=='n': out+=num(v)
        elif k=='s': out+=b'"'+v.encode()+b'"'
        elif k=='r': out+=v.encode()
    return bytes(out)
def line(numl,*specs):
    body=bytearray()
    for i,sp in enumerate(specs):
        if i: body+=b'\x3a'
        body+=tok(sp)
    body+=b'\x0d'
    return bytes([numl>>8,numl&0xFF,len(body)&0xFF,len(body)>>8])+body
def block(flag,data):
    body=bytes([flag])+data;c=0
    for x in body:c^=x
    return (len(body)+1).to_bytes(2,'little')+body+bytes([c])
def header(typ,name,length,p1,p2):
    return block(0,bytes([typ])+name.encode()[:10].ljust(10)+length.to_bytes(2,'little')+p1.to_bytes(2,'little')+p2.to_bytes(2,'little'))

loadscr=open("loading.scr","rb").read()    # 0x4000 (shown during load)
code=open("scopa_code.bin","rb").read()    # 0x8000
title=open("title.rle","rb").read()        # 0x6000 (SCOMPACT-packed; expanded to 0x4000 at boot)
title2=open("title2.rle","rb").read()      # 0x6000+len(title) (second rotating title screen)
deck=open("deck.bin","rb").read()          # 0xC000

# ---- tiny ML loader (POKEd to the printer buffer @23296) ----
# Loads code/title/deck SILENTLY via ROM LD-BYTES (0x0556) -> NO "Bytes:" messages
# over the loading screen, then jumps to the game at 0x8000.
def w16(n): return [n & 0xFF, (n >> 8) & 0xFF]
def ldbytes(dest, length):
    # ld ix,dest : ld de,length : ld a,0xFF : scf : call 0x0556
    return [0xDD,0x21]+w16(dest)+[0x11]+w16(length)+[0x3E,0xFF,0x37,0xCD,0x56,0x05]
LOADER = ([0xF3]                                   # di
          + ldbytes(0x8000, len(code))
          + ldbytes(0x6000, len(title))
          + ldbytes(0x6000+len(title), len(title2))   # second title screen, right after the first
          + ldbytes(0xC000, len(deck))
          + [0xC3,0x00,0x80])                      # jp 0x8000
LADDR = 23296
LEND  = LADDR + len(LOADER) - 1

# ---- BASIC: show the screen, poke the loader, run it ----
prog  = line(10, [('k','CLEAR'),('n',32767)],
                 [('k','LOAD'),('s',''),('k','SCREEN$')],          # artwork -> 0x4000 (shown)
                 [('k','RESTORE'),('n',100)],
                 [('k','FOR'),('r','n'),('r','='),('n',LADDR),('k','TO'),('n',LEND)],
                 [('k','READ'),('r','a')],[('k','POKE'),('r','n'),('r',','),('r','a')],[('k','NEXT'),('r','n')],
                 [('k','RANDOMIZE'),('k','USR'),('n',LADDR)])
dspec = [('k','DATA')]
for i,b in enumerate(LOADER):
    if i: dspec.append(('r',','))
    dspec.append(('n',b))
prog += line(100, dspec)

# ---- tape: BASIC + headered SCREEN$, then HEADERLESS code/title/deck (silent) ----
tap  = header(0,"scopa",len(prog),10,len(prog))+block(0xFF,prog)
tap += header(3,"scopaload",len(loadscr),0x4000,0x8000)+block(0xFF,loadscr)
tap += block(0xFF,code)     # headerless -> loaded by the ML loader
tap += block(0xFF,title)
tap += block(0xFF,title2)
tap += block(0xFF,deck)
open("scopa.tap","wb").write(tap)
print(f"scopa.tap = {len(tap)} bytes | BASIC {len(prog)}B (loader {len(LOADER)}B@{LADDR}) + "
      f"SCREEN${len(loadscr)}B@0x4000 + silent CODE {len(code)}B@0x8000 + TITLE {len(title)}B + TITLE2 {len(title2)}B@0x6000 + DECK {len(deck)}B@0xC000")
