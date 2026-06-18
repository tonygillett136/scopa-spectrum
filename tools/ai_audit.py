#!/usr/bin/env python3
"""Audit the SHIPPED Scopa AI's discard choices (esp. the coin-king question).

Imports the faithful host-mirror from ai_tune.py but overrides the weights with the
ACTUAL shipped values baked into scopa.asm (ai_tune.W0 is the stale pre-tuning baseline).

Run: python tools/ai_audit.py
"""
import random
import ai_tune as T
from ai_tune import VAL, SUIT, PRIME_BY_VALUE, eval_drop, eval_capture, ai_select, \
    find_all_captures, winrate, play_deal, play_match

# ---- weights as actually shipped in scopa.asm (read off the source, June 2026) ----
SHIPPED = dict(
    card_count=3,          # EvalCapture  "*3 (self-play tuned, was *2)"
    denari=5,              # CardBonus    denari card
    settebello_cap=35,     # CardBonus    settebello captured
    seven=12,              # CardBonus    SEVEN capture (was 15)
    six=8,                 # CardBonus    six
    ace=6,                 # CardBonus    ace
    sweep=50,              # EvalCapture  SWEEP (scopa)
    drop_settebello=-40,   # EvalDrop     SETTEBELLO_DROP
    drop_seven=-5,         # EvalDrop     DROP_7  (was -12)
    drop_six=-5,           # EvalDrop     DROP_6  (was -6)
    drop_denari=-4,        # EvalDrop     DROP_DENARI
    drop_face=3,           # EvalDrop     prefer dropping face cards
    leave_sweep_risk=-9,   # EvalSafety   LEAVE_SWEEP_RISK (was -20)
    leave_easy_capture=-5, # EvalSafety   LEAVE_EASY_CAPTURE per value (was -2)
    ace_guard_card=-1,     # EvalSafety   -1 per leftover card (ace rule)
    ace_guard_settebello=-25,
)

CARDNAME = {}
SUITNAME = ['denari', 'coppe', 'spade', 'bastoni']
RANKNAME = {1:'Asso',2:'2',3:'3',4:'4',5:'5',6:'6',7:'7',8:'Fante',9:'Cavallo',10:'Re'}
for i in range(40):
    CARDNAME[i] = f"{RANKNAME[VAL[i]]} di {SUITNAME[SUIT[i]]}"

def name(c): return CARDNAME[c] if c is not None else "-"

def show_drop_scores(hand, table, ace_rule, difficulty=1, w=SHIPPED):
    """Print eval_drop / eval_capture for each hand card and the AI's pick."""
    print(f"  table={[name(c) for c in table]}  ace_rule={ace_rule}  diff={difficulty}")
    for c in hand:
        opts, ace_sweep = find_all_captures(VAL[c], table, ace_rule)
        if opts:
            best = max(eval_capture(c, cs, table, w, difficulty, ace_rule, ace_sweep) for cs in opts)
            print(f"    {name(c):20} id{c:2}  CAPTURE best score = {best:+d}")
        else:
            s = eval_drop(c, table, w, difficulty, ace_rule)
            print(f"    {name(c):20} id{c:2}  DROP    score = {s:+d}")
    hi, capset = ai_select(hand, table, w, difficulty, ace_rule)
    act = "captures" if capset is not None else "DROPS"
    print(f"  --> AI plays slot {hi}: {name(hand[hi])}  ({act})\n")


print("=" * 72)
print("0. SANITY: mirror winrate with SHIPPED weights (should be ~0.50)")
print("=" * 72)
print(f"  shipped vs shipped, 4000 matches, ace_rule on  = "
      f"{winrate(SHIPPED, SHIPPED, 4000, 42, ace_rule=True):.3f}")
print(f"  shipped vs shipped, 4000 matches, ace_rule off = "
      f"{winrate(SHIPPED, SHIPPED, 4000, 43, ace_rule=False):.3f}")

print()
print("=" * 72)
print("1. TONY'S SCENARIO: two kings held, empty table, one is the King of Coins")
print("=" * 72)
print("Hand = [Re di denari (coin king), Re di coppe (non-coin)], table empty")
show_drop_scores([9, 19], [], ace_rule=True,  difficulty=1)
show_drop_scores([9, 19], [], ace_rule=True,  difficulty=3)
show_drop_scores([9, 19], [], ace_rule=False, difficulty=1)

print("=" * 72)
print("2. VARIANT: coin King vs a SEVEN (does a high drop-penalty card flip it?)")
print("=" * 72)
print("Hand = [Re di denari (coin king), 7 di coppe], table empty")
show_drop_scores([9, 16], [], ace_rule=True, difficulty=1)
print("Hand = [Re di denari (coin king), 7 di bastoni], table empty")
show_drop_scores([9, 36], [], ace_rule=True, difficulty=1)

print("=" * 72)
print("3. VARIANT: two non-coin kings (which suit gets thrown? should be arbitrary)")
print("=" * 72)
show_drop_scores([19, 29], [], ace_rule=True, difficulty=1)

print("=" * 72)
print("4. VARIANT: coin king vs non-coin king with a NON-EMPTY table")
print("=" * 72)
print("table=[3 di spade] so a leftover sum could matter")
show_drop_scores([9, 19], [22], ace_rule=True, difficulty=1)
print("table=[Re di spade] -> dropping either king makes a pair the opp can capture")
show_drop_scores([9, 19], [29], ace_rule=True, difficulty=1)

print("=" * 72)
print("5. SCAN: how often does the AI throw a COIN when an equally/more-droppable")
print("   NON-coin alternative existed? (a 'coin leak' rate over random must-drops)")
print("=" * 72)
def scan_coin_leak_orig(n=200000, ace_rule=True, w=SHIPPED, diff=1, seed=7):
    rng = random.Random(seed)
    must_drop = 0          # positions where NO card in hand can capture
    threw_coin = 0         # ...and the AI threw a coin
    threw_coin_avoidable = 0  # ...and a non-coin drop was available
    for _ in range(n):
        deck = list(range(40)); rng.shuffle(deck)
        tn = rng.randint(0, 4)
        table = deck[:tn]
        hand = deck[tn:tn+3]
        # only count positions where every hand card must drop (no capture)
        if any(find_all_captures(VAL[c], table, ace_rule)[0] for c in hand):
            continue
        must_drop += 1
        hi, _ = ai_select(hand, table, w, diff, ace_rule)
        thrown = hand[hi]
        has_noncoin = any(c >= 10 for c in hand)
        if thrown < 10:               # threw a coin
            threw_coin += 1
            if has_noncoin:
                threw_coin_avoidable += 1
    print(f"  must-drop positions: {must_drop}")
    print(f"  threw a coin:        {threw_coin}  ({100*threw_coin/must_drop:.1f}%)")
    print(f"  ...with a non-coin alternative available: {threw_coin_avoidable} "
          f"({100*threw_coin_avoidable/must_drop:.1f}% of must-drops)")
scan_coin_leak_orig()

# ===========================================================================
from ai_tune import ai_select_2ply, sel_random, score_deal

print()
print("=" * 72)
print("6. GENERAL STRENGTH of the shipped 1-ply heuristic")
print("=" * 72)
rA = dict(SHIPPED); rA['_rng'] = random.Random(7)
print(f"  shipped vs RANDOM   (2000 matches, ace on)  = "
      f"{winrate(SHIPPED, rA, 2000, 11, ai_select, sel_random, ace_rule=True):.3f}")
print("  -> how much a 2-ply paranoid lookahead beats the shipped 1-ply (its own weights):")
for disc in (0.3, 0.5, 0.7):
    sel2 = lambda h, t, w, d=1, a=False, _dc=disc: ai_select_2ply(h, t, w, d, a, _dc)
    wr = winrate(SHIPPED, SHIPPED, 3000, 555, sel2, ai_select, ace_rule=True)
    print(f"     2-ply(discount={disc}) vs shipped 1-ply = {wr:.3f}  "
          f"({'2-ply better' if wr>0.52 else 'no clear edge' if wr<0.55 else ''})")

print()
print("=" * 72)
print("7. POINT-TYPE BREAKDOWN (self-play): which points are decided, scopa rate,")
print("   avg margin. Reveals what the heuristic actually optimises vs ignores.")
print("=" * 72)
def coins(p):  return sum(1 for c in p if c < 10)
def primiera(p):
    best = {0:0,1:0,2:0,3:0}
    for c in p: best[SUIT[c]] = max(best[SUIT[c]], PRIME_BY_VALUE[VAL[c]])
    if any(v == 0 for v in best.values()): return 0
    return sum(best.values())
def breakdown(n=20000, ace_rule=True, w=SHIPPED, seed=99):
    rng = random.Random(seed)
    tot = dict(carte=0, denari=0, settebello=0, primiera=0, scopa_total=0,
               deals=0, scopa_deals=0, draws_carte=0, draws_denari=0, draws_prim=0)
    for _ in range(n):
        # instrumented single deal
        deck = list(range(40)); rng.shuffle(deck)
        table = [deck.pop() for _ in range(4)]
        hands=[[],[]]; piles=[[],[]]; scopas=[0,0]; last=None
        turn = rng.randint(0,1)
        while True:
            if not hands[0] and not hands[1]:
                if not deck: break
                for _ in range(3):
                    if deck: hands[0].append(deck.pop())
                    if deck: hands[1].append(deck.pop())
            hi, capset = ai_select(hands[turn], table, w, 1, ace_rule)
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
        tot['deals']+=1
        if len(piles[0])!=len(piles[1]): tot['carte']+=1
        else: tot['draws_carte']+=1
        if coins(piles[0])!=coins(piles[1]): tot['denari']+=1
        else: tot['draws_denari']+=1
        tot['settebello']+=1   # always decided
        if primiera(piles[0])!=primiera(piles[1]): tot['primiera']+=1
        else: tot['draws_prim']+=1
        sc = scopas[0]+scopas[1]
        tot['scopa_total']+=sc
        if sc: tot['scopa_deals']+=1
    d=tot['deals']
    print(f"  deals simulated: {d}")
    print(f"  carte point decided (not a 20-20 draw): {100*tot['carte']/d:.1f}%   "
          f"(draws {100*tot['draws_carte']/d:.1f}%)")
    print(f"  denari point decided (not 5-5):         {100*tot['denari']/d:.1f}%   "
          f"(draws {100*tot['draws_denari']/d:.1f}%)")
    print(f"  primiera decided:                       {100*tot['primiera']/d:.1f}%   "
          f"(draws {100*tot['draws_prim']/d:.1f}%)")
    print(f"  scope per deal (both sides):            {tot['scopa_total']/d:.3f}")
    print(f"  deals with >=1 scopa:                   {100*tot['scopa_deals']/d:.1f}%")
breakdown()

# ===========================================================================
print()
print("=" * 72)
print("8. DOES SMARTER HANDLING ACTUALLY WIN MORE? (candidate variants vs shipped)")
print("=" * 72)
def head_to_head(variant, label, n=8000, seed=1234, ace_rule=True):
    wr = winrate(variant, SHIPPED, n, seed, ace_rule=ace_rule)
    print(f"  {label:42} vs shipped = {wr:.3f}  "
          f"({'+' if wr>0.5 else ''}{(wr-0.5)*100:+.1f}pts)")
    return wr

v_coin   = dict(SHIPPED, drop_denari=-10)
v_coin2  = dict(SHIPPED, drop_denari=-14, ace_guard_card=-2)
v_cards  = dict(SHIPPED, card_count=4)
v_seven  = dict(SHIPPED, seven=18, drop_seven=-10)
v_combo  = dict(SHIPPED, drop_denari=-10, seven=16, drop_seven=-8)
head_to_head(v_coin,  "stronger coin-keep (drop_denari -4->-10)")
head_to_head(v_coin2, "much stronger coin-keep + ace-guard")
head_to_head(v_cards, "grab more cards (card_count 3->4)")
head_to_head(v_seven, "value sevens more")
head_to_head(v_combo, "coin + seven combo")

print()
print("=" * 72)
print("9. HEADROOM: coordinate-ascent optimiser starting FROM the shipped weights")
print("   (if it can't beat ~0.52, the 1-ply weights are already near-optimal and")
print("    the ceiling is the 1-ply STRUCTURE, not the tuning.)")
print("=" * 72)
import ai_tune
ai_tune.W0 = dict(SHIPPED)            # re-baseline the optimiser on shipped weights
tuned = ai_tune.optimise(budget_matches=400, passes=2, rebaselines=1)
print("  tuned-from-shipped vs shipped (6000 matches):",
      f"{winrate(tuned, SHIPPED, 6000, 31337, ace_rule=True):.3f}")
changed = {k: (SHIPPED[k], tuned[k]) for k in ai_tune.TUNE_KEYS if tuned[k] != SHIPPED[k]}
print("  weights it wanted to change:", changed)
