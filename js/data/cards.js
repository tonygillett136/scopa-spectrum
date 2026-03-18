/**
 * cards.js - Card sprite data for 40-card Italian Napoletane deck
 *
 * Uses pre-converted digitized sprites from card-sprites.js (generated
 * by tools/convert_cards.py from real card photographs).
 *
 * Each card is 80x128 pixels (10x16 character cells).
 * Pixel data: 10 bytes/row x 128 rows = 1280 bytes (MSB = leftmost pixel)
 * Attribute data: 10 cols x 16 rows = 160 bytes, each = (flash<<7)|(bright<<6)|(paper<<3)|ink
 */

import { CARD_SPRITE_DATA } from './card-sprites.js';

// ============================================================
// Card dimension constants
// ============================================================
export const CARD_W = 80;
export const CARD_H = 128;
export const CARD_COLS = 10;
export const CARD_ROWS = 16;

const BPR = 10; // bytes per row in pixel buffer
const PIXEL_SIZE = BPR * CARD_H; // 1280 bytes
const ATTR_SIZE = CARD_COLS * CARD_ROWS; // 160 bytes

// Suit constants
export const SUIT_COPPE = 0;
export const SUIT_DENARI = 1;
export const SUIT_BASTONI = 2;
export const SUIT_SPADE = 3;

// Suit names for display
export const SUIT_NAMES = ['Coppe', 'Denari', 'Bastoni', 'Spade'];
export const VALUE_NAMES = ['', 'Asso', 'Due', 'Tre', 'Quattro', 'Cinque', 'Sei', 'Sette', 'Fante', 'Cavallo', 'Re'];

// ============================================================
// Card back constants
// ============================================================
const CARD_BACK_ATTR = 0x0A; // RED(2) on BLUE(1)

// ============================================================
// Base64 decode helper
// ============================================================
function b64ToUint8Array(b64) {
    const bin = atob(b64);
    const arr = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) {
        arr[i] = bin.charCodeAt(i);
    }
    return arr;
}

// ============================================================
// Card back (10x16 with ornate lattice + central medallion)
// ============================================================

function setPixel(buf, x, y, on) {
    if (x < 0 || x >= CARD_W || y < 0 || y >= CARD_H) return;
    const byteIndex = y * BPR + (x >> 3);
    const bitMask = 0x80 >> (x & 7);
    if (on) buf[byteIndex] |= bitMask;
    else buf[byteIndex] &= ~bitMask;
}

function drawHLine(buf, x1, x2, y) {
    for (let x = x1; x <= x2; x++) setPixel(buf, x, y, 1);
}

function drawVLine(buf, x, y1, y2) {
    for (let y = y1; y <= y2; y++) setPixel(buf, x, y, 1);
}

function drawRect(buf, x, y, w, h) {
    drawHLine(buf, x, x + w - 1, y);
    drawHLine(buf, x, x + w - 1, y + h - 1);
    drawVLine(buf, x, y, y + h - 1);
    drawVLine(buf, x + w - 1, y, y + h - 1);
}

function drawLine(buf, x1, y1, x2, y2) {
    const dx = Math.abs(x2 - x1);
    const dy = Math.abs(y2 - y1);
    const sx = x1 < x2 ? 1 : -1;
    const sy = y1 < y2 ? 1 : -1;
    let err = dx - dy;
    let x = x1, y = y1;
    while (true) {
        setPixel(buf, x, y, 1);
        if (x === x2 && y === y2) break;
        const e2 = 2 * err;
        if (e2 > -dy) { err -= dy; x += sx; }
        if (e2 < dx) { err += dx; y += sy; }
    }
}

function buildCardBackPixels() {
    const buf = new Uint8Array(PIXEL_SIZE);

    // Outer border with rounded corners
    drawHLine(buf, 3, 76, 0);
    drawHLine(buf, 1, 78, 1);
    drawHLine(buf, 1, 78, 126);
    drawHLine(buf, 3, 76, 127);
    for (let y = 2; y < 126; y++) {
        setPixel(buf, 0, y, 1);
        setPixel(buf, 79, y, 1);
    }
    // Corner rounding
    setPixel(buf, 1, 0, 0); setPixel(buf, 2, 0, 0);
    setPixel(buf, 77, 0, 0); setPixel(buf, 78, 0, 0);
    setPixel(buf, 1, 127, 0); setPixel(buf, 2, 127, 0);
    setPixel(buf, 77, 127, 0); setPixel(buf, 78, 127, 0);

    // Inner decorative border
    drawRect(buf, 4, 4, 72, 120);

    // Second inner border
    drawRect(buf, 7, 7, 66, 114);

    // Diamond lattice fill
    for (let y = 9; y < 119; y++) {
        for (let x = 9; x < 71; x++) {
            const sum = (x + y) % 4;
            const diff = ((x - y) % 4 + 4) % 4;
            if (sum === 0 || diff === 0) {
                setPixel(buf, x, y, 1);
            }
        }
    }

    // Central medallion (clear oval area)
    const mcx = 40, mcy = 64;
    const mrx = 14, mry = 20;
    for (let dy = -mry; dy <= mry; dy++) {
        for (let dx = -mrx; dx <= mrx; dx++) {
            const d = (dx * dx) / (mrx * mrx) + (dy * dy) / (mry * mry);
            if (d <= 1.0) {
                setPixel(buf, mcx + dx, mcy + dy, 0);
            }
        }
    }
    // Medallion border
    for (let dy = -mry; dy <= mry; dy++) {
        for (let dx = -mrx; dx <= mrx; dx++) {
            const d = (dx * dx) / (mrx * mrx) + (dy * dy) / (mry * mry);
            if (d <= 1.0 && d >= 0.82) {
                setPixel(buf, mcx + dx, mcy + dy, 1);
            }
        }
    }
    // Cross in medallion
    drawHLine(buf, mcx - 10, mcx + 10, mcy);
    drawVLine(buf, mcx, mcy - 16, mcy + 16);
    // Diamond shape
    const dpts = [[mcx, mcy - 14], [mcx + 10, mcy], [mcx, mcy + 14], [mcx - 10, mcy]];
    for (let i = 0; i < 4; i++) {
        const [x1, y1] = dpts[i];
        const [x2, y2] = dpts[(i + 1) % 4];
        drawLine(buf, x1, y1, x2, y2);
    }

    return buf;
}

// ============================================================
// Card border (1px outline with rounded corners)
// ============================================================

function applyCardBorder(pixels, attrs) {
    // Clear corner areas to paper (rounded corners)
    // Top-left
    setPixel(pixels, 0, 0, 0); setPixel(pixels, 1, 0, 0); setPixel(pixels, 2, 0, 0);
    setPixel(pixels, 0, 1, 0); setPixel(pixels, 1, 1, 0);
    setPixel(pixels, 0, 2, 0);
    // Top-right
    setPixel(pixels, 79, 0, 0); setPixel(pixels, 78, 0, 0); setPixel(pixels, 77, 0, 0);
    setPixel(pixels, 79, 1, 0); setPixel(pixels, 78, 1, 0);
    setPixel(pixels, 79, 2, 0);
    // Bottom-left
    setPixel(pixels, 0, 127, 0); setPixel(pixels, 1, 127, 0); setPixel(pixels, 2, 127, 0);
    setPixel(pixels, 0, 126, 0); setPixel(pixels, 1, 126, 0);
    setPixel(pixels, 0, 125, 0);
    // Bottom-right
    setPixel(pixels, 79, 127, 0); setPixel(pixels, 78, 127, 0); setPixel(pixels, 77, 127, 0);
    setPixel(pixels, 79, 126, 0); setPixel(pixels, 78, 126, 0);
    setPixel(pixels, 79, 125, 0);

    // Draw 1-pixel border outline
    // Top edge (row 0)
    drawHLine(pixels, 3, 76, 0);
    // Bottom edge (row 127)
    drawHLine(pixels, 3, 76, 127);
    // Corner curves
    setPixel(pixels, 2, 1, 1); setPixel(pixels, 77, 1, 1);
    setPixel(pixels, 1, 2, 1); setPixel(pixels, 78, 2, 1);
    setPixel(pixels, 2, 126, 1); setPixel(pixels, 77, 126, 1);
    setPixel(pixels, 1, 125, 1); setPixel(pixels, 78, 125, 1);
    // Straight sides (rows 3-124)
    for (let y = 3; y <= 124; y++) {
        setPixel(pixels, 0, y, 1);
        setPixel(pixels, 79, y, 1);
    }

    // Set corner cell attributes to BLACK on WHITE for clean rounded look
    const BORDER_ATTR = 0x38; // BLACK ink, WHITE paper, no bright
    attrs[0] = BORDER_ATTR;                                 // top-left cell
    attrs[CARD_COLS - 1] = BORDER_ATTR;                     // top-right cell
    attrs[(CARD_ROWS - 1) * CARD_COLS] = BORDER_ATTR;       // bottom-left cell
    attrs[CARD_ROWS * CARD_COLS - 1] = BORDER_ATTR;         // bottom-right cell
}

// ============================================================
// Sprite cache & public API
// ============================================================
const spriteCache = new Map();

function cacheKey(suit, value) {
    return (suit << 8) | value;
}

/**
 * Get the rendering data for a specific card.
 * @param {number} suit - 0-3
 * @param {number} value - 1-10
 * @returns {{ pixels: Uint8Array, attrs: Uint8Array }}
 */
export function getCardSprite(suit, value) {
    const key = cacheKey(suit, value);
    if (spriteCache.has(key)) return spriteCache.get(key);

    const dataKey = `${suit}_${value}`;
    const data = CARD_SPRITE_DATA[dataKey];

    let result;
    if (data) {
        const pixels = b64ToUint8Array(data.p);
        const attrs = b64ToUint8Array(data.a);
        applyCardBorder(pixels, attrs);
        result = { pixels, attrs };
    } else {
        // Fallback: empty card with border
        result = {
            pixels: buildCardBackPixels(),
            attrs: new Uint8Array(ATTR_SIZE).fill(0x38), // BLACK on WHITE
        };
    }

    spriteCache.set(key, result);
    return result;
}

/**
 * Get the rendering data for the card back.
 * @returns {{ pixels: Uint8Array, attrs: Uint8Array }}
 */
export function getCardBack() {
    const key = 'back';
    if (spriteCache.has(key)) return spriteCache.get(key);

    const attrs = new Uint8Array(ATTR_SIZE);
    attrs.fill(CARD_BACK_ATTR);

    const result = {
        pixels: buildCardBackPixels(),
        attrs,
    };

    spriteCache.set(key, result);
    return result;
}
