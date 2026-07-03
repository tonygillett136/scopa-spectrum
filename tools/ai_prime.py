#!/usr/bin/env python3
"""Prototype: PRIMIERA / suit-completion awareness for the Scopa AI.
[ARCHIVED experiment -- carries its own weight copy from its day; for CURRENT shipped
 weights import tools/shipped_weights.py, do not trust weight literals below.]

The shipped 1-ply evaluator is STATELESS (sees only hand+table). Primiera is decided
in ~95% of deals but the AI is blind to it beyond fixed per-card bonuses. This adds a
pile-aware term to CAPTURE scoring:
  - suit-unlock: capturing a card in a suit my pile is currently VOID in is huge
    (a missing suit zeroes primiera entirely);
  - prime-gain:  capturing a card that raises my best prime-card in its suit.

Measured head-to-head vs the SHIPPED weights in the faithful host-mirror.
Run: python tools/ai_prime.py
"""
import random
import ai_tune
from ai_tune import (VAL, SUIT, PRIME_BY_VALUE, find_all_captures,
                     eval_capture, eval_drop, score_deal)

# shipped weights (from scopa.asm)
SHIPPED = dict(
    card_count=3, denari=5, settebello_cap=35, seven=12, six=8, ace=6, sweep=50,
    drop_settebello=-40, drop_seven=-5, drop_six=-5, drop_denari=-4, drop_face=3,
    leave_sweep_risk=-9, leave_easy_capture=-5, ace_guard_card=-1, ace_guard_settebello=-25,
)

# ---------------- primiera helpers ----------------
def prime_state(pile):
    """-> (sum of best prime-card per suit, number of suits present)."""
    best = [0, 0, 0, 0]
    for c in pile:
        pv = PRIME_BY_VALUE[VAL[c]]
        s = SUIT[c]
        if pv > best[s]:
            best[s] = pv
    return sum(best), sum(1 for b in best if b > 0)

# ---------------- selectors (uniform signature: receive my pile) ----------------
def sel_baseline(hand, table, w, diff, ace_rule, my_pile):
    """The shipped stateless 1-ply evaluator (pile ignored)."""
    best = None
    for hi, card in enumerate(hand):
        if card is None:
            continue
        opts, ace_sweep = find_all_captures(VAL[card], table, ace_rule)
        if opts:
            for capset in opts:
                sc = eval_capture(card, capset, table, w, diff, ace_rule, ace_sweep)
                if best is None or sc > best[0]:
                    best = (sc, hi, capset)
        else:
            sc = eval_drop(card, table, w, diff, ace_rule)
            if best is None or sc > best[0]:
                best = (sc, hi, None)
    return best[1], best[2]

def make_prime_sel(prime_gain, suit_unlock):
    def sel(hand, table, w, diff, ace_rule, my_pile):
        cur_sum, cur_suits = prime_state(my_pile)
        best = None
        for hi, card in enumerate(hand):
            if card is None:
                continue
            opts, ace_sweep = find_all_captures(VAL[card], table, ace_rule)
            if opts:
                for capset in opts:
                    sc = eval_capture(card, capset, table, w, diff, ace_rule, ace_sweep)
                    captured = [table[i] for i in capset] + [card]
                    new_sum, new_suits = prime_state(my_pile + captured)
                    sc += prime_gain * (new_sum - cur_sum)
                    sc += suit_unlock * (new_suits - cur_suits)
                    if best is None or sc > best[0]:
                        best = (sc, hi, capset)
            else:
                sc = eval_drop(card, table, w, diff, ace_rule)
                if best is None or sc > best[0]:
                    best = (sc, hi, None)
        return best[1], best[2]
    return sel

# ---------------- stateful game/match runner ----------------
def play_deal(wA, wB, selA, selB, rng, leaderA, ace_rule, stats=None):
    deck = list(range(40)); rng.shuffle(deck)
    table = [deck.pop() for _ in range(4)]
    hands = [[], []]; piles = [[], []]; scopas = [0, 0]; last = None
    turn = 0 if leaderA else 1
    while True:
        if not hands[0] and not hands[1]:
            if not deck:
                break
            for _ in range(3):
                if deck: hands[0].append(deck.pop())
                if deck: hands[1].append(deck.pop())
        w, sel = (wA, selA) if turn == 0 else (wB, selB)
        hi, capset = sel(hands[turn], table, w, 1, ace_rule, piles[turn])
        card = hands[turn].pop(hi)
        if capset is not None:
            ace_sweep = ace_rule and VAL[card] == 1 and capset == frozenset(range(len(table))) \
                        and not any(VAL[table[i]] == 1 for i in capset) and len(table) > 0
            piles[turn] += [table[i] for i in sorted(capset)] + [card]
            table = [table[i] for i in range(len(table)) if i not in capset]
            last = turn
            cl = len(hands[0]) + len(hands[1]) + len(deck)
            if not table and cl > 0 and not ace_sweep:
                scopas[turn] += 1
        else:
            table.append(card)
        turn ^= 1
    if table and last is not None:
        piles[last] += table
    if stats is not None:
        def coins(p): return sum(1 for c in p if c < 10)
        ps, _ = prime_state(piles[0]); os_, _ = prime_state(piles[1])
        # need-all-4-suits rule already folded into prime_state via missing suit = 0 contribution,
        # but a missing suit must zero the whole prime -> recompute strictly:
        def strict_prime(p):
            s, n = prime_state(p)
            return s if n == 4 else 0
        ps, os_ = strict_prime(piles[0]), strict_prime(piles[1])
        if ps > os_: stats['primA'] += 1
        elif os_ > ps: stats['primB'] += 1
        else: stats['primD'] += 1
        if coins(piles[0]) > coins(piles[1]): stats['denA'] += 1
        elif coins(piles[1]) > coins(piles[0]): stats['denB'] += 1
        else: stats['denD'] += 1
        stats['deals'] += 1
    return score_deal(piles[0], piles[1], scopas[0], scopas[1])

def play_match(wA, wB, selA, selB, rng, ace_rule, stats=None):
    a = b = 0; leaderA = rng.random() < 0.5
    while True:
        da, db = play_deal(wA, wB, selA, selB, rng, leaderA, ace_rule, stats)
        a += da; b += db; leaderA = not leaderA
        if (a >= 11 or b >= 11) and a != b:
            return 1 if a > b else -1

def winrate(selA, selB, n, seed, ace_rule=True, wA=SHIPPED, wB=SHIPPED, stats=None):
    """A's match win fraction over n matches; A and B swap seats each match.
    stats (if given) accumulates A-vs-B point tallies from A's perspective."""
    rng = random.Random(seed); wins = 0
    for i in range(n):
        if i % 2 == 0:
            r = play_match(wA, wB, selA, selB, rng, ace_rule, stats)
            wins += 1 if r > 0 else 0
        else:
            # A plays second seat; don't collect swapped stats (would flip perspective)
            r = play_match(wB, wA, selB, selA, rng, ace_rule, None)
            wins += 1 if r < 0 else 0
    return wins / n


print("=" * 72)
print("SANITY: baseline-vs-baseline should be ~0.50 (stateful runner self-check)")
print("=" * 72)
print(f"  baseline vs baseline (4000): {winrate(sel_baseline, sel_baseline, 4000, 42):.3f}")

print()
print("=" * 72)
print("GRID SEARCH: prime-aware vs shipped baseline (match win rate, 4000 matches)")
print("  prime_gain = weight per unit of best-prime gained")
print("  suit_unlock = bonus for capturing into a void suit")
print("=" * 72)
results = []
for pg in (0.3, 0.6, 1.0, 1.5):
    for su in (4, 8, 14, 22):
        sel = make_prime_sel(pg, su)
        wr = winrate(sel, sel_baseline, 4000, 2024)
        results.append((wr, pg, su))
        print(f"  prime_gain={pg:<4} suit_unlock={su:<3} -> {wr:.3f}  ({(wr-0.5)*100:+.1f}pts)")
results.sort(reverse=True)
bwr, bpg, bsu = results[0]
print(f"\n  BEST: prime_gain={bpg}, suit_unlock={bsu} -> {bwr:.3f}")

print()
print("=" * 72)
print(f"VALIDATION of best (prime_gain={bpg}, suit_unlock={bsu}), 16000 matches + point split")
print("=" * 72)
best_sel = make_prime_sel(bpg, bsu)
stats = dict(primA=0, primB=0, primD=0, denA=0, denB=0, denD=0, deals=0)
wr = winrate(best_sel, sel_baseline, 16000, 9999, stats=stats)
se = (0.25 / 16000) ** 0.5
print(f"  prime-aware vs shipped: {wr:.4f}  (+/- {1.96*se:.4f} 95% CI)  "
      f"=> {'SIGNIFICANT' if abs(wr-0.5) > 1.96*se else 'within noise'}")
d = stats['deals']
print(f"\n  point-split over {d} decided deals (prime-aware = A, shipped = B):")
print(f"    primiera: A won {100*stats['primA']/d:.1f}%  B won {100*stats['primB']/d:.1f}%  "
      f"draw {100*stats['primD']/d:.1f}%")
print(f"    denari:   A won {100*stats['denA']/d:.1f}%  B won {100*stats['denB']/d:.1f}%  "
      f"draw {100*stats['denD']/d:.1f}%")

print()
print("=" * 72)
print("ISOLATION: pure SUIT-COMPLETION only (prime_gain=0), various unlock weights")
print("=" * 72)
for su in (6, 10, 16, 25, 40):
    sel = make_prime_sel(0.0, su)
    wr = winrate(sel, sel_baseline, 8000, 7777)
    print(f"  suit_unlock={su:<3} (no prime_gain) -> {wr:.3f}  ({(wr-0.5)*100:+.1f}pts)")

print()
print("=" * 72)
print("PAIRED-LEAD: when DROPPING, prefer a card whose rank you hold a duplicate of")
print("=" * 72)
def make_paired_sel(paired_bonus):
    def sel(hand, table, w, diff, ace_rule, my_pile):
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
                # bonus if another hand card shares this rank (re-capture insurance)
                if any(j != hi and c is not None and VAL[c] == VAL[card]
                       for j, c in enumerate(hand)):
                    sc += paired_bonus
                if best is None or sc > best[0]: best = (sc, hi, None)
        return best[1], best[2]
    return sel
for pb in (3, 6, 10, 16):
    wr = winrate(make_paired_sel(pb), sel_baseline, 8000, 4242)
    print(f"  paired_bonus={pb:<3} -> {wr:.3f}  ({(wr-0.5)*100:+.1f}pts)")
