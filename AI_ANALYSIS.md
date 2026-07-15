# Scopa AI — depth audit & conclusion (2026-06-18)

*Disponibile anche in italiano: [AI_ANALYSIS.it.md](AI_ANALYSIS.it.md).*

Triggered by a play Tony saw in the attract/demo: *two kings held, empty table, one the
King of coins (Re di denari) — the AI played a king and it was swept by an ace. Shouldn't
it keep the coin king and throw the non-coin one?* That one play prompted a broader question:
**is the whole AI approach sound, or does it routinely make bad choices?**

This is the full investigation and its conclusion. Diagnostic scripts: `tools/ai_audit.py`,
`tools/ai_prime.py` (both run against `tools/ai_tune.py`, a faithful host-side mirror of the
Z80 evaluator — same card encoding, capture rules, weights and scoring, so results transfer).

> **Note:** `ai_tune.py`'s built-in `W0` is the *pre*-tuning baseline. The audit scripts
> override it with `SHIPPED`, the weights actually baked into `scopa.asm` (card_count ×3,
> seven 12, drop_7 −5, drop_6 −5, leave_sweep_risk −9, leave_easy_capture −5, etc.).

## 1. The specific play was correct

Reproduced in the host-mirror with the shipped weights:

```
Hand = [Re di denari (coin king), Re di coppe (non-coin)], table empty, asso piglia tutto on
  Re di denari  DROP score = -16
  Re di coppe   DROP score = -12   <- higher score wins
  --> AI DROPS the non-coin king, KEEPS the King of coins
```

The `DROP_DENARI = −4` term is exactly what tips it. Independent strategy research agreed
(Wikipedia, pagat.com, the Di Palma & Lanzi 2018 Scopone paper): **both kings are equal for
primiera (prime value 10), so the only differentiator is that the King of coins is a *coin*
— never gift a coin onto the table.** The AI passed the exact test that prompted the doubt.

The likely explanation for what was seen on the CRT: the kings are visually similar at 48×64
(the very legibility issue flagged earlier), so the *non-coin* king being thrown read as the
coin king. (One genuinely debatable case exists — `[coin king, 7]` throws the coin king to
keep the seven — but keeping the seven there is also correct: a 7 is primiera-21 and a sette.)

## 2. The architecture

Two engines:

1. **Mid-game (deck not empty): a 1-ply greedy weighted evaluator.** For every hand card it
   scores the best capture (or the drop) with hand-tuned constants — settebello +35, sweep
   +50, sevens +12, coins +5, plus safety penalties for leaving the table sweepable — and
   picks the max. The demo runs *this* until the deck empties.
2. **Endgame (deck empty): exact alpha-beta minimax** (the Esperto tier). Once the deck is
   gone the unseen cards *are* the opponent's hand, so the position is perfect-information and
   exact search becomes available; it drives the real rules engine via make/unmake.

This matches the academic recommendation for the family: **heuristic in the hidden-information
mid-game, exact search at the perfect-information endgame.** Esperto begins searching at the
*earliest* point exactness is possible (deck-empty); earlier would require determinized /
information-set search over hidden cards — heavy, non-exact, unrealistic in real-time on 48K.

## 3. Is it well-built? Strength measurements

| Measurement (host-sim, shipped weights, asso on) | Result |
|---|---|
| mirror match win rate (shipped vs shipped) | 0.498 — symmetric, no side bias |
| vs a **random** legal player | **0.837** — competent |
| **carte** point decided (not a 20–20 draw) | 92.8% |
| **denari** point decided (not 5–5) | 78.7% (21.3% draw) |
| **primiera** decided | 95.5% |
| scope per deal (both sides) | 1.484; 74.8% of deals have ≥1 scopa |

It values the right things in the right order, implements the forced-single-capture rule,
never declines a legal capture, biases capture-combos toward coins, and already penalises
leaving the table summing ≤10 (the anti-scopa rule).

## 4. Every cheap improvement was tried — none helps

The central question: can the mid-game heuristic be made stronger cheaply? Measured head-to-head
vs the shipped AI (match win rate; >0.50 = better):

| Experiment | Result | Verdict |
|---|---|---|
| Re-tune all weights (coordinate-ascent, **from** the shipped set) | 0.507 | noise — already a local optimum |
| Naive 2-ply "paranoid" lookahead (discount 0.3/0.5/0.7) | 0.46–0.48 | **worse** |
| Stronger coin-keep (drop_denari −4→−10 / −14) | 0.483–0.491 | worse |
| Grab more cards (card_count ×3→×4) | 0.497 | noise |
| Value sevens more | 0.509 | within noise |
| **Primiera-gain awareness** (pile-aware capture bonus) | 0.476–0.498 | worse / break-even |
| **Pure suit-completion** (bonus for capturing a void suit) | 0.485–0.493 | worse |
| **Paired-lead** discard (throw a card you hold a duplicate of) | 0.49–0.505 | noise |

Everything lands at or below break-even.

## 5. Why — the real insight

The primiera-awareness diagnostic is the smoking gun. The "primiera-aware" AI won the primiera
point **47.8% vs 47.7%** — *no change* — while its denari got **worse** (38.1% vs 40.7%).
Steering captures toward primiera didn't win more primiera; it just sacrificed the points the
heuristic was already winning.

The reason is structural: **the comparative points (primiera, denari, carte) are emergent over
the whole deal, not over any single play.** Your final primiera depends on the entire
composition of your pile across ~18 plays — not on any one greedy grab. A 1-ply evaluator
cannot steer an emergent, comparative quantity by local greed; when it tries, it only distorts
the locally-correct choices (grab the coin, take the settebello, avoid the sweep) it already
gets right. Three independent experiments — re-tuning, lookahead, and primiera-awareness — all
fail for the same reason.

## 6. Conclusion

**The mid-game heuristic is at the ceiling of its architecture, and that validates the design
rather than undermining it.** The only thing that demonstrably beats a tuned heuristic is
search, and search is already deployed at the one place it is both exact and cheap (the
deck-empty Esperto endgame).

**Decision: accept the verdict and leave the AI as is.** It plays the prompting scenario
correctly, is competent (84% vs random), is provably near its 1-ply ceiling (every obvious
improvement is worse or no better), and has a genuinely strong exact endgame — in a polished,
shipped, byte-tight build (~50 bytes free). The play that prompted the doubt was good play.

The remaining theoretical lever is mid-game determinized/sampling search (ISMCTS-style), which
is heavy, non-exact, and unrealistic for a real-time 48K Spectrum — and the sim suggests only
modest returns. Not worth disturbing a verified build.

---

## 7. Addendum — napola awareness (2026-06-28): the one concrete combo, shipped for OPTICS

A later CRT observation (Tony): in the demo the AI grabbed a 7 instead of the coin that would *complete*
a 3-point napola. Unlike every §4 experiment — all *emergent* quantities (primiera, suit-completion) a
1-ply eval structurally cannot steer — the napola is **concrete and attributable**: you hold it iff your
pile has A+2+3 of coins, uncontestable, exactly like the settebello the eval already values (+35). So it
was the one untested lever that *could* work. Confirmed the gap: `EvalCapture` valued 7s/settebello/coins
but never called `Napola` (only `ScoreRound` did). Modelled in `tools/ai_napola.py` (ai_prime.py's
pile-aware pattern, faithful host-mirror): a napola-gain term = (run(pile+captured) − run(pile)) × ~35.

| Experiment | Result | Verdict |
|---|---|---|
| Napola-aware capture bonus (any weight 8–90) | 0.502 (24k matches) | **within noise — not stronger** |

Neutral, not negative (unlike primiera-awareness): the napola is rare (~14% of deals), the AI already
completes most completable ones (coins are valued), the "7 vs napola-coin" conflict is rare, and taking
the coin gives up the 7 (also valuable) → net wash. Crucially it is **safe** — denari 39.4/39.2, primiera
47.9/47.9, carte 46.7/46.2, no cannibalisation (the failure mode that sank primiera-awareness). Palle-
awareness: also neutral.

**Decision (for this one term): SHIPPED — for optics, not strength.** It is the only change that fixes a
*visibly* wrong play (which matters in the watched attract demo and for player trust), is provably safe,
and is cheap. It does **not** contradict §6 — the heuristic remains at its *strength* ceiling; napola is
shipped as polish, eyes open. Z80: `NapolaBonus` in `EvalCapture` (+ `BuildNapMask`/`NapRun`/`OrCoinBit`);
verified by the `TM65` unit test (takes the napola coin in Tony's exact position) and a crash-free demo.
No other missed concrete combo exists — settebello is already valued; carte/denari/primiera are emergent;
napola/palle **denial** needs the opponent's hidden pile, which only the deck-empty Esperto minimax sees.

---

## 8. Addendum — the self-play watchdog (2026-06-29): a systematic audit, Z80-confirmed

Tony asked for a harness that plays the real logic against itself for many games and flags "odd" plays.
`tools/ai_watch.py` is a faithful host port of the SHIPPED Esperto mid-game evaluator (aiSelectPlay /
EvalCapture / EvalSafety / EvalDrop / CardBonus / NapolaBonus / ThreatLive — weights read straight out of
scopa.asm; card-counting `Seen` = table + own hand + every played card) playing Esperto-v-Esperto and
logging every mid-game decision with all alternatives. The endgame (deck empty) is the exact minimax —
provably optimal — so oddities can only live in the mid-game heuristic; only deck-not-empty decisions are
audited.

High-signal detector = **dominance**: flag a move only if another legal move is ≥ on *every* fundamental
(cards, coins, settebello, primiera-gain, scopa, napola points) and no worse on the two bad axes (hands the
opponent a scopa; leaves the settebello), strictly better somewhere — a dominated move can't be justified
by any Scopa principle. (Two iterations to get right: the vector must bank the *played* card on a capture
and use true primiera-gain, else it false-flags playing the settebello to capture, or capturing two aces
over one coin.)

**Confirmed on the real Z80.** `tools/ai_zx_check.py` replays each flagged board through the shipped ROM
via a board-injection probe (`TESTMODE 70`: poke Table/hand/OPile/Seen, run the real aiSelectPlay, read
back BestSlot + the captured mask). **14/14 flagged boards → the Z80 makes the identical decision**, so the
mirror is a faithful replica and the findings are the actual shipped logic. (Found + fixed a real harness
bug en route: `zx_shot.write_mem` used ZRCP `write-memory` with a concatenated hex string, which mangles
multi-byte writes — must be `write-memory-raw`.)

**Findings (5000 Esperto-v-Esperto matches, asso off):** ~1.5 dominated mid-game plays per match. Which
fundamental the better move wins on:

| Category | Share | Reading |
|---|---|---|
| primiera (incl. +coins/+cards) | ~75% | the known emergent-primiera blindness (§4/§6) |
| napola points | ~16% | a flat rank bonus occasionally out-weighs a napola gain |
| leaves opp a scopa (vs equal safe move) | ~4% | accepted a small sweep-risk over an equal safe alternative |
| pure carte / denari trades | ~5% | marginal |

**No gross blunders** — zero dropped settebelli, zero passed guaranteed points; the 18 `LEFT_SETTEBELLO`
and the rare `PASSED_SCOPA` are the napola fix correctly completing a 3–5 point napola over a 1-point card.

**Verdict:** the watchdog independently *rediscovered* §4/§6 — the only systematic suboptimality is the
marginal primiera/tempo blindness inherent to a 1-ply evaluator, and §4 already proved primiera-awareness
HURTS (primiera is comparative/emergent over the whole deal). No new bug; the AI is sound; left as-is.
Reusable: `python tools/ai_watch.py [matches]`, then `python tools/ai_zx_check.py` to Z80-confirm a flag.

---

## 9. Addendum — how it actually plays: emergent tactics, and the case file (2026-07-15)

The evaluator is a dozen weighted terms (§2), but at the table those terms compose into a
recognisable *doctrine* that was never explicitly programmed. Watching the attract demo you are
watching that doctrine — and several of its habits look wrong at first sight while being right.
This section writes the doctrine down, then lists every "that looked odd" moment ever raised
against the AI, with the verdicts.

### The doctrine

**Coin discipline: bank with coins, shed non-coins.** A coin scores Denari only from your *pile*,
and the only road from hand to pile is capturing with it. Between two equal-value cards the eval
therefore always **captures with the coin first** (the played card's own +5 lands in the banked
total) and **drops the plain one first** (`DROP_DENARI −4`). Holding a coin past a capture chance
risks being forced to drop it later — gifting a Denari-point card to the opponent. So: the 2 of
denari pair-captures while the 2 of spade waits; the 2 of spade gets thrown while the 2 of denari
waits. Both orderings are the same principle.

**The ace doctrine (asso piglia tutto on — the demo's configuration).** Under the house rule an
ace is the strongest card in the hand, and the eval treats it that way:
- *Any non-empty table:* the ace-sweep is nearly always the top-scoring play — it banks the whole
  table and leaves the opponent facing an empty one, the safest possible leave. (Ace sweeps get
  **no** +50 scopa credit — Scopa d'Assi sweeps score no point — so the choice is pure material.)
  Holding a second ace makes it better, not worse: the opponent must now drop onto the empty
  table, and the second ace harvests the drop. There is no "saving it for later" — all three hand
  cards are played before the redeal; only the order is in question, and material says ace first.
- *A lone ace on the table:* an ace takes it (re-arms your sweep threat, disarms theirs).
- *Empty table, forced drop:* it will sometimes deliberately **drop an ace** — an ace sitting on
  the table is sweep-armour, since the opponent's ace can then only capture that ace rather than
  sweep whatever accumulates. It only does this when the alternative drops are themselves risky
  (low, matchable); given a face card it drops the face and keeps both aces.
- Coin discipline applies here too: the ace of *denari* sweeps first; a non-coin ace is the one
  that gets dropped as armour.

**The drop hierarchy.** Settebello −40 (near-never), any 7 −5 and any 6 −5 (the primiera ranks),
any coin −4, faces (8/9/10) +3 — faces are the cheapest cards in the deck to lose: worst primiera
rank, and unless they are coins they carry no point value at all.

**Sweep-avoidance with real card counting.** Every leave is priced: a table summing ≤10 or
matching a rank costs points — but Esperto's `ThreatLive` check means it never fears a threat it
can *prove* dead (all four cards of that rank already seen). Under asso piglia tutto a leave is
also priced for ace-sweep exposure — unless an ace lies on the table (armour, see above) or every
ace is accounted for.

**Concrete combos are valued, emergent ones are not.** The settebello (+35) and the napola
completion (§7) are attributable to single captures, so the eval chases them. Carte, denari and
primiera as *comparative totals* are emergent over ~18 plays and provably cannot be steered by a
1-ply evaluator (§4–§6) — so it doesn't try.

**The endgame switch.** The moment the deck empties, all of the above is retired and the position
is handed to the exact minimax (§2). Two consequences for the spectator: the last hand is played
*provably optimally*, and it may **look** arbitrary — when several lines reach the same final
score the tie is broken by enumeration order, not by appearances. The minimax optimises outcome,
not optics: it will happily drop a coin it can prove the opponent has no way to capture.

### The case file

Every suspicious play ever raised (all from watching the demo or the CRT), investigated with the
host mirror and where warranted the real Z80:

| # | The suspicion | Verdict | Where |
|---|---|---|---|
| 1 | Threw the coin king while holding two kings (2026-06-18) | **AI right** — it keeps the coin king (−12 vs −16); the thrown king was the *non-coin* one, misread at 48×64 | §1 |
| 2 | Took a 7 instead of completing a 3-point napola (2026-06-28) | **Real gap** — the one confirmed miss; napola term shipped (for optics — strength-neutral) | §7 |
| 3 | Captured a 4 in preference to the 3 of coins (2026-06-29) | **AI right** — like-for-like it always takes the coin; it only prefers the 4 when that haul is strictly bigger | DEVLOG |
| 4 | "The opening table never has a same-value pair — biased shuffle?" (2026-06-29) | **Fair** — 41.2% of opening tables *do* have a pair, exhaustively over all 8,192 RNG seeds = the exact fair-deck rate; pairs are cross-suit so they don't read as pairs at demo speed | `tools/deal_check.py` |
| 5 | "The player side wins more often than the CPU" | **Variance** — 40,000-match simulation in the exact demo configuration: 0.502 | DEVLOG |
| 6 | Played an ace while holding two aces + one card (2026-07-15, asso on) | **AI right** — sweep any non-empty table (23 vs −29 for the alternative); on an empty table an ace-drop is deliberate sweep-armour | this § |
| 7 | Dropped the 2 of denari while holding a plain 2 (2026-07-15) | **Explained** — the mid-game policy *provably* prefers the plain drop (−4, mirror and Z80 agree), so this was the deck-empty minimax: a coin drop is tie-optimal when the fully-deduced opponent hand provably can't punish it. If ever seen with the deck *not* empty it would be a real find — inject the board via `TESTMODE 70` | this § |

Score so far: seven suspicions, one real gap (rare, cosmetic, fixed), six times the machine was
right in a way that read wrong at 48×64 or demo speed. That ratio is not luck — it is what a
self-play-tuned evaluator plus genuine card counting is supposed to look like from the outside.

### Interrogating a position

To ask the shipped brain about any board, drive the verified mirror directly (card ids: 0–9
denari, 10–19 coppe, 20–29 spade, 30–39 bastoni; value = id%10 + 1):

```python
import sys; sys.path.insert(0, "tools")
from ai_watch import ai_select, nm, VAL
hand, table, pile = [1, 21, 15], [31, 38, 13], []
unseen = [0]*11
for v in range(1, 11):
    unseen[v] = 4 - sum(1 for c in hand + table + pile if VAL[c] == v)
r = ai_select(hand, table, pile, unseen, esperto=True, ace_rule=True)
for sc, slot, cs, sweep in sorted(r['options'], key=lambda o: -o[0]):
    print(sc, nm(hand[slot]), "sweep" if sweep else [nm(table[i]) for i in cs] if cs else "drop")
```

The top-scoring line is what the Spectrum will play (ties: first found wins, matching the Z80's
`ConsiderBest`). To confirm a mid-game decision on the real Z80, poke the same board through the
`TESTMODE 70` probe with `tools/ai_zx_check.py`.
