/**
 * Border colour management.
 * The ZX Spectrum border is always from the BRIGHT 0 palette (0-7).
 */
export class Border {
    constructor(renderer) {
        this.renderer = renderer;
        this.colour = 0; // black
    }

    setColour(colour) {
        this.colour = colour & 7;
        this.renderer.setBorder(this.colour);
    }

    getColour() {
        return this.colour;
    }

    /**
     * Set per-scanline border stripe colours (for tape loading effect).
     * @param stripes Uint8Array(CANVAS_H) — colour index per native scanline
     */
    setStripes(stripes) {
        this.renderer.setBorderStripes(stripes);
    }

    clearStripes() {
        this.renderer.clearBorderStripes();
    }
}
