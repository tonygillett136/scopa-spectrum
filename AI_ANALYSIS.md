# Scopa AI — depth audit & conclusion (2026-06-18)

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
