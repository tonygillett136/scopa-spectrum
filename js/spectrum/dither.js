/**
 * dither.js - Ordered dithering utilities for ZX Spectrum card art
 *
 * Uses Bayer 8x8 matrix to create ~17 perceptual tone levels within
 * the Spectrum's 2-color-per-cell constraint. Ink pixels represent
 * "dark" and paper pixels represent "light" — the actual colors are
 * set separately via attributes.
 */

// Standard 8x8 Bayer ordered dither matrix (values 0-63)
const BAYER_8x8 = [
    [ 0, 32,  8, 40,  2, 34, 10, 42],
    [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44,  4, 36, 14, 46,  6, 38],
    [60, 28, 52, 20, 62, 30, 54, 22],
    [ 3, 35, 11, 43,  1, 33,  9, 41],
    [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47,  7, 39, 13, 45,  5, 37],
    [63, 31, 55, 23, 61, 29, 53, 21],
];

/**
 * Generate 8 bytes for one 8x8 character cell at a given shade level.
 * @param {number} shade - 0.0 = all paper (light), 1.0 = all ink (dark)
 * @returns {Uint8Array} 8 bytes, one per row of the cell
 */
export function ditherCell(shade) {
    const threshold = Math.round(shade * 64);
    const bytes = new Uint8Array(8);
    for (let row = 0; row < 8; row++) {
        let byte = 0;
        for (let col = 0; col < 8; col++) {
            if (BAYER_8x8[row][col] < threshold) {
                byte |= (0x80 >> col);
            }
        }
        bytes[row] = byte;
    }
    return bytes;
}

/**
 * Stamp a dithered fill into a card sprite pixel buffer at a given cell position.
 * @param {Uint8Array} buf - Card pixel buffer
 * @param {number} bpr - Bytes per row in the buffer
 * @param {number} cellX - Character cell column (0-based within card)
 * @param {number} cellY - Character cell row (0-based within card)
 * @param {number} shade - 0.0 = all paper, 1.0 = all ink
 */
export function ditherRect(buf, bpr, cellX, cellY, shade) {
    const cell = ditherCell(shade);
    const px = cellX; // byte column in buffer
    const py = cellY * 8; // pixel row
    for (let row = 0; row < 8; row++) {
        const bufIdx = (py + row) * bpr + px;
        buf[bufIdx] |= cell[row];
    }
}

/**
 * Fill a rectangular region of cells with a uniform dither shade.
 * @param {Uint8Array} buf - Card pixel buffer
 * @param {number} bpr - Bytes per row
 * @param {number} cellX - Start cell column
 * @param {number} cellY - Start cell row
 * @param {number} cellW - Width in cells
 * @param {number} cellH - Height in cells
 * @param {number} shade - 0.0-1.0
 */
export function ditherFillRect(buf, bpr, cellX, cellY, cellW, cellH, shade) {
    const cell = ditherCell(shade);
    for (let cy = 0; cy < cellH; cy++) {
        for (let cx = 0; cx < cellW; cx++) {
            const px = cellX + cx;
            const py = (cellY + cy) * 8;
            for (let row = 0; row < 8; row++) {
                const bufIdx = (py + row) * bpr + px;
                buf[bufIdx] |= cell[row];
            }
        }
    }
}

/**
 * Create a vertical gradient across multiple cells in a single column.
 * @param {Uint8Array} buf - Card pixel buffer
 * @param {number} bpr - Bytes per row
 * @param {number} cellX - Cell column
 * @param {number} startCellY - Starting cell row
 * @param {number} shadeTop - Shade at top (0.0-1.0)
 * @param {number} shadeBot - Shade at bottom (0.0-1.0)
 * @param {number} numCells - Number of cells in the gradient
 */
export function ditherGradientV(buf, bpr, cellX, startCellY, shadeTop, shadeBot, numCells) {
    for (let i = 0; i < numCells; i++) {
        const t = numCells > 1 ? i / (numCells - 1) : 0;
        const shade = shadeTop + (shadeBot - shadeTop) * t;
        ditherRect(buf, bpr, cellX, startCellY + i, shade);
    }
}

/**
 * Create a vertical gradient across multiple cells spanning multiple columns.
 * @param {Uint8Array} buf - Card pixel buffer
 * @param {number} bpr - Bytes per row
 * @param {number} cellX - Start cell column
 * @param {number} cellW - Width in cells
 * @param {number} startCellY - Starting cell row
 * @param {number} shadeTop - Shade at top
 * @param {number} shadeBot - Shade at bottom
 * @param {number} numCells - Number of cell rows
 */
export function ditherGradientVWide(buf, bpr, cellX, cellW, startCellY, shadeTop, shadeBot, numCells) {
    for (let cx = 0; cx < cellW; cx++) {
        ditherGradientV(buf, bpr, cellX + cx, startCellY, shadeTop, shadeBot, numCells);
    }
}

/**
 * Stamp a dithered circular/radial fill into a pixel buffer.
 * Draws pixel-by-pixel with radial shading from center to edge.
 * @param {Uint8Array} buf - Card pixel buffer
 * @param {number} bpr - Bytes per row
 * @param {number} cx - Center X in pixels
 * @param {number} cy - Center Y in pixels
 * @param {number} radius - Radius in pixels
 * @param {number} shadeInner - Shade at center
 * @param {number} shadeOuter - Shade at edge
 */
export function ditherCircle(buf, bpr, cx, cy, radius, shadeInner, shadeOuter) {
    const r2 = radius * radius;
    for (let dy = -radius; dy <= radius; dy++) {
        for (let dx = -radius; dx <= radius; dx++) {
            const dist2 = dx * dx + dy * dy;
            if (dist2 > r2) continue;

            const px = cx + dx;
            const py = cy + dy;
            if (px < 0 || py < 0) continue;

            const dist = Math.sqrt(dist2);
            const t = dist / radius;
            const shade = shadeInner + (shadeOuter - shadeInner) * t;
            const threshold = Math.round(shade * 64);

            // Use Bayer matrix at the pixel's position within its cell
            const bayerVal = BAYER_8x8[py & 7][px & 7];
            if (bayerVal < threshold) {
                // Set pixel as ink
                const byteCol = px >> 3;
                const bitPos = 7 - (px & 7);
                const bufIdx = py * bpr + byteCol;
                if (bufIdx >= 0 && bufIdx < buf.length) {
                    buf[bufIdx] |= (1 << bitPos);
                }
            }
        }
    }
}

/**
 * Set a single pixel in a card buffer using dithered threshold.
 * Useful for per-pixel shading effects.
 * @param {Uint8Array} buf - Card pixel buffer
 * @param {number} bpr - Bytes per row
 * @param {number} x - Pixel X
 * @param {number} y - Pixel Y
 * @param {number} shade - 0.0-1.0
 */
export function ditherPixel(buf, bpr, x, y, shade) {
    const threshold = Math.round(shade * 64);
    const bayerVal = BAYER_8x8[y & 7][x & 7];
    if (bayerVal < threshold) {
        const byteCol = x >> 3;
        const bitPos = 7 - (x & 7);
        const bufIdx = y * bpr + byteCol;
        if (bufIdx >= 0 && bufIdx < buf.length) {
            buf[bufIdx] |= (1 << bitPos);
        }
    }
}

/**
 * Fill a pixel-level rectangle with dithered shading.
 * More precise than cell-based ditherFillRect — works at arbitrary coords.
 * @param {Uint8Array} buf - Card pixel buffer
 * @param {number} bpr - Bytes per row
 * @param {number} x - Top-left pixel X
 * @param {number} y - Top-left pixel Y
 * @param {number} w - Width in pixels
 * @param {number} h - Height in pixels
 * @param {number} shade - 0.0-1.0
 */
export function ditherPixelRect(buf, bpr, x, y, w, h, shade) {
    const threshold = Math.round(shade * 64);
    for (let py = y; py < y + h; py++) {
        for (let px = x; px < x + w; px++) {
            const bayerVal = BAYER_8x8[py & 7][px & 7];
            if (bayerVal < threshold) {
                const byteCol = px >> 3;
                const bitPos = 7 - (px & 7);
                const bufIdx = py * bpr + byteCol;
                if (bufIdx >= 0 && bufIdx < buf.length) {
                    buf[bufIdx] |= (1 << bitPos);
                }
            }
        }
    }
}
