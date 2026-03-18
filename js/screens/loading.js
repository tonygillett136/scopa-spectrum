import { LOADING_SCREEN_DATA } from '../data/loading-screen.js';
import { Beeper } from '../audio/beeper.js';
import { TapeSound } from '../audio/tape.js';
import * as C from '../spectrum/constants.js';

/**
 * Tape loading screen simulation.
 *
 * Phases:
 *   PROMPT  - "Press PLAY on tape" message, waiting for keypress
 *   PILOT   - Pilot tone playing, border stripes cycling red/cyan
 *   LOADING - Data block loading, image appearing band-by-band
 *   DONE    - Loading complete, brief pause before transition
 *
 * Border stripes:
 *   On a real Spectrum, the CPU toggles the border colour register in sync
 *   with the tape signal. Because the display is raster-scanned, different
 *   scanlines see different border colours, producing horizontal stripes.
 *
 *   Pilot tone (~807Hz): regular, evenly-spaced RED/CYAN stripes that
 *   scroll gently as the phase drifts relative to the frame start.
 *
 *   Data blocks: BLUE/YELLOW stripes of varying width (0-bits and 1-bits
 *   have different pulse lengths), producing the distinctive irregular
 *   "barber pole" pattern.
 */

const PHASE_PROMPT  = 0;
const PHASE_PILOT   = 1;
const PHASE_LOADING = 2;
const PHASE_DONE    = 3;

// Loading speed: bytes per frame at 50fps
// Real Spectrum: ~1500 bytes/sec = ~30 bytes/frame
// We speed it up slightly for a better experience
const BYTES_PER_FRAME = 40;

// Pilot tone duration (ms)
const PILOT_DURATION = 2000;

// Pause after loading completes before transition (ms)
const DONE_PAUSE = 1500;

// Stripe dimensions (native resolution lines)
// Pilot tone ~807Hz → ~1614 edges/sec. At 312 lines/frame * 50fps = 15600 lines/sec
// → one colour change every ~9.7 lines. We use 5 lines per band for visual clarity.
const PILOT_STRIPE_HEIGHT = 5;

export class LoadingScreen {
    constructor(onComplete) {
        this.onComplete = onComplete;
        this.phase = PHASE_PROMPT;
        this.timer = 0;
        this.bytesLoaded = 0;
        this.promptFlashTimer = 0;
        this.promptVisible = true;
        this.beeper = new Beeper();
        this.tapeSound = null;
        this.ctx = null;

        // Stripe animation state
        this.stripePhase = 0;
        this.stripeBuffer = new Uint8Array(C.CANVAS_H);
        this.dataRng = 1; // PRNG seed for data stripe widths
    }

    enter(ctx) {
        this.ctx = ctx;
        const { fb, border, gfx } = ctx;

        // Black screen, black border
        gfx.ink(C.WHITE);
        gfx.paper(C.BLACK);
        gfx.bright(false);
        gfx.cls();
        border.setColour(C.BLACK);

        // Show the prompt
        this._drawPrompt(gfx);

        this.phase = PHASE_PROMPT;
    }

    _drawPrompt(gfx) {
        gfx.ink(C.WHITE);
        gfx.paper(C.BLACK);
        gfx.bright(false);

        gfx.printAtStr(10, 3, 'Program: Scopa Spectrum');
        gfx.printAtStr(12, 3, 'Press PLAY on tape.');
        gfx.printAtStr(14, 3, '(Press any key to load)');

        // Flashing cursor at bottom
        gfx.ink(C.WHITE);
        gfx.paper(C.BLACK);
        gfx.bright(true);
        gfx.flash(true);
        gfx.printAtStr(23, 0, 'K');
        gfx.flash(false);
    }

    handleInput(key, event) {
        if (this.phase === PHASE_PROMPT) {
            this._startLoading();
        }
    }

    _startLoading() {
        // Init audio (must be from user interaction)
        this.beeper.init();
        this.beeper.resume();

        // Start tape sound
        this.tapeSound = new TapeSound(this.beeper);
        this.tapeSound.play();

        // Clear screen for loading
        const { fb, gfx } = this.ctx;
        gfx.ink(C.WHITE);
        gfx.paper(C.BLACK);
        gfx.bright(false);
        gfx.cls();

        this.phase = PHASE_PILOT;
        this.timer = 0;
        this.bytesLoaded = 0;
        this.stripePhase = 0;
        this.dataRng = 1;
    }

    update(dt) {
        switch (this.phase) {
            case PHASE_PROMPT:
                this.promptFlashTimer += dt;
                if (this.promptFlashTimer >= 500) {
                    this.promptFlashTimer = 0;
                    this.promptVisible = !this.promptVisible;
                }
                break;

            case PHASE_PILOT:
                this.timer += dt;
                // Generate scrolling red/cyan pilot stripes
                this._generatePilotStripes();
                this.ctx.border.setStripes(this.stripeBuffer);

                if (this.timer >= PILOT_DURATION) {
                    this.phase = PHASE_LOADING;
                    this.timer = 0;
                }
                break;

            case PHASE_LOADING:
                this._loadBytes();
                // Generate irregular blue/yellow data stripes
                this._generateDataStripes();
                this.ctx.border.setStripes(this.stripeBuffer);
                break;

            case PHASE_DONE:
                this.timer += dt;
                if (this.timer >= DONE_PAUSE) {
                    if (this.tapeSound) this.tapeSound.stop();
                    this.ctx.border.clearStripes();
                    this.ctx.border.setColour(C.BLACK);
                    if (this.onComplete) this.onComplete(this.beeper);
                }
                break;
        }
    }

    /**
     * Generate evenly-spaced RED/CYAN pilot tone stripes.
     * The stripes scroll smoothly to simulate phase drift between
     * the pilot tone frequency and the frame rate.
     */
    _generatePilotStripes() {
        const buf = this.stripeBuffer;
        const h = PILOT_STRIPE_HEIGHT;
        const period = h * 2; // one full red+cyan cycle

        // Advance phase each frame (fractional for smooth scrolling)
        this.stripePhase += 0.8;
        const offset = Math.floor(this.stripePhase) % period;

        for (let y = 0; y < C.CANVAS_H; y++) {
            const pos = (y + offset) % period;
            buf[y] = pos < h ? C.RED : C.CYAN;
        }
    }

    /**
     * Generate irregular BLUE/YELLOW data loading stripes.
     * On a real Spectrum, 0-bits produce narrow stripes and 1-bits produce
     * wider stripes, creating the distinctive varied-width "barber pole".
     * We simulate this with a deterministic PRNG for reproducible but
     * irregular stripe widths.
     */
    _generateDataStripes() {
        const buf = this.stripeBuffer;

        // Advance phase for scrolling effect
        this.stripePhase += 1.2;
        const offset = Math.floor(this.stripePhase);

        // Generate stripe widths using PRNG (simulates bit-stream)
        let y = 0;
        let colour = C.BLUE;
        let rng = ((offset * 2654435761) >>> 0) | 1; // hash the offset for variety

        while (y < C.CANVAS_H) {
            // Mix of narrow (2-3px, 0-bits) and wide (4-7px, 1-bits) stripes
            rng = ((rng * 1103515245 + 12345) >>> 0);
            const isBitOne = (rng >> 16) & 1;
            const width = isBitOne ? (3 + ((rng >> 8) & 3)) : (2 + ((rng >> 12) & 1));

            for (let i = 0; i < width && y < C.CANVAS_H; i++, y++) {
                buf[y] = colour;
            }
            colour = (colour === C.BLUE) ? C.YELLOW : C.BLUE;
        }
    }

    /**
     * Load N bytes of the screen data per call.
     * Writes directly into the framebuffer's interleaved pixel buffer
     * and attribute buffer, so the image appears in authentic band-by-band order.
     */
    _loadBytes() {
        const fb = this.ctx.fb;
        const end = Math.min(this.bytesLoaded + BYTES_PER_FRAME, 6912);

        for (let i = this.bytesLoaded; i < end; i++) {
            if (i < 6144) {
                fb.pixelBuffer[i] = LOADING_SCREEN_DATA[i];
            } else {
                fb.attributeBuffer[i - 6144] = LOADING_SCREEN_DATA[i];
            }
        }

        this.bytesLoaded = end;

        if (this.bytesLoaded >= 6912) {
            this.phase = PHASE_DONE;
            this.timer = 0;
            // Clear stripes and set black border on completion
            this.ctx.border.clearStripes();
            this.ctx.border.setColour(C.BLACK);
        }
    }

    render(gfx) {
        if (this.phase === PHASE_PROMPT) {
            if (!this.promptVisible) {
                gfx.ink(C.BLACK);
                gfx.paper(C.BLACK);
                gfx.bright(false);
                gfx.printAtStr(14, 3, '                         ');
            } else {
                gfx.ink(C.WHITE);
                gfx.paper(C.BLACK);
                gfx.bright(false);
                gfx.printAtStr(14, 3, '(Press any key to load)');
            }
        }
    }

    exit() {
        // Clear stripes on exit in case we leave mid-load
        if (this.ctx && this.ctx.border) {
            this.ctx.border.clearStripes();
        }
    }
}
