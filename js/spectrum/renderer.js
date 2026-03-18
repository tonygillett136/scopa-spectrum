import {
    PALETTE, SCREEN_W, SCREEN_H, CHAR_COLS,
    BORDER_SIZE, CANVAS_W, CANVAS_H
} from './constants.js';

/**
 * Renders the Spectrum framebuffer to an HTML5 canvas.
 * Handles attribute decoding, FLASH, border, and nearest-neighbour scaling.
 */
export class Renderer {
    constructor(canvas, framebuffer, scale = 3) {
        this.fb = framebuffer;
        this.scale = scale;
        this.flashPhase = false;
        this.borderColour = 0; // 0-7, always BRIGHT 0
        this.borderStripes = null; // null = solid, or Uint8Array(CANVAS_H) per-line colours

        // Output canvas — the final visible canvas
        this.canvas = canvas;
        this.canvas.width = CANVAS_W * scale;
        this.canvas.height = CANVAS_H * scale;
        this.ctx = canvas.getContext('2d');
        this.ctx.imageSmoothingEnabled = false;

        // Native resolution offscreen canvas (320x256 with border)
        this.nativeCanvas = document.createElement('canvas');
        this.nativeCanvas.width = CANVAS_W;
        this.nativeCanvas.height = CANVAS_H;
        this.nativeCtx = this.nativeCanvas.getContext('2d');

        // ImageData for the native canvas
        this.imageData = this.nativeCtx.createImageData(CANVAS_W, CANVAS_H);
        this.pixels = this.imageData.data; // Uint8ClampedArray RGBA
    }

    toggleFlash() {
        this.flashPhase = !this.flashPhase;
    }

    setBorder(colour) {
        this.borderColour = colour & 7;
    }

    setBorderStripes(stripes) {
        this.borderStripes = stripes;
    }

    clearBorderStripes() {
        this.borderStripes = null;
    }

    /**
     * Render one complete frame: border + display area.
     */
    renderFrame() {
        const fb = this.fb;
        const data = this.pixels;

        if (this.borderStripes) {
            // Per-scanline border colours (tape loading stripes)
            for (let y = 0; y < CANVAS_H; y++) {
                const rgb = PALETTE[0][this.borderStripes[y] & 7];
                const rowStart = y * CANVAS_W * 4;
                for (let x = 0; x < CANVAS_W; x++) {
                    const idx = rowStart + x * 4;
                    data[idx]     = rgb[0];
                    data[idx + 1] = rgb[1];
                    data[idx + 2] = rgb[2];
                    data[idx + 3] = 255;
                }
            }
        } else {
            // Solid border colour
            const borderRGB = PALETTE[0][this.borderColour];
            for (let i = 0; i < CANVAS_W * CANVAS_H; i++) {
                const idx = i * 4;
                data[idx]     = borderRGB[0];
                data[idx + 1] = borderRGB[1];
                data[idx + 2] = borderRGB[2];
                data[idx + 3] = 255;
            }
        }

        // Render the 256x192 display area within the border
        for (let y = 0; y < SCREEN_H; y++) {
            const charRow = y >> 3;
            for (let col = 0; col < CHAR_COLS; col++) {
                // Read pixel byte from interleaved buffer
                const pixByte = fb.pixelBuffer[fb.pixelAddress(col * 8, y)];

                // Read attribute for this cell
                const attrByte = fb.attributeBuffer[charRow * CHAR_COLS + col];
                const flash  = (attrByte >> 7) & 1;
                const bright = (attrByte >> 6) & 1;
                let paper    = (attrByte >> 3) & 7;
                let ink      = attrByte & 7;

                // Handle FLASH
                if (flash && this.flashPhase) {
                    const tmp = ink; ink = paper; paper = tmp;
                }

                const inkRGB   = PALETTE[bright][ink];
                const paperRGB = PALETTE[bright][paper];

                // Write 8 pixels
                for (let bit = 7; bit >= 0; bit--) {
                    const px = col * 8 + (7 - bit);
                    const screenX = BORDER_SIZE + px;
                    const screenY = BORDER_SIZE + y;
                    const idx = (screenY * CANVAS_W + screenX) * 4;

                    const isInk = (pixByte >> bit) & 1;
                    const rgb = isInk ? inkRGB : paperRGB;
                    data[idx]     = rgb[0];
                    data[idx + 1] = rgb[1];
                    data[idx + 2] = rgb[2];
                    data[idx + 3] = 255;
                }
            }
        }

        // Put native image data onto offscreen canvas
        this.nativeCtx.putImageData(this.imageData, 0, 0);

        // Scale up to output canvas with nearest-neighbour
        this.ctx.imageSmoothingEnabled = false;
        this.ctx.drawImage(
            this.nativeCanvas,
            0, 0, CANVAS_W, CANVAS_H,
            0, 0, CANVAS_W * this.scale, CANVAS_H * this.scale
        );
    }
}
