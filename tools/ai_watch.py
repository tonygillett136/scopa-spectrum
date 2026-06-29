#!/usr/bin/env python3
"""Self-play 'watchdog' for the Scopa AI.

Plays the SHIPPED Esperto mid-game evaluator against itself for many games (like the demo),
logs every mid-game decision with all its alternatives, and runs principle-based oddity
detectors -- "a strong player would frown at this" -- to surface plays worth investigating.

This is a faithful host port of scopa.asm's aiSelectPlay / EvalCapture / EvalSafety / EvalDrop /
CardBonus / NapolaBonus / ThreatLive (shipped weights, verified against the asm 2026-06-29):
  card_count x3; coin +5; settebello(id6) +35; 7 +12; 6 +8; ace +6; sweep +50; napola run-delta x35;
  drop: settebello -40, 7 -5, 6 -5, coin -4, face(>=8) +3; safety: sum<=10 -> -9, each matchable
  value -> -5, both gated by ThreatLive (Esperto: a threat is dead if all 4 of that value are seen,
  seen = table + own hand + every played card -> unseen = opp hand + deck); asso-piglia-tutto guard
  only when the rule is on. Endgame (deck empty) is exact minimax in the ROM (optimal) -> the heuristic,
  and thus any oddity, lives while the deck still has cards, so we only FLAG deck-not-empty decisions.

Flagged boards are written to scratchpad/odd_boards.json for replay through the real Z80 (ai_zx_check.py).

Usage:  python tools/ai_watch.py [matches] [seed]      (default 3000 matches, seed 1)
"""
import sys, os, json, random
from itertools import combinations
from collections import defaultdict

VAL  = [i % 10 + 1 for i in range(40)]
SUIT = [i // 10 for i in range(40)]
SETTEBELLO = 6
SN = ['denari', 'coppe', 'spade', 'bastoni']
RN = {1:'A',2:'2',3:'3',4:'4',5:'5',6:'6',7:'7',8:'fante',9:'cavallo',10:'re'}
def nm(c): return f"{RN[VAL[c]]} di {SN[SUIT[c]]}"
def names(cs): return [nm(c) for c in cs]
def is_coin(c): return c < 10

W = dict(card_count=3, coin=5, settebello=35, seven=12, six=8, ace=6, sweep=50,
         drop_settebello=-40, drop_seven=-5, drop_six=-5, drop_coin=-4, drop_face=3,
         sweep_risk=-9, easy_capture=-5, ace_guard=-1, ace_guard_sette=-25, napola=35)

# ---------------- rules ----------------
def find_captures(val, table, ace_rule=False):
    """-> (list of capsets [tuple of table indices], ace_sweep_bool). Mirrors findAllCaptures."""
    n = len(table)
    if n == 0: return [], False
    if ace_rule and val == 1 and not any(VAL[c] == 1 for c in table):
        return [tuple(range(n))], True
    singles = [(i,) for i in range(n) if VAL[table[i]] == val]
    if singles: return singles, False
    opts = []
    for r in range(2, n + 1):
        for combo in combinations(range(n), r):
            if sum(VAL[table[i]] for i in combo) == val:
                opts.append(combo)
    return opts, False

# ---------------- evaluator (faithful to scopa.asm) ----------------
def card_bonus(c):
    s = 0
    if is_coin(c): s += W['coin']
    if c == SETTEBELLO: s += W['settebello']
    v = VAL[c]
    if v == 7: s += W['seven']
    elif v == 6: s += W['six']
    elif v == 1: s += W['ace']
    return s

def napola_run(mask):
    n = 0
    for b in range(10):
        if mask & (1 << b): n += 1
        else: break
    return n if n >= 3 else 0

def napola_bonus(played, captured, pile):
    mask = 0
    for c in pile:
        if is_coin(c): mask |= 1 << c            # coin ids are 0..9 == their bit
    before = napola_run(mask)
    if is_coin(played): mask |= 1 << played
    for c in captured:
        if is_coin(c): mask |= 1 << c
    delta = napola_run(mask) - before
    return delta * W['napola'] if delta > 0 else 0

def eval_safety(tmptable, unseen, esperto, ace_rule):
    """tmptable = leftover table; unseen[v] = #unseen cards of value v (1..10). Mirrors EvalSafety."""
    if not tmptable: return 0
    def live(v): return unseen[v] > 0 if esperto else True
    s = 0
    tot = sum(VAL[c] for c in tmptable)
    if tot <= 10 and live(tot): s += W['sweep_risk']
    present = set(VAL[c] for c in tmptable)
    for d in range(1, 11):
        if d in present and live(d): s += W['easy_capture']
    if ace_rule:
        if esperto and unseen[1] == 0: return s              # opp can't ace-sweep
        if any(VAL[c] == 1 for c in tmptable): return s       # ace on table -> sweep-proof
        s += W['ace_guard'] * len(tmptable)
        if SETTEBELLO in tmptable: s += W['ace_guard_sette']
    return s

def eval_capture(played, capset, table, pile, unseen, esperto, ace_rule, ace_sweep):
    captured = [table[i] for i in capset]
    s = (len(captured) + 1) * W['card_count']
    for c in captured: s += card_bonus(c)
    s += card_bonus(played)
    s += napola_bonus(played, captured, pile)
    leftover = [table[i] for i in range(len(table)) if i not in capset]
    if not leftover:
        if not ace_sweep: s += W['sweep']
    elif esperto or True:        # EASY(diff 0) skips safety; demo is Esperto so safety on
        s += eval_safety(leftover, unseen, esperto, ace_rule)
    return s

def eval_drop(played, table, unseen, esperto, ace_rule):
    v = VAL[played]; s = 0
    if played == SETTEBELLO: s += W['drop_settebello']
    elif v == 7: s += W['drop_seven']
    elif v == 6: s += W['drop_six']
    if is_coin(played): s += W['drop_coin']
    if v >= 8: s += W['drop_face']
    s += eval_safety(table + [played], unseen, esperto, ace_rule)
    return s

def ai_select(hand, table, pile, unseen, esperto=True, ace_rule=False):
    """-> dict: chosen (slot, capset|None, score) + the full ranked option list. First wins ties (=Z80)."""
    opts = []      # (score, slot, capset_or_None, ace_sweep)
    for slot, card in enumerate(hand):
        if card is None: continue
        caps, ace_sweep = find_captures(VAL[card], table, ace_rule)
        if caps:
            for cs in caps:
                sc = eval_capture(card, cs, table, pile, unseen, esperto, ace_rule, ace_sweep)
                opts.append((sc, slot, cs, ace_sweep))
        else:
            sc = eval_drop(card, table, unseen, esperto, ace_rule)
            opts.append((sc, slot, None, False))
    best = None
    for o in opts:                       # first-found max (strict >) == ConsiderBest
        if best is None or o[0] > best[0]: best = o
    return dict(score=best[0], slot=best[1], capset=best[2], ace_sweep=best[3], options=opts)

# ---------------- oddity detectors ----------------
# Primary signal = DOMINANCE: a move is unambiguously odd if another legal move is >= on every
# fundamental we care about (cards, coins, settebello, 7s, scopa, napola points) and no worse on the
# two "bad" axes (hands the opponent a scopa; leaves the settebello on the table) -- and strictly better
# somewhere. A dominated choice can't be justified by any Scopa principle, so it's a real candidate.
# Soft principle tags are kept as secondary context.
DOM_GOOD = ('cards', 'coins', 'sette', 'prim', 'scopa', 'napola')
DOM_BAD  = ('opp_scopa', 'leaves_sette')

def primiera_raw(cards):
    best = {0: 0, 1: 0, 2: 0, 3: 0}
    for c in cards: best[SUIT[c]] = max(best[SUIT[c]], PRIME[VAL[c]])
    return sum(best.values())

def move_features(slot, capset, hand, table, pile, unseen, last_card):
    played = hand[slot]
    if capset is None:                          # a drop banks nothing; the played card is exposed
        banked, left = [], table + [played]
    else:                                       # a capture banks the captured cards AND the played card
        captured = [table[i] for i in capset]
        banked = captured + [played]
        left = [table[i] for i in range(len(table)) if i not in capset]
    def opp_sweep(L):
        if not L: return 0
        if len(L) == 1: return 1 if unseen[VAL[L[0]]] > 0 else 0
        s = sum(VAL[c] for c in L); return 1 if (s <= 10 and unseen[s] > 0) else 0
    return dict(
        cards=len(banked),
        coins=sum(1 for c in banked if is_coin(c)),
        sette=1 if SETTEBELLO in banked else 0,
        prim=primiera_raw(pile + banked) - primiera_raw(pile),   # primiera contribution (handles 7>6>ace)
        scopa=1 if (capset is not None and not left and not last_card) else 0,
        napola=napola_bonus(played, [] if capset is None else [table[i] for i in capset], pile) // W['napola'],
        opp_scopa=opp_sweep(left),
        leaves_sette=1 if SETTEBELLO in left else 0,
    )

def dominates(B, A):
    if not (all(B[k] >= A[k] for k in DOM_GOOD) and all(B[k] <= A[k] for k in DOM_BAD)):
        return False
    return any(B[k] > A[k] for k in DOM_GOOD) or any(B[k] < A[k] for k in DOM_BAD)

def detectors(hand, table, pile, unseen, chosen, esperto, ace_rule, last_card):
    """-> (tags list, dominating_move or None). dominating_move = (slot, capset, featsB, featsChosen)."""
    cslot, cset = chosen['slot'], chosen['capset']
    legal = []                       # (slot, capset|None, feats)
    for slot, card in enumerate(hand):
        if card is None: continue
        caps, _ = find_captures(VAL[card], table, ace_rule)
        if caps:
            for cs in caps:
                legal.append((slot, cs, move_features(slot, cs, hand, table, pile, unseen, last_card)))
        else:
            legal.append((slot, None, move_features(slot, None, hand, table, pile, unseen, last_card)))
    chosen_feat = move_features(cslot, cset, hand, table, pile, unseen, last_card)
    dom = None
    for slot, cs, f in legal:
        if (slot, cs) == (cslot, cset): continue
        if dominates(f, chosen_feat):
            dom = (slot, cs, f, chosen_feat); break
    tags = []
    if chosen_feat['opp_scopa'] and any(not f['opp_scopa'] for _, _, f in legal): tags.append("gave_scopa")
    if chosen_feat['leaves_sette'] and any(not f['leaves_sette'] for _, _, f in legal): tags.append("left_settebello")
    if cset is None and any(cs is not None for _, cs, _ in legal): tags.append("drop_with_capture")
    return tags, dom

# ---------------- scoring ----------------
PRIME = {1:16,2:12,3:13,4:14,5:15,6:18,7:21,8:10,9:10,10:10}
def score_deal(pp, op, sp, so):
    def coins(p): return sum(1 for c in p if is_coin(c))
    def prim(p):
        b = {0:0,1:0,2:0,3:0}
        for c in p: b[SUIT[c]] = max(b[SUIT[c]], PRIME[VAL[c]])
        return 0 if any(v == 0 for v in b.values()) else sum(b.values())
    def nap(p):
        n = 0
        for cid in range(10):
            if cid in p: n += 1
            else: break
        return n if n >= 3 else 0
    a = b = 0
    if len(pp) > len(op): a += 1
    elif len(op) > len(pp): b += 1
    if coins(pp) > coins(op): a += 1
    elif coins(op) > coins(pp): b += 1
    if SETTEBELLO in pp: a += 1
    else: b += 1
    pa, pb = prim(pp), prim(op)
    if pa > pb: a += 1
    elif pb > pa: b += 1
    a += sp + nap(pp); b += so + nap(op)
    if all(s in pp for s in (6,16,26,36)): a += 1
    if all(s in op for s in (6,16,26,36)): b += 1
    return a, b

# ---------------- self-play with logging ----------------
def play_deal(rng, leader, ace_rule, log):
    deck = list(range(40)); rng.shuffle(deck)
    table = [deck.pop() for _ in range(4)]
    hands = [[], []]; piles = [[], []]; scopas = [0, 0]; last_cap = None
    turn = 0 if leader == 0 else 1
    while True:
        if not hands[0] and not hands[1]:
            if not deck: break
            for _ in range(3):
                if deck: hands[0].append(deck.pop())
                if deck: hands[1].append(deck.pop())
        S = turn
        # unseen[v] from S's view = #cards of value v in (opponent hand + deck)
        unseen = [0]*11
        for c in hands[1-S] + deck: unseen[VAL[c]] += 1
        decision = ai_select(hands[S], table, piles[S], unseen, esperto=True, ace_rule=ace_rule)
        last_card = (len(deck) == 0 and len(hands[0]) + len(hands[1]) == 1)
        # only audit while the heuristic is the real engine (deck not yet empty)
        if deck:
            tags, dom = detectors(hands[S], table, piles[S], unseen, decision, True, ace_rule, last_card)
            if dom or tags:
                log(tags, dom, hands[S][:], table[:], piles[S][:], piles[1-S][:],
                    unseen[:], decision, len(deck))
        slot, cset = decision['slot'], decision['capset']
        card = hands[S].pop(slot)
        if cset is not None:
            ace_sweep = decision['ace_sweep']
            captured = [table[i] for i in sorted(cset)]
            piles[S].extend(captured); piles[S].append(card)
            table = [table[i] for i in range(len(table)) if i not in cset]
            last_cap = S
            left = len(hands[0]) + len(hands[1]) + len(deck)
            if not table and left > 0 and not ace_sweep: scopas[S] += 1
        else:
            table.append(card)
        turn ^= 1
    if table and last_cap is not None: piles[last_cap].extend(table)
    return score_deal(piles[0], piles[1], scopas[0], scopas[1])

def play_match(rng, ace_rule, log):
    a = b = 0; leader = 0 if rng.random() < 0.5 else 1
    while True:
        da, db = play_deal(rng, leader, ace_rule, log); a += da; b += db; leader ^= 1
        if (a >= 11 or b >= 11) and a != b: return

def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    ace_rule = '--asso' in sys.argv
    rng = random.Random(seed)
    counts = defaultdict(int); examples = defaultdict(list); nflag = [0]; domkind = defaultdict(int)
    def log(tags, dom, hand, table, pile, opile, unseen, decision, deckleft):
        nflag[0] += 1
        rec = dict(tags=tags, hand=hand, table=table, pile=pile, opile=opile, unseen=unseen,
                   slot=decision['slot'], capset=list(decision['capset']) if decision['capset'] else None,
                   score=decision['score'], deckleft=deckleft, dom=None)
        if dom:
            counts['DOMINATED'] += 1
            kind = tuple(sorted(k for k in DOM_GOOD if dom[2][k] > dom[3][k])) or \
                   tuple('-' + k for k in DOM_BAD if dom[2][k] < dom[3][k])
            domkind[kind] += 1
            rec['dom'] = dict(slot=dom[0], capset=list(dom[1]) if dom[1] else None,
                              better=dom[2], chosen=dom[3])
            if len(examples['DOMINATED']) < 14: examples['DOMINATED'].append(rec)
        for t in tags:
            counts[t] += 1
            if len(examples[t]) < 8: examples[t].append(rec)
    for _ in range(N):
        play_match(rng, ace_rule, log)
    print(f"== ai_watch: {N} Esperto-v-Esperto matches, asso={'on' if ace_rule else 'off'}, seed {seed} ==")
    print(f"flagged mid-game decisions: {nflag[0]}\n")
    print(f"  DOMINATED  (a strictly-better legal move existed): {counts['DOMINATED']}"
          f"  (~{counts['DOMINATED']/N:.2f}/match)")
    print(f"  dominated breakdown (which fundamental the better move wins on):")
    for kind, c in sorted(domkind.items(), key=lambda kv: -kv[1]):
        print(f"     {'+'.join(kind):20} {c}")
    print(f"  soft tags: gave_scopa={counts['gave_scopa']}  left_settebello={counts['left_settebello']}"
          f"  drop_with_capture={counts['drop_with_capture']}")
    out = os.environ.get('SCRATCH', '/private/tmp/claude-501/-Volumes-SSD1-code-retro-computing/'
          '72dc0c20-d47b-4fae-9ee6-816d84514517/scratchpad')
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'odd_boards.json'), 'w') as fh:
        json.dump(dict(counts=dict(counts), dominated=examples['DOMINATED']), fh, indent=1)
    print(f"\nall DOMINATED examples -> {out}/odd_boards.json")
    def desc(hand, slot, cs, table):
        p = hand[slot]
        return f"drop {nm(p)}" if cs is None else f"play {nm(p)} -> take {names([table[i] for i in cs])}"
    for i, rec in enumerate(examples['DOMINATED'][:12]):
        print(f"\n--- DOMINATED #{i+1}  (deckleft={rec['deckleft']}) ---")
        print(f"    hand  = {names(rec['hand'])}")
        print(f"    table = {names(rec['table'])}")
        print(f"    CHOSE : {desc(rec['hand'], rec['slot'], rec['capset'], rec['table'])}  (eval {rec['score']})")
        d = rec['dom']
        print(f"    BETTER: {desc(rec['hand'], d['slot'], d['capset'], rec['table'])}")
        bf, cf = d['better'], d['chosen']
        diff = {k: (cf[k], bf[k]) for k in list(DOM_GOOD)+list(DOM_BAD) if bf[k] != cf[k]}
        print(f"    (chosen->better differs on: {diff})")

if __name__ == '__main__':
    main()
