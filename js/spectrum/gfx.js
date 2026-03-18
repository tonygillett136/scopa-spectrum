import { FONT_DATA } from './font.js';
import { SCREEN_W, SCREEN_H, CHAR_COLS, CHAR_ROWS, CELL_SIZE } from './constants.js';

/**
 * Graphics primitives for the ZX Spectrum framebuffer.
 * Provides BASIC-like drawing functions: PRINT, PLOT, DRAW, etc.
 */
export class Gfx {
    constructor(framebuffer) {
        this.fb = framebuffer;

        // Current drawing state (like Spectrum system variables)
        this.currentInk = 7;    // white
        this.currentPaper = 0;  // black
        this.currentBright = 0;
        this.currentFlash = 0;

        // Print position (character coordinates)
        this.printCol = 0;
        this.printRow = 0;
    }

    // --- Colour state ---

    ink(colour) {
        this.currentInk = colour & 7;
    }

    paper(colour) {
        this.currentPaper = colour & 7;
    }

    bright(flag) {
        this.currentBright = flag ? 1 : 0;
    }

    flash(flag) {
        this.currentFlash = flag ? 1 : 0;
    }

    /**
     * Build an attribute byte from current state.
     */
    currentAttrByte() {
        return (this.currentFlash << 7) |
               (this.currentBright << 6) |
               (this.currentPaper << 3) |
               this.currentInk;
    }

    // --- Screen operations ---

    /**
     * Clear screen with current ink/paper/bright.
     */
    cls() {
        this.fb.clear(this.currentInk, this.currentPaper, this.currentBright);
        this.printCol = 0;
        this.printRow = 0;
    }

    // --- Pixel operations ---

    /**
     * Set a pixel (INK colour). x: 0-255, y: 0-191
     */
    plot(x, y) {
        this.fb.setPixel(x, y, true);
        // Set the attribute for the cell this pixel falls in
        const cc = x >> 3;
        const cr = y >> 3;
        this.fb.setAttrByte(cc, cr, this.currentAttrByte());
    }

    /**
     * Clear a pixel (PAPER colour). x: 0-255, y: 0-191
     */
    unplot(x, y) {
        this.fb.setPixel(x, y, false);
    }

    /**
     * Draw a line from (x0,y0) to (x1,y1) using Bresenham's algorithm.
     */
    drawLine(x0, y0, x1, y1) {
        let dx = Math.abs(x1 - x0);
        let dy = Math.abs(y1 - y0);
        let sx = x0 < x1 ? 1 : -1;
        let sy = y0 < y1 ? 1 : -1;
        let err = dx - dy;

        while (true) {
            this.plot(x0, y0);
            if (x0 === x1 && y0 === y1) break;
            const e2 = 2 * err;
            if (e2 > -dy) { err -= dy; x0 += sx; }
            if (e2 < dx)  { err += dx; y0 += sy; }
        }
    }

    // --- Rectangle operations ---

    /**
     * Draw a rectangle outline. x, y in pixels; w, h in pixels.
     */
    rect(x, y, w, h) {
        this.drawLine(x, y, x + w - 1, y);
        this.drawLine(x + w - 1, y, x + w - 1, y + h - 1);
        this.drawLine(x + w - 1, y + h - 1, x, y + h - 1);
        this.drawLine(x, y + h - 1, x, y);
    }

    /**
     * Fill a rectangle with INK pixels. x, y, w, h in pixels.
     * Also sets attributes for all cells covered.
     */
    fillRect(x, y, w, h) {
        for (let py = y; py < y + h && py < SCREEN_H; py++) {
            for (let px = x; px < x + w && px < SCREEN_W; px++) {
                if (px >= 0 && py >= 0) {
                    this.fb.setPixel(px, py, true);
                }
            }
        }
        // Set attributes for all covered cells
        const cc0 = Math.max(0, x >> 3);
        const cr0 = Math.max(0, y >> 3);
        const cc1 = Math.min(CHAR_COLS - 1, (x + w - 1) >> 3);
        const cr1 = Math.min(CHAR_ROWS - 1, (y + h - 1) >> 3);
        const attr = this.currentAttrByte();
        for (let cr = cr0; cr <= cr1; cr++) {
            for (let cc = cc0; cc <= cc1; cc++) {
                this.fb.setAttrByte(cc, cr, attr);
            }
        }
    }

    /**
     * Fill a rectangle region with PAPER (clear pixels).
     * Sets attributes for all covered cells.
     */
    clearRect(x, y, w, h) {
        for (let py = y; py < y + h && py < SCREEN_H; py++) {
            for (let px = x; px < x + w && px < SCREEN_W; px++) {
                if (px >= 0 && py >= 0) {
                    this.fb.setPixel(px, py, false);
                }
            }
        }
        const cc0 = Math.max(0, x >> 3);
        const cr0 = Math.max(0, y >> 3);
        const cc1 = Math.min(CHAR_COLS - 1, (x + w - 1) >> 3);
        const cr1 = Math.min(CHAR_ROWS - 1, (y + h - 1) >> 3);
        const attr = this.currentAttrByte();
        for (let cr = cr0; cr <= cr1; cr++) {
            for (let cc = cc0; cc <= cc1; cc++) {
                this.fb.setAttrByte(cc, cr, attr);
            }
        }
    }

    // --- Text operations ---

    /**
     * Set the print position (character coordinates).
     */
    printAt(row, col) {
        this.printRow = row;
        this.printCol = col;
    }

    /**
     * Print a string at the current print position using the Spectrum ROM font.
     * Advances the cursor. Wraps at line end.
     */
    print(text) {
        for (let i = 0; i < text.length; i++) {
            const ch = text.charCodeAt(i);

            if (ch === 10) {
                // Newline
                this.printCol = 0;
                this.printRow++;
                continue;
            }

            if (this.printCol >= CHAR_COLS) {
                this.printCol = 0;
                this.printRow++;
            }
            if (this.printRow >= CHAR_ROWS) {
                break; // No scroll for now
            }

            this.printChar(this.printCol, this.printRow, ch);
            this.printCol++;
        }
    }

    /**
     * Print a string at a specific character position.
     */
    printAtStr(row, col, text) {
        this.printAt(row, col);
        this.print(text);
    }

    /**
     * Print a single character at character position (col, row).
     * Sets both pixels and attributes for that cell.
     */
    printChar(col, row, charCode) {
        if (col < 0 || col >= CHAR_COLS || row < 0 || row >= CHAR_ROWS) return;

        // Clamp to printable range (32-127)
        const fontIndex = charCode - 32;
        if (fontIndex < 0 || fontIndex >= 96) return;

        const fontOffset = fontIndex * 8;
        const px = col * CELL_SIZE;
        const py = row * CELL_SIZE;

        // Write 8 rows of 8 pixels
        for (let r = 0; r < 8; r++) {
            const fontByte = FONT_DATA[fontOffset + r];
            // Write entire byte at once
            this.fb.setByte(col, py + r, fontByte);
        }

        // Set attribute for this cell
        this.fb.setAttrByte(col, row, this.currentAttrByte());
    }

    /**
     * Draw a sprite (array of bytes, 1 byte = 8 horizontal pixels) at pixel position.
     * widthCells: width in character cells (each cell = 8 pixels = 1 byte)
     * heightPx: height in pixels
     * data: Uint8Array of widthCells * heightPx bytes
     */
    drawSprite(x, y, widthCells, heightPx, data) {
        const startCol = x >> 3;
        let idx = 0;
        for (let py = 0; py < heightPx; py++) {
            for (let c = 0; c < widthCells; c++) {
                if (startCol + c < CHAR_COLS && y + py < SCREEN_H) {
                    this.fb.setByte(startCol + c, y + py, data[idx]);
                }
                idx++;
            }
        }
    }

    /**
     * Set attributes for a rectangular region of character cells.
     * Uses the current ink/paper/bright/flash state.
     */
    setAttrRegion(col, row, widthCells, heightCells) {
        const attr = this.currentAttrByte();
        for (let r = row; r < row + heightCells && r < CHAR_ROWS; r++) {
            for (let c = col; c < col + widthCells && c < CHAR_COLS; c++) {
                if (c >= 0 && r >= 0) {
                    this.fb.setAttrByte(c, r, attr);
                }
            }
        }
    }
}
