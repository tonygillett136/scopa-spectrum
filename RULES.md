# Scopa — Rules & Scoring (as implemented)

This documents the exact rules and scoring **this game implements**, not generic Scopa. Where the
implementation makes a specific choice among the many regional variants, that choice is called out.
Source references point at `scopa.asm` so this doubles as a developer reference.

Scopa is a traditional Italian fishing card game for two players (here: you vs. the AI). You capture
cards from a shared table by matching values, and score at the end of each round (deal). First to
**11 points** wins the match.

---

## 1. The deck

A 40-card **Neapolitan** deck — four suits of ten cards each:

- **Coins** (*denari*) · **Cups** (*coppe*) · **Swords** (*spade*) · **Clubs** (*bastoni*)
- Values **1–10**: Ace (1), 2…7, then the three court figures — **Fante** (Jack, 8),
  **Cavallo** (Knight, 9), **Re** (King, 10).

Internally each card is an id `0–39`: `suit = id / 10` (0 coins, 1 cups, 2 swords, 3 clubs),
`value = id % 10 + 1`. The **settebello** (7 of coins) is id 6; it matters for scoring.

---

## 2. Setup and the deal

- The deck is shuffled. **Four cards** are dealt face-up to the table and **three cards** to each
  player's hand. (If three or more Kings land on the opening table some rule-sets redeal; this game
  does **not** — it deals straight.)
- Players alternate playing one card at a time until both hands are empty, then **three more** are
  dealt to each (the table is *not* replenished). This repeats until the 40-card deck is exhausted —
  six deals of three per player. The **last** deal empties the deck.
- **Who leads:** random for the first match of a session, then alternates each match; within a match
  the deal/lead alternates each round. (`OpenLeader`, `Leader`.)

---

## 3. Playing a turn

On your turn you play one card from your hand and either **capture** or **drop** it:

- **Capture a single card:** if a table card has the **same value** as your card, you may take it.
- **Capture a sum:** if a set of table cards **adds up to** your card's value, you may take that whole
  set (e.g. play a 7 to take a 3 + 4).
- **You must capture if a capture is possible** — you can't choose to drop instead. When more than one
  capture is legal, *you* choose which (the AI picks the best). (`findAllCaptures`, `ResolvePlay`.)
- **Drop:** if no capture is possible, the card is laid face-up on the table.

Captured cards (yours plus the card you played) go to your score pile; they're only counted at the end
of the round.

---

## 4. Scopa (the sweep)

Clearing the **entire table** with a capture scores a **Scopa**: **+1 point**, immediately, that round.

Two exceptions are enforced:

- **Not on the last play of the deal.** Capturing the final card(s) of the very last deal never counts
  as a Scopa. (`IsLastPlay` — see also the *Scoring* note below.)
- **Not with an ace under *Asso piglia tutto*** (see §5) — a "*Scopa d'Assi*" doesn't count.
  (`AceSweepOpt`.)

Each Scopa is worth one point and they accumulate over the round (`PScopa`/`OScopa`).

---

## 5. *Asso piglia tutto* — optional rule (default **OFF**)

A toggle on the skill menu (key **5**). When **ON**, playing an **ace** captures the **whole table**
regardless of values (the ace is a "sweep"). As noted above, clearing the table *with the ace this way*
is **not** scored as a Scopa. When OFF, an ace behaves as a normal value-1 card. (`AceRule`.)

---

## 6. End-of-round scoring

After each deal is fully played, both pile counts are scored. The implementation awards these
categories (`ScoreRound`):

| Category | Points | Awarded to | Tie |
|---|---|---|---|
| **Carte** (most cards) | 1 | whoever captured more cards | no point |
| **Denari** (most coins) | 1 | whoever captured more *coins* (any suit-0 card) | no point |
| **Settebello** (7 of coins) | 1 | whoever holds the 7 of coins | n/a (only one exists) |
| **Primiera** (best "prime") | 1 | higher primiera total (see §7) | no point |
| **Scope** (sweeps) | 1 each | accumulated during the round (§4) | — |
| **Napola** (coin run) | variable | see §8 | — |
| **Palle del cane** (all four 7s) | 1 | whoever captured all four 7s | — |

For the four classic categories (**Carte, Denari, Settebello, Primiera**) the winner gets **+1** and a
**tie scores nothing** for either side (`AwardCat`). Scope, Napola and Palle del cane are added on top.

> Most "standard" Scopa is just the first four categories + Scope (to 11). This game additionally
> always scores **Napola** and **Palle del cane** as regional bonuses — see below.

---

## 7. Primiera (the "prime")

Primiera rewards holding high-"prime" cards across all four suits. Take your **best card in each suit**,
look up its prime value, and **sum the four**. Higher total wins the 1-point category (tie = none).

Prime value by card value (`PRIME` table — note it is **not** the same as the face value):

| Card | A | 2 | 3 | 4 | 5 | 6 | **7** | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Prime | 16 | 12 | 13 | 14 | 15 | 18 | **21** | 10 | 10 | 10 |

So the **7** is the most valuable primiera card, then the **6**, then the **ace** — which is why the
sevens (and the settebello especially) are fought over. (`Primiera`, best-per-suit then summed.)

---

## 8. Napola (the run of coins) — *our specific rule*

If you capture the **Ace, 2 and 3 of coins**, you score **Napola**: **3 points**, plus **+1 for each
further *consecutive* coin** you also hold (4, then 5, then 6 …). Your Napola score therefore equals
**the value of the highest unbroken run of coins from the ace**. All ten coins = **10** ("*Napoleone*").
If you don't hold all of Ace+2+3 of coins, Napola is **0**. (`Napola`.)

Examples:

- Coins A,2,3 → **3**.  A,2,3,4,5 → **5**.  A…7 → **7**.  All ten → **10**.
- Coins A,2,3,4,5 **and 8** (gap at 6,7) → **5** — the run stops at the gap; the lone 8 does **not**
  count.

**Divergence note.** Wikipedia's *Scopone trentino* description is internally inconsistent here: it says
"*additional points equal to the highest consecutive coin*" (which is our rule) but its worked example
(A,2,3,4,5,8 → 6) instead counts **1 per coin card regardless of gaps**. We deliberately implement the
cleaner, more widely-used **consecutive-run** reading (A,2,3,4,5,8 → **5**, not 6). We also do **not**
adopt the rest of that variant's package (no play-to-21, no doubled Settebello/Re-bello "in-sequence"
point, no "capture all ten coins = instant win").

**Timing — unlike a Scopa.** Napola (and Palle del cane, §9) are *pile-composition* bonuses: scored on
which cards you end up holding, **regardless of when you captured them** — including a card handed over
by the end-of-round sweep of the last table cards to the last capturer (§5). So unlike a Scopa — an *act*
that never counts on the final card (§4) — a Napola/Palle completed on the very last hand, even by that
final sweep, counts in full and its banner fires (`ShowNapolaIfDone` / `ShowPalleIfDone`, called both at
capture-time and after `SweepToLast`).

---

## 9. Palle del cane (all four sevens)

A regional bonus: capturing **all four 7s** in a round scores **+1** ("*le palle del cane*").
(`PalleDelCane`.)

---

## 10. Winning the match

Round points accumulate across rounds into the match score. After a round, if either player has reached
**11**, the higher total wins the match. **If both are at/over 11 and tied, the match does _not_ end** —
another round is played (the deal alternating as usual) and play continues until one side finishes a round
strictly ahead with ≥11. So a tie can never be the final result; there is no "draw" outcome.
(`PMatch`/`OMatch`, compared against 11; `RunMatch` `.maybe`: `jr z,.round` loops back on an exact tie,
otherwise the higher score takes `ShowWinYou`/`ShowWinOpp`.)

---

## 11. Difficulty levels

Four AI tiers, selected on the skill menu (keys **1–4**):

1. **Easy** — basic value heuristic, no sweep-avoidance.
2. **Medium** — adds positional/value weighting.
3. **Hard** — adds card-counting aggression in the late game (tracks seen cards).
4. **Esperto** — full card-counting **plus** an *exact* alpha-beta search of the perfect-information
   endgame (once the deck is empty, the unseen cards are the opponent's hand). The strongest level; the
   attract/demo mode plays at Esperto. The AI never sees your hand. (See `AI_ANALYSIS.md`.)

---

## 12. Summary of variant choices

This game is **standard 11-point Scopa** (Carte, Denari, Settebello, Primiera, plus Scope) with two
regional bonuses layered on — **Napola** (consecutive-coin run from the ace) and **Palle del cane**
(all four 7s) — and an optional **Asso piglia tutto** toggle. It is *not* the full 21-point *Scopone
trentino* ruleset. Captures are mandatory when possible; sweeps score except on the last play of a deal
or via an *asso piglia tutto* ace.
