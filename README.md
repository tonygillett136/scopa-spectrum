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
- **Skill select**: `1` Easy, `2` Medium, `3` Hard.
- **In play**: `O` / `P` move the cursor over your hand (and cycle capture options when a
  played card can take more than one set); `SPACE` plays / confirms.

Match is first to 11 points. Each deal scores **Carte** (most cards), **Denari** (most
coins), **Settebello** (7 of coins), **Primiera** (best card from each suit), one point per
**Scopa** (table sweep), plus the regional **Napola/Neapolitan** and *palle del cane* bonuses.

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
`sjasmplus -DTESTMODE=N scopa.asm` (N = 1..15; see `DEVELOPMENT.md`).

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
| `tools/` | Art pipeline (`convert_deck.py`, `make_screens.py`, `mono_outline.py`, …) |
| `DEVELOPMENT.md` | Architecture / memory map / build / gotchas reference |
| `DEVLOG.md` | Chronological build log |
| `ARTICLE.md` | Write-up of how the game was built |

Built and tuned against real hardware on a CRT.
