# Scopa for the 48K ZX Spectrum

A complete implementation of the Italian card game **Scopa**, written in Z80 machine
code for an unmodified 48K Sinclair ZX Spectrum. One player versus a strong AI, match
to 11, with the full Neapolitan (Napoletane) deck rendered in defined-monochrome card art.

> *Based on an original ZX Spectrum game by Angelo Colucci* — a friend's game from years
> ago, whose hand-drawn cards were superb and which was lost to time. This is a recreation,
> built to honour it.

## Playing it

Load `scopa.tap` on a real 48K Spectrum or an accurate emulator. It boots from a silent
multi-part tape loader straight to the title screen.

- **Title screen**: `SPACE` to start, `H` for how-to-play.
- **Skill select**: `1` Easy, `2` Medium, `3` Hard. `4` toggles the optional **Asso piglia
  tutto** rule (default OFF — see below).
- **In play**: `O` / `P` move the cursor over your hand (and cycle capture options when a
  played card can take more than one set); `SPACE` plays / confirms. Your played card stays
  in your hand while you choose which cards to take, so it never hides the table.

Match is first to 11 points. Each deal scores **Carte** (most cards), **Denari** (most
coins), **Settebello** (7 of coins), **Primiera** (best card from each suit), one point per
**Scopa** (table sweep), plus the regional **Napola/Neapolitan** and *palle del cane* bonuses.

### Optional rule: *Asso piglia tutto*

A traditional Neapolitan variation, off by default, toggled with `4` on the skill screen.
With it on, playing an **ace sweeps the whole table** — unless an ace is already on the table
(then it takes only that ace), and an ace on an empty table simply drops. This is the *Scopa
d'Assi* reading, where clearing the table with an ace scores **no** Scopa point.

## The AI

The opponent evaluates **every legal play** — each card in its hand against each way it could
capture, plus simply dropping — and scores each with a weighted value function, then plays the
best (a 1-ply look). The priorities mirror how Scopa actually scores: the *settebello* and the
sevens/sixes (primiera) are prized, a *scopa* is big, and it weighs grabbing points now against
leaving you an easy table.

- **Easy** — greedy: takes the most valuable capture, ignores what it leaves behind.
- **Medium** — adds defence: avoids handing you a sweep or easy matches.
- **Hard** — adds card-counting: it remembers every card already played and pushes harder late
  in a deal.

It plays **fair**. The AI only ever sees its own hand, the face-up table, and (on Hard) the
public record of cards already played — *never* your hand or the deck order. The deck is a
Fisher-Yates shuffle seeded at boot.

The weights aren't guesses any more: they were **self-play tuned** with `tools/ai_tune.py`, a
host-side simulator that plays tens of thousands of games to search the weight space (only
changes that reproduced across independent runs were kept).

## Building

Requires [sjasmplus](https://github.com/z00m128/sjasmplus) and Python 3 (with Pillow, only
if regenerating the art).

```sh
# (optional) regenerate art from the reference card photos — see note below:
python tools/convert_deck.py      # -> deck.bin        (RUN FROM this directory)
python tools/make_screens.py      # -> title.scr, loading.scr, *_banner.bin

# assemble + build the tape:
sjasmplus scopa.asm               # -> scopa.sna (emulator) + scopa_code.bin
python build_tap.py               # -> scopa.tap
```

`TESTMODE` builds run scripted scenarios for headless verification:
`sjasmplus -DTESTMODE=N scopa.asm` (N = 1..19; see `DEVELOPMENT.md`).

### Note on the card art

The deck art is **derived** from photographs of a physical Napoletane deck that are *not*
included in this repository. The committed `deck.bin` (and `title.scr` / `loading.scr` /
banners) are the monochrome renderings the game actually ships; the original colour scans
live outside the repo, so `tools/convert_deck.py` won't re-run without them. The art is
strictly faithful to that reference deck.

## Layout

| Path | What |
|------|------|
| `scopa.asm` | The whole game (Z80, sjasmplus) |
| `deck.bin` | 40 cards + 1 back, 384 bitmap bytes each, INCBIN @0xC000 |
| `title.rle` / `title.scr` / `loading.scr` | Screens |
| `*_banner.bin` | SCOPA! / NEAPOLITAN / tricolore banners |
| `build_tap.py` | Builds `scopa.tap` (silent multi-part loader) |
| `tools/` | Art pipeline (`convert_deck.py`, `make_screens.py`, `mono_outline.py`) + `ai_tune.py` (host-side AI weight tuner) |
| `DEVELOPMENT.md` | Architecture / memory map / build / gotchas reference |
| `DEVLOG.md` | Chronological build log |
| `ARTICLE.md` | Write-up of how the game was built |

Built and tuned against real hardware on a CRT.
