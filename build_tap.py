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

loadzx0=open("loading.zx0","rb").read()    # ZX0-packed loading screen -> decoded to 0x4000 at boot
code=open("scopa_code.bin","rb").read()    # 0x8000
title=open("title.zx0","rb").read()        # 0x6000 (ZX0-packed; decoded to 0x4000 at boot)
title2=open("title2.zx0","rb").read()      # 0x6000+len(title) (second rotating title screen)
deck=open("deck_zx0.bin","rb").read()      # 0xC000  (ZX0-COMPRESSED deck + index)
decoder=open("decoder.bin","rb").read()    # 0xE100  (decoder + dzx0 + cache code + CacheIds=0xFF)
winzx0=open("win_zx0.bin","rb").read()     # 0xF20A  (ZX0 VINCITORE screen; = CacheBase + CACHEN*384)
WINADDR=0xF20A                             # past the 10-slot card cache; ShowWinYou unpacks it to 0x4000

import re
def sym(name):                             # read a label's address from the assembler symbol file
    for ln in open("scopa.sym"):
        if ln.split(":",1)[0].strip()==name:
            return int(re.search(r"0x[0-9A-Fa-f]+",ln).group(),16)
    raise SystemExit(f"{name} not found in scopa.sym -- assemble first")
DZX0=sym("dzx0_standard")                   # the 68B ZX0 decoder lives inside decoder.bin (@0xE100..)
TAPEFLAG=sym("TapeFlag")                     # loader sets this to 1 so the game skips its boot hold

# ---- tiny ML loader (POKEd to the printer buffer @23296) ----
# Loads everything SILENTLY via ROM LD-BYTES (0x0556). The loading screen is ZX0-packed: load the
# decoder (which contains dzx0) FIRST, stream the compressed screen into a scratch buffer @0x6000,
# decode it onto 0x4000 (a clean POP-IN), then load the rest CONTINUOUSLY and jump to the game.
# CRITICAL: the loader must NEVER pause between blocks -- a continuously-playing tape/TZXDuino
# streams the next block past the Spectrum while it waits, desyncing the load. So there's no hold
# here; instead it sets TapeFlag=1 (the game then skips its boot min-display hold -- a snapshot
# load leaves the flag 0 and gets the brief hold). No "Bytes:" messages, no LOAD SCREEN$ build-up.
def w16(n): return [n & 0xFF, (n >> 8) & 0xFF]
def ldbytes(dest, length):
    # ld ix,dest : ld de,length : ld a,0xFF : scf : call 0x0556
    return [0xDD,0x21]+w16(dest)+[0x11]+w16(length)+[0x3E,0xFF,0x37,0xCD,0x56,0x05]
LOADER = ([0xF3]                                          # di
          + [0x21,0x00,0x58, 0x11,0x01,0x58, 0x01,0xFF,0x02, 0x36,0x00, 0xED,0xB0]  # blank attrs 0x5800.. black
          + ldbytes(0xE100, len(decoder))                 # decoder (incl. dzx0) FIRST
          + ldbytes(0x6000, len(loadzx0))                 # compressed loading screen -> scratch @0x6000
          # V-SYNCED reveal (no "horizontal blinds"): decode the screen to a SHADOW @0xC000 (free until the
          # deck loads there later), copy the bitmap to 0x4000 under the still-black attrs (invisible), then
          # sync to the top border and LDIR the 768 attrs in one beam-locked colour flip. The loader is di'd,
          # so the vsync is ei:halt:di -- one frame, which the next block's long pilot leader absorbs (no desync).
          + [0x21,0x00,0x60, 0x11,0x00,0xC0] + [0xCD]+w16(DZX0)               # decode SCR -> shadow @0xC000
          + [0x21,0x00,0xC0, 0x11,0x00,0x40, 0x01,0x00,0x18, 0xED,0xB0]       # ldir bitmap 0xC000->0x4000 (6144)
          + [0xFB, 0x76, 0xF3]                                                # ei : halt : di  -> vblank
          + [0x21,0x00,0xD8, 0x11,0x00,0x58, 0x01,0x00,0x03, 0xED,0xB0]       # ldir attrs 0xD800->0x5800 (768)
          + ldbytes(0x8000, len(code))
          + ldbytes(0x6000, len(title))                   # title overwrites the loading.zx0 scratch
          + ldbytes(0x6000+len(title), len(title2))
          + ldbytes(0xC000, len(deck))
          + ldbytes(WINADDR, len(winzx0))
          + [0x3E,0x01, 0x32]+w16(TAPEFLAG)               # ld a,1 : ld (TapeFlag),a -> "loaded from tape"
          + [0xC3,0x00,0x80])                             # jp 0x8000
LADDR = 23296
LEND  = LADDR + len(LOADER) - 1

# ---- BASIC: poke the loader, run it (no LOAD SCREEN$ -> the loader pops the screen in itself) ----
prog  = line(10, [('k','CLEAR'),('n',32767)],
                 [('k','RESTORE'),('n',100)],
                 [('k','FOR'),('r','n'),('r','='),('n',LADDR),('k','TO'),('n',LEND)],
                 [('k','READ'),('r','a')],[('k','POKE'),('r','n'),('r',','),('r','a')],[('k','NEXT'),('r','n')],
                 [('k','RANDOMIZE'),('k','USR'),('n',LADDR)])
dspec = [('k','DATA')]
for i,b in enumerate(LOADER):
    if i: dspec.append(('r',','))
    dspec.append(('n',b))
prog += line(100, dspec)

# ---- tape: BASIC (headered), then HEADERLESS blocks in LOAD order (decoder first -> dzx0 ready) ----
tap  = header(0,"scopa",len(prog),10,len(prog))+block(0xFF,prog)
tap += block(0xFF,decoder)     # headerless -> loaded by the ML loader (dzx0 needed before the screen)
tap += block(0xFF,loadzx0)
tap += block(0xFF,code)
tap += block(0xFF,title)
tap += block(0xFF,title2)
tap += block(0xFF,deck)
tap += block(0xFF,winzx0)
open("scopa.tap","wb").write(tap)
print(f"scopa.tap = {len(tap)} bytes | BASIC {len(prog)}B (loader {len(LOADER)}B@{LADDR}) + "
      f"DECODER {len(decoder)}B@0xE100 + LOAD-ZX0 {len(loadzx0)}B(pop-in) + CODE {len(code)}B@0x8000 + "
      f"TITLE {len(title)}+{len(title2)}B@0x6000 + ZX0-DECK {len(deck)}B@0xC000 + WIN {len(winzx0)}B@0x{WINADDR:X}")
