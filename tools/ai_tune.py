#!/usr/bin/env python3
"""Host-side Scopa simulator + AI weight tuner + 2-ply experiment.

Mirrors the Z80 engine (scopa.asm) exactly so tuned weights transfer:
  card id 0..39: value=id%10+1, suit=id//10 (0 denari/coins,1 coppe,2 spade,3 bastoni);
  settebello=id6. Single-card capture priority, else subset-sum. Capture if the played
  card matches; the player chooses which card. Scopa on table-clear except the deal's last
  card. Match to 11. Scoring: carte/denari/settebello/primiera(all 4 suits)/scope + napola
  + palle del cane. The AI is the 1-ply weighted evaluator from aiSelectPlay/EvalCapture/
  EvalDrop/EvalSafety/CardBonus.

Usage: python tools/ai_tune.py [selftest|optimise|twoply|all] [matches]
"""
import sys, random
from itertools import combinations

VAL = [i % 10 + 1 for i in range(40)]            # card -> value 1..10
SUIT = [i // 10 for i in range(40)]              # card -> suit 0..3
PRIME_BY_VALUE = {1:16,2:12,3:13,4:14,5:15,6:18,7:21,8:10,9:10,10:10}

# ---- HISTORICAL pre-tune baseline (what the optimiser measured against) ----
# NOT the shipped weights! The tuned values that actually ship live in scopa.asm and are
# mirrored in tools/shipped_weights.py -- import from there for anything current.
W0 = dict(
    card_count=2, denari=5, settebello_cap=35, seven=15, six=8, ace=6, sweep=50,
    drop_settebello=-40, drop_seven=-12, drop_six=-6, drop_denari=-4, drop_face=3,
    leave_sweep_risk=-20, leave_easy_capture=-2,
    ace_guard_card=-1, ace_guard_settebello=-25,   # only used when ace_rule on
)
TUNE_KEYS = ['card_count','denari','settebello_cap','seven','six','ace','sweep',
             'drop_settebello','drop_seven','drop_six','drop_denari','drop_face',
             'leave_sweep_risk','leave_easy_capture']

# ---------------- rules ----------------
def find_all_captures(val, table, ace_rule):
    """-> (list of capsets [each a frozenset of table indices], ace_sweep_bool)."""
    n = len(table)
    if n == 0:
        return [], False
    if ace_rule and val == 1 and not any(VAL[c] == 1 for c in table):
        return [frozenset(range(n))], True            # asso piglia tutto: sweep all
    singles = [i for i in range(n) if VAL[table[i]] == val]
    if singles:
        return [frozenset((i,)) for i in singles], False   # single-card priority
    opts = []
    for r in range(2, n + 1):
        for combo in combinations(range(n), r):
            if sum(VAL[table[i]] for i in combo) == val:
                opts.append(frozenset(combo))
    return opts, False

# ---------------- evaluator (mirrors the Z80) ----------------
def card_bonus(card, w):
    s = 0
    if card < 10: s += w['denari']
    if card == 6: s += w['settebello_cap']
    v = VAL[card]
    if v == 7: s += w['seven']
    elif v == 6: s += w['six']
    elif v == 1: s += w['ace']
    return s

def eval_safety(leftover, w, ace_rule):
    if not leftover: return 0
    s = 0
    if sum(VAL[c] for c in leftover) <= 10: s += w['leave_sweep_risk']
    s += w['leave_easy_capture'] * len(set(VAL[c] for c in leftover))
    if ace_rule:
        if any(VAL[c] == 1 for c in leftover): return s     # sweep-proof
        s += w['ace_guard_card'] * len(leftover)
        if 6 in leftover: s += w['ace_guard_settebello']
    return s

def eval_capture(card, capset, table, w, difficulty, ace_rule, ace_sweep):
    captured = [table[i] for i in capset]
    s = (len(captured) + 1) * w['card_count']
    for c in captured: s += card_bonus(c, w)
    s += card_bonus(card, w)
    leftover = [table[i] for i in range(len(table)) if i not in capset]
    if not leftover:
        if not ace_sweep: s += w['sweep']
    elif difficulty > 0:
        s += eval_safety(leftover, w, ace_rule)
    return s

def eval_drop(card, table, w, difficulty, ace_rule):
    v = VAL[card]; s = 0
    if card == 6: s += w['drop_settebello']
    elif v == 7: s += w['drop_seven']
    elif v == 6: s += w['drop_six']
    if card < 10: s += w['drop_denari']
    if v >= 8: s += w['drop_face']
    if difficulty > 0: s += eval_safety(table + [card], w, ace_rule)
    return s

def ai_select(hand, table, w, difficulty=1, ace_rule=False):
    """-> (hand_index, capset_or_None). 1-ply greedy, first-found wins ties (= Z80)."""
    best = None
    for hi, card in enumerate(hand):
        if card is None: continue
        opts, ace_sweep = find_all_captures(VAL[card], table, ace_rule)
        if opts:
            for capset in opts:
                sc = eval_capture(card, capset, table, w, difficulty, ace_rule, ace_sweep)
                if best is None or sc > best[0]:
                    best = (sc, hi, capset)
        else:
            sc = eval_drop(card, table, w, difficulty, ace_rule)
            if best is None or sc > best[0]:
                best = (sc, hi, None)
    return best[1], best[2]

# ---------------- 2-ply (paranoid lookahead) ----------------
def opponent_threat(table, w):
    """Best capture value an opponent could extract from `table` with one ideal card
    (max over played values 1..10), scored by the same capture reward (no safety)."""
    if not table: return 0
    best = 0
    for v in range(1, 11):
        opts, _ = find_all_captures(v, table, False)
        for capset in opts:
            captured = [table[i] for i in capset]
            # a phantom card of value v captures `captured`; score its gain
            sc = (len(captured) + 1) * w['card_count']
            for c in captured: sc += card_bonus(c, w)
            if len(captured) == len(table): sc += w['sweep']   # they'd sweep -> scopa
            if sc > best: best = sc
    return best

def ai_select_2ply(hand, table, w, difficulty=1, ace_rule=False, discount=0.5):
    """1-ply capture/drop value minus discount * the opponent's best reply to the
    resulting table. Replaces the hand-coded safety with a computed threat."""
    best = None
    for hi, card in enumerate(hand):
        if card is None: continue
        opts, ace_sweep = find_all_captures(VAL[card], table, ace_rule)
        if opts:
            for capset in opts:
                captured = [table[i] for i in capset]
                imm = (len(captured) + 1) * w['card_count']
                for c in captured: imm += card_bonus(c, w)
                imm += card_bonus(card, w)
                newtab = [table[i] for i in range(len(table)) if i not in capset]
                if not newtab and not ace_sweep: imm += w['sweep']
                sc = imm - discount * opponent_threat(newtab, w)
                if best is None or sc > best[0]: best = (sc, hi, capset)
        else:
            v = VAL[card]; imm = 0
            if card == 6: imm += w['drop_settebello']
            elif v == 7: imm += w['drop_seven']
            elif v == 6: imm += w['drop_six']
            if card < 10: imm += w['drop_denari']
            if v >= 8: imm += w['drop_face']
            newtab = table + [card]
            sc = imm - discount * opponent_threat(newtab, w)
            if best is None or sc > best[0]: best = (sc, hi, None)
    return best[1], best[2]

# ---------------- scoring ----------------
def score_deal(pile_p, pile_o, scopa_p, scopa_o):
    def coins(p):  return sum(1 for c in p if c < 10)
    def primiera(p):
        best = {0:0,1:0,2:0,3:0}
        for c in p: best[SUIT[c]] = max(best[SUIT[c]], PRIME_BY_VALUE[VAL[c]])
        if any(v == 0 for v in best.values()): return 0   # need all 4 suits
        return sum(best.values())
    def napola(p):
        n = 0
        for cid in range(10):
            if cid in p: n += 1
            else: break
        return n if n >= 3 else 0
    pp = oo = 0
    if len(pile_p) > len(pile_o): pp += 1
    elif len(pile_o) > len(pile_p): oo += 1
    if coins(pile_p) > coins(pile_o): pp += 1
    elif coins(pile_o) > coins(pile_p): oo += 1
    if 6 in pile_p: pp += 1
    else: oo += 1
    prp, pro = primiera(pile_p), primiera(pile_o)
    if prp > pro: pp += 1
    elif pro > prp: oo += 1
    pp += scopa_p; oo += scopa_o
    pp += napola(pile_p); oo += napola(pile_o)
    if all(s in pile_p for s in (6,16,26,36)): pp += 1     # palle del cane
    if all(s in pile_o for s in (6,16,26,36)): oo += 1
    return pp, oo

# ---------------- game / match ----------------
def play_deal(wA, wB, selA, selB, rng, leaderA, ace_rule):
    """One full deal. wA/selA = player A's weights+selector. Returns (ptsA, ptsB)."""
    deck = list(range(40)); rng.shuffle(deck)
    table = [deck.pop() for _ in range(4)]
    hands = [[], []]                          # 0 = A, 1 = B
    piles = [[], []]
    scopas = [0, 0]
    last_cap = None
    turn = 0 if leaderA else 1
    while True:
        if not hands[0] and not hands[1]:
            if not deck:
                break
            for _ in range(3):
                if deck: hands[0].append(deck.pop())
                if deck: hands[1].append(deck.pop())
        w, sel = (wA, selA) if turn == 0 else (wB, selB)
        hi, capset = sel(hands[turn], table, w, 1, ace_rule)
        card = hands[turn].pop(hi)
        if capset is not None:
            ace_sweep = ace_rule and VAL[card] == 1 and capset == frozenset(range(len(table))) \
                        and not any(VAL[table[i]] == 1 for i in capset) and len(table) > 0
            captured = [table[i] for i in sorted(capset)]
            piles[turn].extend(captured); piles[turn].append(card)
            table = [table[i] for i in range(len(table)) if i not in capset]
            last_cap = turn
            cards_left = len(hands[0]) + len(hands[1]) + len(deck)
            if not table and cards_left > 0 and not ace_sweep:
                scopas[turn] += 1
        else:
            table.append(card)
        turn ^= 1
    if table and last_cap is not None:
        piles[last_cap].extend(table)
    pp, oo = score_deal(piles[0], piles[1], scopas[0], scopas[1])
    return pp, oo

def play_match(wA, wB, selA, selB, rng, ace_rule=False):
    """Match to 11. Returns +1 if A wins, -1 if B wins."""
    a = b = 0; leaderA = rng.random() < 0.5
    while True:
        da, db = play_deal(wA, wB, selA, selB, rng, leaderA, ace_rule)
        a += da; b += db; leaderA = not leaderA
        if (a >= 11 or b >= 11) and a != b:
            return 1 if a > b else -1

def winrate(wA, wB, n, seed, selA=ai_select, selB=ai_select, ace_rule=False):
    """A's match win fraction over n matches (A and B swap sides each match)."""
    rng = random.Random(seed); wins = 0
    for i in range(n):
        if i % 2 == 0:
            r = play_match(wA, wB, selA, selB, rng, ace_rule)
            wins += 1 if r > 0 else 0
        else:
            r = play_match(wB, wA, selB, selA, rng, ace_rule)   # A plays second seat
            wins += 1 if r < 0 else 0
    return wins / n

# ---------------- optimiser (coordinate ascent, re-baselined) ----------------
def optimise(budget_matches=800, passes=2, rebaselines=2):
    cur = dict(W0); baseline = dict(W0)
    seed = 1000
    for rb in range(rebaselines):
        for p in range(passes):
            for k in TUNE_KEYS:
                v = cur[k]; step = max(1, abs(v) // 4)
                cands = sorted(set([v-2*step, v-step, v, v+step, v+2*step]))
                # common random numbers: same decks for every candidate of THIS weight
                wseed = seed; seed += 1
                best_v, best_wr = v, -1
                for cv in cands:
                    trial = dict(cur); trial[k] = cv
                    wr = winrate(trial, baseline, budget_matches, wseed)
                    # tie-break toward the incumbent value to resist noise
                    if wr > best_wr + 1e-9 or (abs(wr - best_wr) <= 1e-9 and cv == v):
                        best_wr, best_v = wr, cv
                cur[k] = best_v
            print(f"  [rebaseline {rb} pass {p}] vs original winrate "
                  f"{winrate(cur, W0, budget_matches*3, 777):.3f}", flush=True)
        baseline = dict(cur)                  # iterated hill-climb
    return cur

# ---------------- reference opponents ----------------
def sel_random(hand, table, w, difficulty=1, ace_rule=False):
    idxs = [i for i, c in enumerate(hand) if c is not None]
    hi = w['_rng'].choice(idxs)
    opts, _ = find_all_captures(VAL[hand[hi]], table, ace_rule)
    return hi, (opts[0] if opts else None)

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'
    N = int(sys.argv[2]) if len(sys.argv) > 2 else None

    if mode in ('selftest', 'all'):
        print("== selftest ==")
        # Z80 TESTMODE-19 scenario score (medium, ace_rule on): expect -20
        s = eval_capture(13, frozenset({0}), [3, 6, 16], W0, 1, True, False)
        print(f"  eval_capture(4c capturing 4d, leaving [settebello,7c], ace_rule) = {s}  (Z80=-20)")
        # ace-sweep score (TESTMODE 18): expect 44
        s2 = eval_capture(0, frozenset({0,1,2}), [4,16,9], W0, 1, True, True)
        print(f"  ace-sweep score = {s2}  (Z80=44)")
        # sanity: a deal runs and scores total <= a few points each
        rng = random.Random(1)
        pp, oo = play_deal(W0, W0, ai_select, ai_select, rng, True, False)
        print(f"  sample deal points: A={pp} B={oo}  (should be small ints, sum>=4)")
        wr = winrate(W0, W0, 400, 42)
        print(f"  mirror match winrate W0 vs W0 = {wr:.3f}  (should be ~0.50)")

    if mode in ('optimise', 'all'):
        print("== optimise (coordinate ascent vs current weights) ==")
        bud = N or 300
        tuned = optimise(budget_matches=bud)
        print("  TUNED weights:")
        for k in TUNE_KEYS:
            mark = '' if tuned[k] == W0[k] else f'  (was {W0[k]})'
            print(f"    {k:22} {tuned[k]}{mark}")
        print("  validation (5000 matches each):")
        print(f"    tuned vs current  = {winrate(tuned, W0, 5000, 9001):.3f}")
        rA = dict(W0); rA['_rng'] = random.Random(7)
        print(f"    tuned vs random   = {winrate(tuned, rA, 2000, 9002, ai_select, sel_random):.3f}")
        print(f"    current vs random = {winrate(W0, rA, 2000, 9003, ai_select, sel_random):.3f}")
        # emit the tuned dict for baking
        print("  TUNED_DICT =", {k: tuned[k] for k in TUNE_KEYS})

    if mode in ('twoply', 'all'):
        print("== 2-ply experiment (paranoid lookahead vs 1-ply, current weights) ==")
        for disc in (0.3, 0.5, 0.7):
            sel2 = lambda h, t, w, d=1, a=False, _dc=disc: ai_select_2ply(h, t, w, d, a, _dc)
            wr = winrate(W0, W0, N or 2000, 5555, sel2, ai_select)
            print(f"    2-ply(discount={disc}) vs 1-ply = {wr:.3f}")

if __name__ == '__main__':
    main()
