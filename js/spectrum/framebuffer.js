import {
    PIXEL_BUFFER_SIZE, ATTR_BUFFER_SIZE,
    SCREEN_W, SCREEN_H, CHAR_COLS, CHAR_ROWS
} from './constants.js';

/**
 * ZX Spectrum video RAM emulation.
 *
 * The pixel buffer uses the Spectrum's famous interleaved memory layout:
 *   Address bits: [third(2)][pixelRow(3)][charRow(3)][column(5)]
 *
 * The attribute buffer is a simple linear 32x24 array:
 *   Bit 7: FLASH, Bit 6: BRIGHT, Bits 5-3: PAPER, Bits 2-0: INK
 */
export class Framebuffer {
    constructor() {
        this.pixelBuffer = new Uint8Array(PIXEL_BUFFER_SIZE);
        this.attributeBuffer = new Uint8Array(ATTR_BUFFER_SIZE);
    }

    /**
     * Convert (x, y) pixel coordinate to interleaved buffer offset.
     * x: 0-255, y: 0-191
     * Returns byte offset into pixelBuffer (the byte containing this pixel).
     */
    pixelAddress(x, y) {
        const third    = (y >> 6) & 3;    // Which third (0-2)
        const charRow  = (y >> 3) & 7;    // Character row within third (0-7)
        const pixelRow = y & 7;           // Pixel row within character cell (0-7)
        const col      = x >> 3;          // Byte column (0-31)
        return (third << 11) | (pixelRow << 8) | (charRow << 5) | col;
    }

    /**
     * Convert (charCol, charRow) to attribute buffer offset.
     */
    attrAddress(charCol, charRow) {
        return charRow * CHAR_COLS + charCol;
    }

    /**
     * Set a single pixel. x: 0-255, y: 0-191, on: true/false
     */
    setPixel(x, y, on) {
        if (x < 0 || x >= SCREEN_W || y < 0 || y >= SCREEN_H) return;
        const addr = this.pixelAddress(x, y);
        const bit = 7 - (x & 7);
        if (on) {
            this.pixelBuffer[addr] |= (1 << bit);
        } else {
            this.pixelBuffer[addr] &= ~(1 << bit);
        }
    }

    /**
     * Get a single pixel value. Returns true if INK, false if PAPER.
     */
    getPixel(x, y) {
        if (x < 0 || x >= SCREEN_W || y < 0 || y >= SCREEN_H) return false;
        const addr = this.pixelAddress(x, y);
        const bit = 7 - (x & 7);
        return (this.pixelBuffer[addr] & (1 << bit)) !== 0;
    }

    /**
     * Write a full byte (8 horizontal pixels) at the given byte column and y row.
     * col: 0-31, y: 0-191
     */
    setByte(col, y, value) {
        const addr = this.pixelAddress(col * 8, y);
        this.pixelBuffer[addr] = value;
    }

    /**
     * Set attribute for a character cell.
     * charCol: 0-31, charRow: 0-23
     * ink: 0-7, paper: 0-7, bright: 0/1, flash: 0/1
     */
    setAttr(charCol, charRow, ink, paper, bright = 0, flash = 0) {
        const addr = this.attrAddress(charCol, charRow);
        this.attributeBuffer[addr] =
            (flash << 7) | (bright << 6) | (paper << 3) | ink;
    }

    /**
     * Get attribute for a character cell. Returns { ink, paper, bright, flash }.
     */
    getAttr(charCol, charRow) {
        const byte = this.attributeBuffer[this.attrAddress(charCol, charRow)];
        return {
            ink:    byte & 7,
            paper:  (byte >> 3) & 7,
            bright: (byte >> 6) & 1,
            flash:  (byte >> 7) & 1,
        };
    }

    /**
     * Set attribute byte directly at a character cell position.
     */
    setAttrByte(charCol, charRow, byte) {
        this.attributeBuffer[this.attrAddress(charCol, charRow)] = byte;
    }

    /**
     * Clear the entire screen (pixels + attributes).
     * Sets all pixels off, all attributes to ink on paper with given brightness.
     */
    clear(ink = 0, paper = 0, bright = 0) {
        this.pixelBuffer.fill(0);
        const attr = (bright << 6) | (paper << 3) | ink;
        this.attributeBuffer.fill(attr);
    }
}
