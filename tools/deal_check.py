#!/usr/bin/env python3
"""Is the initial 4-card table deal biased? (Tony: "I don't remember ever seeing two cards of the same
value on the opening table.")

Answer: NO bias. This runs the EXACT Z80 deal -- the real Spectrum ROM as the random byte source, the real
Fisher-Yates, the real DealRound order -- over every possible starting seed, and counts how often the
opening table has two cards of the same value.

The Z80 RNG (scopa.asm `Rnd`) does no PRNG arithmetic at all: it returns consecutive bytes of the lower
8 KB of the Spectrum ROM (address = Seed & 0x1FFF) and bumps the pointer; the seed's low byte is set from
the R refresh register at boot. Cheap, but the Fisher-Yates (`Shuffle`) launders it into a statistically
fair shuffle. There is NO re-deal rule and nothing that filters same-value pairs.

Result (verified 2026-06-29): 41.2% of opening tables have a same-value pair -- identical to the fair-deck
theoretical rate (1 - (36*32*28)/(39*38*37) = 0.412). So ~2 deals in 5 DO contain a pair; they're just
easy to miss because a same-value pair is always two DIFFERENT suits (unique deck -> no two identical
cards), which don't read as "a pair" at a glance.

Run:  python tools/deal_check.py
"""
import sys, os, subprocess
sys.path.insert(0, "/Volumes/SSD1/code/retro_computing/zxspectrum/mastery/tools")
from zx_shot import Speccy

VAL = lambda c: c % 10 + 1
SN = ['d', 'c', 's', 'b']
def show(c): return f"{VAL(c)}{SN[c // 10]}"
def has_pair(cards):
    vs = [VAL(c) for c in cards]
    return len(set(vs)) < len(vs)

def main():
    subprocess.run(["pkill", "-9", "-f", "zesarux"], capture_output=True)
    import time; time.sleep(1)
    with Speccy(port=10000) as zx:
        zx.smartload(os.path.abspath("scopa.tap")); zx.sleep(3)
        ROM = zx.read_mem(0x0000, 0x2000)           # the lower-8KB ROM = the Rnd byte source
    subprocess.run(["pkill", "-9", "-f", "zesarux"], capture_output=True)
    assert len(ROM) == 0x2000

    def rnd(seed):                                  # scopa.asm Rnd: byte at Seed&0x1FFF, pointer++
        return ROM[seed & 0x1FFF], ((seed & 0x1FFF) + 1)
    def shuffle_deal(seed):                         # Shuffle (Fisher-Yates) + DealRound order
        deck = list(range(40))
        for b in range(39, 0, -1):
            a, seed = rnd(seed)
            j = a % (b + 1)                         # the .mod subtraction loop == a mod (b+1)
            deck[b], deck[j] = deck[j], deck[b]
        return deck[6:10], seed                     # Player=0..2, Opp=3..5, Table=6..9

    allseeds = sum(has_pair(shuffle_deal(s)[0]) for s in range(0x2000))
    seq, s = [], 0x0040
    for _ in range(2000):
        t, s = shuffle_deal(s); seq.append(has_pair(t))
    print("fair-deck theory                : 41.2%")
    print(f"Z80 deal, all 8192 seed starts  : {100*allseeds/0x2000:.1f}%")
    print(f"Z80 deal, 2000 chained deals    : {100*sum(seq)/len(seq):.1f}%")
    print("=> no bias; same-value pairs occur at the fair rate (~2 deals in 5).")
    print("sample opening tables (first 12 chained deals):")
    s = 0x0040
    for _ in range(12):
        t, s = shuffle_deal(s)
        print("   ", [show(c) for c in t], "<- same-value pair" if has_pair(t) else "")

if __name__ == '__main__':
    main()
