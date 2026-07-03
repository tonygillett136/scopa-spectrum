#!/usr/bin/env python3
"""Replay ai_watch's flagged boards through the REAL Z80 ROM (TESTMODE 70 board-injection probe)
and confirm the shipped aiSelectPlay makes the SAME decision as the host mirror -- i.e. the findings
are the actual logic, not a mirror artefact.

Build first:  ../mastery/tools/sjasmplus scopa.asm -DTESTMODE=70 --sym=scopa.sym && python3 build_tap.py
Run:          python3 tools/ai_zx_check.py [odd_boards.json] [N]
"""
import sys, os, json, subprocess
sys.path.insert(0, "/Volumes/SSD1/code/retro_computing/zxspectrum/mastery/tools")
from zx_shot import Speccy

CMD, RSLOT, ROPT, RTN, RCAP = 0x7E00, 0x7E01, 0x7E02, 0x7E03, 0x7E04   # TM70 mailbox (fixed)
# State addresses come from scopa.sym -- the state ORG has moved four times in this project's
# history; hardcoding these silently poked wrong memory after any move. Requires a TM70 build
# (sjasmplus scopa.asm -DTESTMODE=70 --sym=scopa.sym) so the sym matches the loaded tape.
import re
def _sym(name):
    for ln in open("scopa.sym"):
        if ln.split(":", 1)[0].strip() == name:
            return int(re.search(r"0x[0-9A-Fa-f]+", ln).group(), 16)
    raise SystemExit(f"{name} not in scopa.sym -- assemble the TM70 build first")
Table, TableN, Opp = _sym("Table"), _sym("TableN"), _sym("Opp")
OPile, OPileN = _sym("OPile"), _sym("OPileN")
Seen, Difficulty, DeckPos, AceRule = _sym("Seen"), _sym("Difficulty"), _sym("DeckPos"), _sym("AceRule")
SCRATCH = os.path.join(os.path.dirname(__file__), "..", "tmp", "odd_boards.json")

def seen_bytes(cards):
    b = bytearray(5)
    for c in cards: b[c >> 3] |= 1 << (c & 7)
    return bytes(b)

def main():
    path = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith('.json') else SCRATCH
    boards = json.load(open(path))['dominated']
    N = int([a for a in sys.argv[1:] if a.isdigit()][0]) if any(a.isdigit() for a in sys.argv[1:]) else len(boards)
    subprocess.run(["pkill", "-9", "-f", "zesarux"], capture_output=True)
    import time; time.sleep(1)
    def probe(zx, rec):
        hand, table, pile, opile = rec['hand'], rec['table'], rec['pile'], rec['opile']
        zx.write_mem(Opp, bytes((hand + [0xFF, 0xFF, 0xFF])[:3]))
        zx.write_mem(Table, bytes(table)); zx.write_mem(TableN, bytes([len(table)]))
        zx.write_mem(OPile, bytes(pile[:40])); zx.write_mem(OPileN, bytes([len(pile)]))
        zx.write_mem(Seen, seen_bytes(table + hand + pile + opile))
        zx.write_mem(Difficulty, bytes([3])); zx.write_mem(DeckPos, bytes([20]))
        zx.write_mem(AceRule, bytes([0]))
        zx.write_mem(CMD, bytes([1]))
        for _ in range(40):
            zx.sleep(0.03)
            if zx.read_mem(CMD, 1)[0] == 0: break
        zslot = zx.read_mem(RSLOT, 1)[0]; zopt = zx.read_mem(ROPT, 1)[0]; ztn = zx.read_mem(RTN, 1)[0]
        if zopt == 0xFF: return zslot, None
        cap = zx.read_mem(RCAP, ztn)
        return zslot, set(i for i in range(ztn) if cap[i] != 0)
    match = total = 0
    with Speccy(port=10000) as zx:
        zx.smartload(os.path.abspath("scopa.tap")); zx.sleep(3)
        probe(zx, boards[0])                      # discard: the first injected board reads stale state
        for rec in boards[:N]:
            zslot, zcap = probe(zx, rec)
            mslot = rec['slot']; mcap = set(rec['capset']) if rec['capset'] else None
            ok = (zslot == mslot) and (zcap == mcap)
            total += 1; match += 1 if ok else 0
            tag = "OK " if ok else "XX "
            print(f"  {tag} Z80(slot {zslot}, cap {sorted(zcap) if zcap else 'drop'}) "
                  f"vs mirror(slot {mslot}, cap {sorted(mcap) if mcap else 'drop'})")
    subprocess.run(["pkill", "-9", "-f", "zesarux"], capture_output=True)
    print(f"\nZ80 vs mirror: {match}/{total} decisions identical "
          f"-> mirror is {'FAITHFUL' if match == total else 'DIVERGENT'} on these boards")

if __name__ == '__main__':
    main()
