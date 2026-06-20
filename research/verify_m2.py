#!/usr/bin/env python3
"""M2 verification: load main.sna (MODE 2), let it ZX0-decode all 41 cards into 0xC000,
read that region back from ZEsarUX, and compare BYTE-EXACT to deck.bin. This is the real
roundtrip: official zx0 compressor (host) <-> official dzx0_standard decoder (on the Z80)."""
import sys, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Volumes/SSD1/code/retro_computing/zxspectrum/mastery/tools")
from zx_shot import Speccy

CARD = 384
deck = open(os.path.join(HERE, "deck.bin"), "rb").read()
NCARD = len(deck) // CARD

ok = True
try:
    with Speccy(port=10000) as zx:
        zx.smartload(os.path.join(HERE, "main.sna"))
        zx.sleep(1.0)                       # decode of 41 cards is <<1 frame; 1s is ample
        mism = []
        for c in range(NCARD):
            got = bytes(zx.read_mem(0xC000 + c*CARD, CARD))
            exp = deck[c*CARD:(c+1)*CARD]
            if got != exp:
                # find first differing byte
                d = next((i for i in range(CARD) if got[i] != exp[i]), -1)
                mism.append((c, d))
        if mism:
            ok = False
            print(f"FAIL: {len(mism)}/{NCARD} cards mismatched")
            for c, d in mism[:8]:
                print(f"  card {c}: first diff at byte {d}")
        else:
            print(f"PASS: all {NCARD} cards decoded BYTE-EXACT (15744B) by dzx0_standard on the Z80")
finally:
    subprocess.run(["pkill", "-9", "-f", "zesarux"], capture_output=True)

sys.exit(0 if ok else 1)
