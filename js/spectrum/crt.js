import { CANVAS_W, CANVAS_H } from './constants.js';

/**
 * CRT post-processing effects.
 * Applies scanlines, phosphor glow, and optional RGB separation
 * to make the output look like a real CRT monitor.
 */
export class CRT {
    constructor(sourceCanvas, scale) {
        this.sourceCanvas = sourceCanvas;
        this.scale = scale;
        this.w = CANVAS_W * scale;
        this.h = CANVAS_H * scale;

        // Output canvas (replaces the source on screen)
        this.canvas = document.createElement('canvas');
        this.canvas.width = this.w;
        this.canvas.height = this.h;
        this.canvas.id = 'crt-output';
        this.ctx = this.canvas.getContext('2d');

        // Glow layer (blurred copy)
        this.glowCanvas = document.createElement('canvas');
        this.glowCanvas.width = this.w;
        this.glowCanvas.height = this.h;
        this.glowCtx = this.glowCanvas.getContext('2d');

        // Pre-rendered scanline overlay
        this.scanlineCanvas = document.createElement('canvas');
        this.scanlineCanvas.width = this.w;
        this.scanlineCanvas.height = this.h;
        this._createScanlines();

        // Replace source canvas in DOM
        this.sourceCanvas.parentNode.insertBefore(this.canvas, this.sourceCanvas);
        this.sourceCanvas.style.display = 'none';
    }

    /**
     * Pre-render the scanline pattern.
     * Every other row of scaled pixels gets darkened.
     */
    _createScanlines() {
        const ctx = this.scanlineCanvas.getContext('2d');

        // Fill white (multiply blend: white = no change)
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, this.w, this.h);

        // Dark bands on even rows — creates the scanline gap effect
        // At 3x scale, each Spectrum pixel row is 3 screen rows.
        // We darken 1 out of every 3 rows for subtle scanlines,
        // or 1 out of every 2 for more pronounced effect.
        ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
        for (let y = 0; y < this.h; y += 2) {
            ctx.fillRect(0, y, this.w, 1);
        }
    }

    /**
     * Apply all CRT effects to the current frame.
     * Call this after the renderer has drawn to sourceCanvas.
     */
    applyEffects() {
        const ctx = this.ctx;

        // Step 1: Draw the sharp source image
        ctx.drawImage(this.sourceCanvas, 0, 0);

        // Step 2: Create phosphor glow (blurred, brightened copy)
        this.glowCtx.filter = 'blur(4px) brightness(1.3)';
        this.glowCtx.drawImage(this.sourceCanvas, 0, 0);
        this.glowCtx.filter = 'none';

        // Step 3: Composite the glow layer (additive blend)
        ctx.globalAlpha = 0.12;
        ctx.globalCompositeOperation = 'lighter';
        ctx.drawImage(this.glowCanvas, 0, 0);

        // Step 4: Apply scanline overlay (multiply blend)
        ctx.globalAlpha = 1.0;
        ctx.globalCompositeOperation = 'multiply';
        ctx.drawImage(this.scanlineCanvas, 0, 0);

        // Reset composite mode
        ctx.globalCompositeOperation = 'source-over';
        ctx.globalAlpha = 1.0;
    }
}
