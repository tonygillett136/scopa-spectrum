#!/usr/bin/env python3
"""Prototype: NAPOLA (and palle) awareness for the Scopa AI — Tony's observation, 2026-06-28.

The shipped 1-ply eval values 7s (+12), the settebello (+35) and coins (+5), but is BLIND to
the NAPOLA (A+2+3 of coins = 3 pts, +1 per further consecutive coin) and to the palle del cane
(all four 7s = +1). So it grabs a 7 (+12) over the coin that completes a 3-point napola (just a
+5 coin). Unlike primiera (EMERGENT over the whole deal -> ai_prime.py's experiment failed),
napola/palle are CONCRETE and attributable -- you hold them iff specific cards are in your pile,
exactly like the settebello, which the eval already values. So a pile-aware 1-ply term should work.

Adds a pile-aware napola/palle-GAIN term to capture scoring and measures it head-to-head vs the
SHIPPED weights in the faithful host-mirror. Run: python tools/ai_napola.py
"""
import random
import ai_tune
from ai_tune import (VAL, SUIT, PRIME_BY_VALUE, find_all_captures,
                     eval_capture, eval_drop, score_deal)

SHIPPED = dict(
    card_count=3, denari=5, settebello_cap=35, seven=12, six=8, ace=6, sweep=50,
    drop_settebello=-40, drop_seven=-5, drop_six=-5, drop_denari=-4, drop_face=3,
    leave_sweep_risk=-9, leave_easy_capture=-5, ace_guard_card=-1, ace_guard_settebello=-25,
)
SUITN = ['denari', 'coppe', 'spade', 'bastoni']
RANKN = {1:'A',2:'2',3:'3',4:'4',5:'5',6:'6',7:'7',8:'Fante',9:'Cav',10:'Re'}
def NAME(c): return f"{RANKN[VAL[c]]}-{SUITN[SUIT[c]]}"

# ---- the concrete combos the eval is blind to (match score_deal exactly) ----
def napola_points(pile):
    s = set(pile); n = 0
    for cid in range(10):           # coin ids 0(ace),1(2),2(3),... consecutive from the ace
        if cid in s: n += 1
        else: break
    return n if n >= 3 else 0
def palle_done(pile):
    return 1 if all(s in pile for s in (6, 16, 26, 36)) else 0
def coins(p): return sum(1 for c in p if c < 10)
def strict_prime(p):
    best = [0,0,0,0]
    for c in p:
        if PRIME_BY_VALUE[VAL[c]] > best[SUIT[c]]: best[SUIT[c]] = PRIME_BY_VALUE[VAL[c]]
    return sum(best) if all(best) else 0

# ---- selectors (uniform signature: receive my running pile) ----
def sel_baseline(hand, table, w, diff, ace_rule, my_pile):
    best = None
    for hi, card in enumerate(hand):
        if card is None: continue
        opts, ace_sweep = find_all_captures(VAL[card], table, ace_rule)
        if opts:
            for capset in opts:
                sc = eval_capture(card, capset, table, w, diff, ace_rule, ace_sweep)
                if best is None or sc > best[0]: best = (sc, hi, capset)
        else:
            sc = eval_drop(card, table, w, diff, ace_rule)
            if best is None or sc > best[0]: best = (sc, hi, None)
    return best[1], best[2]

def make_napola_sel(napola_gain, palle_gain=0):
    def sel(hand, table, w, diff, ace_rule, my_pile):
        cur_nap, cur_palle = napola_points(my_pile), palle_done(my_pile)
        best = None
        for hi, card in enumerate(hand):
            if card is None: continue
            opts, ace_sweep = find_all_captures(VAL[card], table, ace_rule)
            if opts:
                for capset in opts:
                    sc = eval_capture(card, capset, table, w, diff, ace_rule, ace_sweep)
                    newpile = my_pile + [table[i] for i in capset] + [card]
                    sc += napola_gain * (napola_points(newpile) - cur_nap)
                    sc += palle_gain * (palle_done(newpile) - cur_palle)
                    if best is None or sc > best[0]: best = (sc, hi, capset)
            else:
                sc = eval_drop(card, table, w, diff, ace_rule)
                if best is None or sc > best[0]: best = (sc, hi, None)
        return best[1], best[2]
    return sel

# ---- stateful runner (each side gets its running pile; from ai_prime.py) ----
def play_deal(selA, selB, rng, leaderA, ace_rule, stats=None):
    deck = list(range(40)); rng.shuffle(deck)
    table = [deck.pop() for _ in range(4)]
    hands=[[],[]]; piles=[[],[]]; scopas=[0,0]; last=None
    turn = 0 if leaderA else 1
    while True:
        if not hands[0] and not hands[1]:
            if not deck: break
            for _ in range(3):
                if deck: hands[0].append(deck.pop())
                if deck: hands[1].append(deck.pop())
        sel = selA if turn == 0 else selB
        hi, capset = sel(hands[turn], table, SHIPPED, 1, ace_rule, piles[turn])
        card = hands[turn].pop(hi)
        if capset is not None:
            ace_sweep = ace_rule and VAL[card]==1 and capset==frozenset(range(len(table))) \
                        and not any(VAL[table[i]]==1 for i in capset) and len(table)>0
            piles[turn] += [table[i] for i in sorted(capset)] + [card]
            table = [table[i] for i in range(len(table)) if i not in capset]
            last = turn
            cl = len(hands[0])+len(hands[1])+len(deck)
            if not table and cl>0 and not ace_sweep: scopas[turn]+=1
        else:
            table.append(card)
        turn ^= 1
    if table and last is not None: piles[last]+=table
    if stats is not None:
        stats['deals'] += 1
        na, nb = napola_points(piles[0]), napola_points(piles[1])
        if na: stats['napA_d']+=1; stats['napA_p']+=na
        if nb: stats['napB_d']+=1; stats['napB_p']+=nb
        ca, cb = coins(piles[0]), coins(piles[1])
        stats['denA'] += ca>cb; stats['denB'] += cb>ca
        pa, pb = strict_prime(piles[0]), strict_prime(piles[1])
        stats['primA'] += pa>pb; stats['primB'] += pb>pa
        stats['carteA'] += len(piles[0])>len(piles[1]); stats['carteB'] += len(piles[1])>len(piles[0])
    return score_deal(piles[0], piles[1], scopas[0], scopas[1])

def play_match(selA, selB, rng, ace_rule, stats=None):
    a=b=0; leaderA = rng.random()<0.5
    while True:
        da,db = play_deal(selA, selB, rng, leaderA, ace_rule, stats)
        a+=da; b+=db; leaderA = not leaderA
        if (a>=11 or b>=11) and a!=b: return 1 if a>b else -1

def winrate(selA, selB, n, seed, ace_rule=True, stats=None):
    rng = random.Random(seed); wins=0
    for i in range(n):
        if i % 2 == 0:
            r = play_match(selA, selB, rng, ace_rule, stats); wins += r>0
        else:
            r = play_match(selB, selA, rng, ace_rule, None);  wins += r<0   # A in seat 2
    return wins/n

# ================================ experiments ================================
print("="*72); print("SANITY: baseline vs baseline (must be ~0.50)"); print("="*72)
print(f"  baseline vs baseline (4000): {winrate(sel_baseline, sel_baseline, 4000, 42):.3f}")

print(); print("="*72)
print("GRID: napola-aware vs shipped (match win rate, 6000 matches, ace on)")
print("  napola_gain = eval points added per napola-point a capture locks in / extends")
print("  (settebello = +35 for 1 pt, so ~30-35/pt is 'priced like the settebello')")
print("="*72)
res=[]
for g in (8, 15, 25, 35, 45, 60, 90):
    wr = winrate(make_napola_sel(g), sel_baseline, 6000, 2024)
    res.append((wr,g)); print(f"  napola_gain={g:<3} -> {wr:.3f}  ({(wr-0.5)*100:+.1f}pts)")
res.sort(reverse=True); bwr,bg = res[0]
print(f"\n  BEST: napola_gain={bg} -> {bwr:.3f}")

print(); print("="*72)
print(f"VALIDATION of napola_gain={bg}: 24000 matches + point split"); print("="*72)
st=dict(deals=0,napA_d=0,napB_d=0,napA_p=0,napB_p=0,denA=0,denB=0,primA=0,primB=0,carteA=0,carteB=0)
wr = winrate(make_napola_sel(bg), sel_baseline, 24000, 9999, stats=st)
se=(0.25/24000)**0.5
print(f"  napola-aware (A) vs shipped (B): {wr:.4f}  (+/-{1.96*se:.4f} 95% CI)  "
      f"=> {'SIGNIFICANT win' if wr-0.5>1.96*se else 'SIGNIFICANT loss' if 0.5-wr>1.96*se else 'within noise'}")
d=st['deals']
print(f"  over {d} sampled deals (napola-aware=A vs shipped=B):")
print(f"    napola scored:  A {100*st['napA_d']/d:.2f}% of deals ({st['napA_p']/d:.4f} pts/deal)   "
      f"B {100*st['napB_d']/d:.2f}% ({st['napB_p']/d:.4f} pts/deal)")
print(f"    denari point:   A {100*st['denA']/d:.1f}%   B {100*st['denB']/d:.1f}%   (cannibalised?)")
print(f"    primiera point: A {100*st['primA']/d:.1f}%   B {100*st['primB']/d:.1f}%")
print(f"    carte point:    A {100*st['carteA']/d:.1f}%   B {100*st['carteB']/d:.1f}%")

print(); print("="*72)
print("PALLE (all four 7s, +1): does a small palle-gain add anything on top?"); print("="*72)
for pg in (0, 6, 12, 24):
    wr = winrate(make_napola_sel(bg, pg), sel_baseline, 8000, 555)
    print(f"  napola_gain={bg} palle_gain={pg:<3} -> {wr:.3f}  ({(wr-0.5)*100:+.1f}pts)")

print(); print("="*72)
print("TONY'S CASE: pile holds A+2 of coins; table has the 3-of-coins AND a 7;")
print("  hand can capture either. Baseline grabs the 7 (+12); napola-aware should take the coin.")
print("="*72)
pile=[0,1]                    # A-denari, 2-denari already captured (napola needs the 3)
table=[2, 36]                 # 3-denari (completes napola)  +  7-bastoni
hand=[12, 26]                 # 3-coppe (captures 3-denari) , 7-spade (captures 7-bastoni)
for label, sel in (("BASELINE (shipped)", sel_baseline), (f"NAPOLA-aware (g={bg})", make_napola_sel(bg))):
    hi, cap = sel(hand, table, SHIPPED, 1, True, pile)
    capd = [table[i] for i in cap] if cap else []
    print(f"  {label:22}: plays {NAME(hand[hi]):9} -> captures {[NAME(c) for c in capd]}")
print(f"  (pile after the napola-aware play would be A,2,3 of coins = napola, +3 points)")
