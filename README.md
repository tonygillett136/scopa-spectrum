# Scopa Spectrum

A faithful recreation of the classic Italian card game **Scopa**, rendered with authentic **ZX Spectrum** aesthetics in the browser.

Built with HTML5 Canvas and vanilla JavaScript — no frameworks, no dependencies.

## Features

- **Authentic ZX Spectrum look** — 256x192 framebuffer with attribute clash (2 colours per 8x8 cell), border stripes, and ROM-accurate font
- **CRT effects** — scanlines, phosphor glow, and vignette overlay
- **Beeper audio** — square-wave sound effects and a looping title melody, all via Web Audio API
- **Digitized card sprites** — 40-card Napoletane deck rendered as 80x128px pixel art with rounded borders
- **Three AI difficulty levels** — Easy (makes mistakes), Medium (balanced), Hard (card counting)
- **2-Player hot-seat** — handover screen between turns
- **Best-of-3 match mode** — toggle on/off from the title screen
- **Persistent statistics** — win/loss record saved to localStorage
- **Deal and capture animations** — cards slide across the screen with beeper sound effects

## How to Play

Open `index.html` in a browser — either directly (`file://`) or via any HTTP server.

### Controls

| Key | Action |
|-----|--------|
| **1 / 2 / 3** | Start game: Easy / Medium / Hard vs CPU |
| **4** | Start 2-Player hot-seat game |
| **5** | View statistics |
| **I** | Instructions |
| **B** | Toggle Best-of-3 match mode |
| **Left / Right** | Select card in hand or on table |
| **Space / Enter** | Play selected card / confirm capture |
| **Up / Down** | Switch between hand view and table view |

### Scopa Rules

Play a card from your hand to the table:

- If its value matches a single table card, capture it
- If its value equals the sum of multiple table cards, capture them all
- If a single-card match exists, you **must** take it (priority rule)
- Capturing all table cards is a **scopa** (sweep) — worth 1 bonus point

**Scoring** (per hand):

| Category | Points |
|----------|--------|
| **Carte** | 1 pt — most cards captured |
| **Denari** | 1 pt — most coin-suit cards |
| **Settebello** | 1 pt — captured the 7 of Denari |
| **Primiera** | 1 pt — highest Primiera total |
| **Scope** | 1 pt each — per sweep |

First to **11 points** wins.

## Project Structure

```
index.html              Entry point
css/crt.css             CRT overlay styles
js/
  main.js               Boot sequence, game loop, screen manager
  screens/
    loading.js          Faux tape-loading screen
    title.js            Title screen with menu and music
    gameplay.js         Main game screen with animations
  game/
    state.js            Game state FSM
    rules.js            Capture logic and scopa rules
    scoring.js          End-of-hand scoring (Primiera, etc.)
    deck.js             Card deck creation and shuffling
    ai.js               AI with 3 difficulty levels
    match.js            Best-of-3 match series
    stats.js            localStorage statistics
  audio/
    beeper.js           Square-wave beeper engine
    sfx.js              Sound effects
    music.js            Title screen melody
    tape.js             Tape-loading noise
  data/
    cards.js            Card sprite API
    card-sprites.js     Pre-converted base64 sprite data
    loading-screen.js   Loading screen pixel data
  spectrum/
    framebuffer.js      256x192 interleaved VRAM
    renderer.js         Canvas renderer with 3x scaling
    gfx.js              Drawing primitives
    font.js             ZX Spectrum ROM font
    border.js           Border stripes effect
    crt.js              CRT post-processing
    constants.js        Colour palette and dimensions
    dither.js           Dithering utilities
reference_cards/        Napoletane card reference images
tools/
  download_cards.py     Script to fetch card images
  convert_cards.py      Script to convert cards to sprite data
```

## Technical Details

- **Rendering**: Native 320x256 canvas (256x192 + 32px border) scaled 3x with nearest-neighbour interpolation
- **Game loop**: 50fps via `requestAnimationFrame`
- **FLASH attribute**: Toggles every 320ms, matching the real Spectrum
- **Audio**: Lazy `AudioContext` initialisation on first user interaction
- **No build step**: Pure ES modules loaded directly by the browser

## License

MIT
