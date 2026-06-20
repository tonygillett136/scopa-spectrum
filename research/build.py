#!/usr/bin/env python3
"""Build the sandbox: compress (if needed), assemble for a given MODE/DEC, emit main.sna
+ main.tap.  Usage: python3 build.py [MODE] [DEC]   (defaults MODE=5 DEC=2 = slide/mega)

MODE: 2=verify-decode  3=static board  4=riffle (beam-race pipeline)  5=slide (tear test)
DEC : 0=standard(68B)  1=turbo(126B)  2=mega(673B)
"""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
SJ = "/Volumes/SSD1/code/retro_computing/zxspectrum/mastery/tools/sjasmplus"
MODE = sys.argv[1] if len(sys.argv) > 1 else "5"
DEC = sys.argv[2] if len(sys.argv) > 2 else "2"

if not os.path.exists(os.path.join(HERE, "deck.zx0")):
    subprocess.run([sys.executable, "compress_deck.py"], cwd=HERE, check=True)

r = subprocess.run([SJ, "main.asm", f"-DMODE={MODE}", f"-DDEC={DEC}", "--sym=main.sym"],
                   cwd=HERE, capture_output=True, text=True)
if "Errors: 0" not in (r.stdout + r.stderr):
    print(r.stdout, r.stderr); sys.exit("assemble failed")

# ---- wrap main_code.bin (0x8000..) into a .tap: BASIC loader + one CODE block ----
code = open(os.path.join(HERE, "main_code.bin"), "rb").read()
ORG = 0x8000

def block(flag, data):
    body = bytes([flag]) + data
    c = 0
    for x in body:
        c ^= x
    return (len(body) + 1).to_bytes(2, "little") + body + bytes([c])

def header(typ, name, length, p1, p2):
    return block(0, bytes([typ]) + name.encode()[:10].ljust(10) +
                 length.to_bytes(2, "little") + p1.to_bytes(2, "little") + p2.to_bytes(2, "little"))

# BASIC: 10 CLEAR 32767: LOAD ""CODE: RANDOMIZE USR 32768
CLEAR, LOAD, CODE, RAND, USR = 0xFD, 0xEF, 0xAF, 0xF9, 0xC0
def numtok(n): return str(n).encode() + bytes([0x0E,0,0, n & 0xFF, (n >> 8) & 0xFF, 0])
basic = bytearray()
basic += bytes([CLEAR]) + numtok(32767) + b":" + bytes([LOAD]) + b'""' + bytes([CODE]) + b":"
basic += bytes([RAND]) + bytes([USR]) + numtok(ORG) + bytes([0x0D])
line = bytes([0, 10, len(basic) & 0xFF, len(basic) >> 8]) + bytes(basic)

tap = header(0, "beamrace", len(line), 10, len(line)) + block(0xFF, line)
tap += header(3, "beamcode", len(code), ORG, 0x8000) + block(0xFF, code)
open(os.path.join(HERE, "main.tap"), "wb").write(tap)

print(f"built MODE={MODE} DEC={DEC}: main.sna + main.tap ({len(tap)}B, code {len(code)}B @0x{ORG:04X})")
