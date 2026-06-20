#!/usr/bin/env python3
"""Build + verify (byte-exact) + time each ZX0 decoder variant (standard/turbo/mega).
For each: assemble MODE 2 -> decode all 41 cards -> compare to deck.bin; then assemble
MODE 21 -> decode round-robin for 250 frames -> per-card T-states."""
import sys, os, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Volumes/SSD1/code/retro_computing/zxspectrum/mastery/tools")
from zx_shot import Speccy

SJ = "/Volumes/SSD1/code/retro_computing/zxspectrum/mastery/tools/sjasmplus"
CARD = 384
FRAME_T = 69888
NFRAMES = 250
deck = open(os.path.join(HERE, "deck.bin"), "rb").read()
NCARD = len(deck)//CARD
NAMES = {0: "standard (68B)", 1: "turbo (126B)", 2: "mega (673B)"}

def asm(mode, dec):
    r = subprocess.run([SJ, "main.asm", f"-DMODE={mode}", f"-DDEC={dec}", "--sym=main.sym"],
                       cwd=HERE, capture_output=True, text=True)
    if "Errors: 0" not in (r.stdout + r.stderr):
        print(r.stdout, r.stderr); sys.exit(f"assemble failed MODE={mode} DEC={dec}")

def sym(name):
    for ln in open(os.path.join(HERE, "main.sym")):
        if ln.startswith(name+":") and "EQU" in ln:
            return int(ln.split("0x")[-1].strip(), 16) & 0xFFFF
    return None

def run(load_sleep):
    pkill()
    zx = Speccy(port=10000)
    zx.smartload(os.path.join(HERE, "main.sna"))
    zx.sleep(load_sleep)
    return zx

def pkill():
    subprocess.run(["pkill","-9","-f","zesarux"], capture_output=True); time.sleep(0.8)

print(f"{'decoder':16} {'verify':10} {'T/card':>9} {'T/byte':>8} {'frac of frame':>14}")
print("-"*62)
results = {}
for dec in (0, 1, 2):
    # ---- verify (MODE 2) ----
    asm(2, dec)
    zx = run(1.0)
    bad = 0
    for c in range(NCARD):
        if bytes(zx.read_mem(0xC000+c*CARD, CARD)) != deck[c*CARD:(c+1)*CARD]:
            bad += 1
    zx.close(); pkill()
    verify = "PASS" if bad == 0 else f"FAIL({bad})"
    # ---- time (MODE 21) ----
    asm(21, dec)
    tc = sym("TmCount")
    zx = run(6.0)
    cnt = int.from_bytes(zx.read_mem(tc, 2), "little")
    zx.close(); pkill()
    per = NFRAMES*FRAME_T/cnt if cnt else 0
    results[dec] = (verify, per, cnt)
    print(f"{NAMES[dec]:16} {verify:10} {per:9.0f} {per/CARD:8.1f} {per/FRAME_T*100:13.1f}%")

print("\n(per-card decode includes <~1% ROM-ISR overhead => slight OVERestimate)")
print(f"frame = {FRAME_T} T; top-region behind-beam window ~55,000 T; bottom-border/vblank ~26,900 T")
