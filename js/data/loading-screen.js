// ZX Spectrum Loading Screen Generator for SCOPA
// Generates a 6912-byte screen: 6144 bytes pixel data + 768 bytes attributes
//
// Spectrum display: 256x192 pixels, 32x24 character cells (8x8 each)
// Pixel memory uses interleaved layout in 3 "thirds" of 64 rows each.
// Attribute byte: bit7=FLASH, bit6=BRIGHT, bits5-3=PAPER(0-7), bits2-0=INK(0-7)

// Spectrum colour indices
const BLACK = 0;
const BLUE = 1;
const RED = 2;
const MAGENTA = 3;
const GREEN = 4;
const CYAN = 5;
const YELLOW = 6;
const WHITE = 7;

/**
 * Convert a pixel coordinate to the Spectrum's interleaved byte address.
 */
function pixelAddress(x, y) {
    const third = (y >> 6) & 3;
    const charRow = (y >> 3) & 7;
    const pixelRow = y & 7;
    const col = x >> 3;
    return (third << 11) | (pixelRow << 8) | (charRow << 5) | col;
}

/**
 * Build an attribute byte from components.
 */
function attr(ink, paper, bright, flash) {
    return ((flash ? 1 : 0) << 7) | ((bright ? 1 : 0) << 6) | ((paper & 7) << 3) | (ink & 7);
}

/**
 * Generate the complete loading screen.
 */
function generateLoadingScreen() {
    // Linear pixel canvas: 1 byte per pixel (0=off/paper, 1=on/ink)
    const linear = new Uint8Array(256 * 192);
    // Attribute grid: 32 columns x 24 rows
    const attrs = new Uint8Array(768);

    // --- Drawing primitives ---

    function setPixel(x, y) {
        if (x >= 0 && x < 256 && y >= 0 && y < 192) {
            linear[y * 256 + x] = 1;
        }
    }

    function clearPixel(x, y) {
        if (x >= 0 && x < 256 && y >= 0 && y < 192) {
            linear[y * 256 + x] = 0;
        }
    }

    function getPixel(x, y) {
        if (x >= 0 && x < 256 && y >= 0 && y < 192) {
            return linear[y * 256 + x];
        }
        return 0;
    }

    function fillRect(x0, y0, w, h) {
        for (let dy = 0; dy < h; dy++) {
            for (let dx = 0; dx < w; dx++) {
                setPixel(x0 + dx, y0 + dy);
            }
        }
    }

    function drawHLine(x0, x1, y) {
        for (let x = x0; x <= x1; x++) {
            setPixel(x, y);
        }
    }

    function drawVLine(x, y0, y1) {
        for (let y = y0; y <= y1; y++) {
            setPixel(x, y);
        }
    }

    function drawCircle(cx, cy, r) {
        // Midpoint circle algorithm
        let x = r;
        let y = 0;
        let d = 1 - r;
        while (x >= y) {
            setPixel(cx + x, cy + y);
            setPixel(cx - x, cy + y);
            setPixel(cx + x, cy - y);
            setPixel(cx - x, cy - y);
            setPixel(cx + y, cy + x);
            setPixel(cx - y, cy + x);
            setPixel(cx + y, cy - x);
            setPixel(cx - y, cy - x);
            y++;
            if (d < 0) {
                d += 2 * y + 1;
            } else {
                x--;
                d += 2 * (y - x) + 1;
            }
        }
    }

    function drawFilledCircle(cx, cy, r) {
        for (let dy = -r; dy <= r; dy++) {
            for (let dx = -r; dx <= r; dx++) {
                if (dx * dx + dy * dy <= r * r) {
                    setPixel(cx + dx, cy + dy);
                }
            }
        }
    }

    function drawLine(x0, y0, x1, y1) {
        // Bresenham's line algorithm
        const dx = Math.abs(x1 - x0);
        const dy = Math.abs(y1 - y0);
        const sx = x0 < x1 ? 1 : -1;
        const sy = y0 < y1 ? 1 : -1;
        let err = dx - dy;
        while (true) {
            setPixel(x0, y0);
            if (x0 === x1 && y0 === y1) break;
            const e2 = 2 * err;
            if (e2 > -dy) { err -= dy; x0 += sx; }
            if (e2 < dx) { err += dx; y0 += sy; }
        }
    }

    function setAttr(col, row, value) {
        if (col >= 0 && col < 32 && row >= 0 && row < 24) {
            attrs[row * 32 + col] = value;
        }
    }

    function fillAttrRect(col, row, w, h, value) {
        for (let dy = 0; dy < h; dy++) {
            for (let dx = 0; dx < w; dx++) {
                setAttr(col + dx, row + dy, value);
            }
        }
    }

    // --- 5x7 mini font for small text ---
    // Each character is 5 pixels wide, 7 pixels tall, stored as 7 bytes (top to bottom)
    const MINI_FONT = {
        'A': [0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
        'B': [0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E],
        'C': [0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E],
        'D': [0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E],
        'E': [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F],
        'F': [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10],
        'G': [0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F],
        'H': [0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
        'I': [0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E],
        'J': [0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C],
        'K': [0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11],
        'L': [0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F],
        'M': [0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11],
        'N': [0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11],
        'O': [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
        'P': [0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10],
        'Q': [0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D],
        'R': [0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11],
        'S': [0x0E, 0x11, 0x10, 0x0E, 0x01, 0x11, 0x0E],
        'T': [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04],
        'U': [0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
        'V': [0x11, 0x11, 0x11, 0x11, 0x0A, 0x0A, 0x04],
        'W': [0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11],
        'X': [0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11],
        'Y': [0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04],
        'Z': [0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F],
        ' ': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
        '0': [0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E],
        '1': [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E],
        '2': [0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F],
        '3': [0x0E, 0x11, 0x01, 0x06, 0x01, 0x11, 0x0E],
        '4': [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02],
        '5': [0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E],
        '6': [0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E],
        '7': [0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08],
        '8': [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E],
        '9': [0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C],
        '(': [0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02],
        ')': [0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08],
        '-': [0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00],
        '.': [0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C],
        '!': [0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04],
        '/': [0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10],
        ':': [0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00],
    };

    // Draw a 5x7 mini character at pixel position (px, py)
    function drawMiniChar(px, py, ch) {
        const data = MINI_FONT[ch];
        if (!data) return;
        for (let row = 0; row < 7; row++) {
            const bits = data[row];
            for (let col = 0; col < 5; col++) {
                if (bits & (0x10 >> col)) {
                    setPixel(px + col, py + row);
                }
            }
        }
    }

    // Draw a string of mini characters starting at pixel (px, py), 6px spacing
    function drawMiniString(px, py, str) {
        for (let i = 0; i < str.length; i++) {
            drawMiniChar(px + i * 6, py, str[i]);
        }
    }

    // Center a mini string in a given pixel width region starting at px
    function drawMiniStringCentered(py, str) {
        const totalWidth = str.length * 6 - 1;
        const px = Math.floor((256 - totalWidth) / 2);
        drawMiniString(px, py, str);
    }

    // =========================================================================
    // LARGE "SCOPA" TITLE LETTERS
    // Each letter is approximately 24px wide x 24px tall (3 char cells)
    // Designed as chunky blocky pixel art
    // =========================================================================

    // Each big letter is defined as a function that draws into the linear buffer
    // at a given top-left corner (x, y)

    function drawBigS(x, y) {
        // Top bar
        fillRect(x + 4, y, 16, 4);
        // Top-left curve
        fillRect(x, y + 2, 6, 4);
        fillRect(x + 2, y + 1, 4, 2);
        // Left side upper
        fillRect(x, y + 4, 4, 4);
        // Middle bar
        fillRect(x + 4, y + 10, 16, 4);
        fillRect(x + 2, y + 9, 4, 2);
        fillRect(x + 18, y + 13, 4, 2);
        // Right side lower
        fillRect(x + 20, y + 12, 4, 6);
        // Bottom-right curve
        fillRect(x + 18, y + 18, 6, 3);
        // Bottom bar
        fillRect(x + 4, y + 20, 16, 4);
        // Corners / rounding
        fillRect(x + 20, y + 1, 4, 3);
        fillRect(x, y + 19, 4, 3);
    }

    function drawBigC(x, y) {
        // Top bar
        fillRect(x + 4, y, 16, 4);
        fillRect(x + 2, y + 1, 3, 2);
        // Top-right corner accent
        fillRect(x + 20, y + 1, 4, 3);
        // Left side
        fillRect(x, y + 3, 4, 18);
        // Bottom-left curve
        fillRect(x + 2, y + 20, 3, 2);
        // Bottom bar
        fillRect(x + 4, y + 20, 16, 4);
        // Bottom-right corner accent
        fillRect(x + 20, y + 20, 4, 3);
    }

    function drawBigO(x, y) {
        // Top bar
        fillRect(x + 4, y, 16, 4);
        fillRect(x + 2, y + 1, 3, 2);
        fillRect(x + 19, y + 1, 3, 2);
        // Left side
        fillRect(x, y + 3, 4, 18);
        // Right side
        fillRect(x + 20, y + 3, 4, 18);
        // Bottom bar
        fillRect(x + 4, y + 20, 16, 4);
        fillRect(x + 2, y + 20, 3, 2);
        fillRect(x + 19, y + 20, 3, 2);
    }

    function drawBigP(x, y) {
        // Left vertical bar (full height)
        fillRect(x, y, 4, 24);
        // Top bar
        fillRect(x + 4, y, 16, 4);
        fillRect(x + 19, y + 1, 3, 2);
        // Right side upper
        fillRect(x + 20, y + 3, 4, 6);
        // Middle bar
        fillRect(x + 4, y + 10, 16, 4);
        fillRect(x + 19, y + 10, 3, 2);
    }

    function drawBigA(x, y) {
        // Top bar
        fillRect(x + 4, y, 16, 4);
        fillRect(x + 2, y + 1, 3, 2);
        fillRect(x + 19, y + 1, 3, 2);
        // Left side
        fillRect(x, y + 3, 4, 21);
        // Right side
        fillRect(x + 20, y + 3, 4, 21);
        // Middle crossbar
        fillRect(x + 4, y + 10, 16, 4);
    }

    // --- Title positioning ---
    // 5 letters, each ~24px wide with ~4px gap = 5*24 + 4*4 = 136px
    // Center in 256px: start at (256-136)/2 = 60
    const titleY = 16; // Character row 2, pixel row 16
    const letterW = 24;
    const letterGap = 6;
    const totalTitleW = 5 * letterW + 4 * letterGap;
    const titleStartX = Math.floor((256 - totalTitleW) / 2);

    drawBigS(titleStartX, titleY);
    drawBigC(titleStartX + letterW + letterGap, titleY);
    drawBigO(titleStartX + 2 * (letterW + letterGap), titleY);
    drawBigP(titleStartX + 3 * (letterW + letterGap), titleY);
    drawBigA(titleStartX + 4 * (letterW + letterGap), titleY);

    // Set attributes for the title area: BRIGHT YELLOW on BLUE
    // Title spans char rows 2-4 (pixel rows 16-39)
    // Calculate column range from pixel positions
    const titleAttrColStart = Math.floor(titleStartX / 8);
    const titleAttrColEnd = Math.ceil((titleStartX + totalTitleW) / 8);
    const titleAttrValue = attr(YELLOW, BLUE, true, false);
    fillAttrRect(titleAttrColStart, 2, titleAttrColEnd - titleAttrColStart, 3, titleAttrValue);

    // =========================================================================
    // DECORATIVE BORDER LINE (character row 5, pixel row ~44)
    // Row 5 in character cells = pixel rows 40-47. We'll draw a thick dashed
    // double-line pattern with diamond accents.
    // =========================================================================
    const borderY = 44;

    // Double line with a repeating diamond pattern
    for (let x = 8; x < 248; x++) {
        // Top thin line
        setPixel(x, borderY - 2);
        // Bottom thin line
        setPixel(x, borderY + 2);
    }
    // Diamond accents every 16 pixels
    for (let cx = 16; cx < 248; cx += 16) {
        setPixel(cx, borderY - 3);
        setPixel(cx - 1, borderY - 2);
        setPixel(cx + 1, borderY - 2);
        setPixel(cx - 2, borderY - 1);
        setPixel(cx + 2, borderY - 1);
        setPixel(cx - 3, borderY);
        setPixel(cx - 2, borderY);
        setPixel(cx - 1, borderY);
        setPixel(cx, borderY);
        setPixel(cx + 1, borderY);
        setPixel(cx + 2, borderY);
        setPixel(cx + 3, borderY);
        setPixel(cx - 2, borderY + 1);
        setPixel(cx + 2, borderY + 1);
        setPixel(cx - 1, borderY + 2);
        setPixel(cx + 1, borderY + 2);
        setPixel(cx, borderY + 3);
    }

    // Border attributes: BRIGHT CYAN on BLACK (row 5)
    const borderAttrValue = attr(CYAN, BLACK, true, false);
    fillAttrRect(0, 5, 32, 1, borderAttrValue);

    // =========================================================================
    // DENARI COIN / SUN SYMBOL (rows 7-16, centered)
    // Large circle with sun rays and inner detail
    // =========================================================================
    const coinCX = 128;
    const coinCY = 108; // roughly rows 12-14 center
    const coinOuterR = 28;
    const coinInnerR = 22;
    const coinCoreR = 8;

    // Outer circle
    drawCircle(coinCX, coinCY, coinOuterR);
    drawCircle(coinCX, coinCY, coinOuterR - 1);

    // Inner circle
    drawCircle(coinCX, coinCY, coinInnerR);

    // Core filled circle
    drawFilledCircle(coinCX, coinCY, coinCoreR);

    // Clear a small center for the "D" letter
    for (let dy = -5; dy <= 5; dy++) {
        for (let dx = -4; dx <= 4; dx++) {
            if (dx * dx + dy * dy <= 25) {
                clearPixel(coinCX + dx, coinCY + dy);
            }
        }
    }

    // Draw a small "D" for Denari in the center
    // Using a simple hand-drawn D shape
    for (let dy = -4; dy <= 4; dy++) {
        setPixel(coinCX - 3, coinCY + dy);
    }
    setPixel(coinCX - 2, coinCY - 4);
    setPixel(coinCX - 1, coinCY - 4);
    setPixel(coinCX, coinCY - 3);
    setPixel(coinCX + 1, coinCY - 3);
    setPixel(coinCX + 2, coinCY - 2);
    setPixel(coinCX + 2, coinCY - 1);
    setPixel(coinCX + 2, coinCY);
    setPixel(coinCX + 2, coinCY + 1);
    setPixel(coinCX + 2, coinCY + 2);
    setPixel(coinCX + 1, coinCY + 3);
    setPixel(coinCX, coinCY + 3);
    setPixel(coinCX - 1, coinCY + 4);
    setPixel(coinCX - 2, coinCY + 4);

    // Sun rays radiating outward from between the inner and outer circles
    const numRays = 16;
    for (let i = 0; i < numRays; i++) {
        const angle = (i * 2 * Math.PI) / numRays;
        const innerX = Math.round(coinCX + Math.cos(angle) * (coinInnerR + 2));
        const innerY = Math.round(coinCY + Math.sin(angle) * (coinInnerR + 2));
        const outerX = Math.round(coinCX + Math.cos(angle) * (coinOuterR - 2));
        const outerY = Math.round(coinCY + Math.sin(angle) * (coinOuterR - 2));
        drawLine(innerX, innerY, outerX, outerY);
    }

    // Decorative dots between inner and outer ring (midpoint)
    const numDots = 32;
    const dotR = (coinInnerR + coinOuterR) / 2;
    for (let i = 0; i < numDots; i++) {
        const angle = (i * 2 * Math.PI) / numDots;
        const dx = Math.round(coinCX + Math.cos(angle) * dotR);
        const dy = Math.round(coinCY + Math.sin(angle) * dotR);
        setPixel(dx, dy);
    }

    // Small decorative elements: 4 compass points between inner ring and core
    const compassR = 15;
    for (let i = 0; i < 4; i++) {
        const angle = (i * Math.PI) / 2;
        const px = Math.round(coinCX + Math.cos(angle) * compassR);
        const py = Math.round(coinCY + Math.sin(angle) * compassR);
        // Small diamond at each compass point
        setPixel(px, py - 2);
        setPixel(px - 1, py - 1);
        setPixel(px + 1, py - 1);
        setPixel(px - 2, py);
        setPixel(px - 1, py);
        setPixel(px, py);
        setPixel(px + 1, py);
        setPixel(px + 2, py);
        setPixel(px - 1, py + 1);
        setPixel(px + 1, py + 1);
        setPixel(px, py + 2);
    }

    // Coin attributes: BRIGHT YELLOW on BLACK
    // Coin spans approximately char rows 10-17
    const coinAttrValue = attr(YELLOW, BLACK, true, false);
    const coinCharRowStart = Math.floor((coinCY - coinOuterR - 2) / 8);
    const coinCharRowEnd = Math.ceil((coinCY + coinOuterR + 2) / 8);
    const coinCharColStart = Math.floor((coinCX - coinOuterR - 2) / 8);
    const coinCharColEnd = Math.ceil((coinCX + coinOuterR + 2) / 8);
    fillAttrRect(coinCharColStart, coinCharRowStart, coinCharColEnd - coinCharColStart, coinCharRowEnd - coinCharRowStart, coinAttrValue);

    // =========================================================================
    // FOUR SUIT INDICATORS (character row 19, pixel row 152)
    // Cup, Coin, Baton, Sword - evenly spaced
    // =========================================================================
    const suitY = 152;
    const suitSpacing = 56;
    const suitStartX = 128 - Math.floor((3 * suitSpacing) / 2);

    // --- Cup (Coppe) ---
    function drawCup(cx, cy) {
        // Bowl
        fillRect(cx - 5, cy - 4, 11, 2);
        fillRect(cx - 6, cy - 2, 13, 5);
        fillRect(cx - 5, cy + 3, 11, 1);
        fillRect(cx - 4, cy + 4, 9, 1);
        fillRect(cx - 3, cy + 5, 7, 1);
        // Stem
        fillRect(cx - 1, cy + 6, 3, 3);
        // Base
        fillRect(cx - 4, cy + 9, 9, 2);
    }

    // --- Coin (Denari) - small version ---
    function drawSmallCoin(cx, cy) {
        drawCircle(cx, cy, 6);
        drawCircle(cx, cy + 1, 5);
        // Center dot
        setPixel(cx, cy);
        setPixel(cx - 1, cy);
        setPixel(cx + 1, cy);
        setPixel(cx, cy - 1);
        setPixel(cx, cy + 1);
    }

    // --- Baton (Bastoni) ---
    function drawBaton(cx, cy) {
        // Vertical stick
        fillRect(cx - 1, cy - 7, 3, 15);
        // Knots/bulges
        fillRect(cx - 2, cy - 7, 5, 2);
        fillRect(cx - 2, cy - 2, 5, 2);
        fillRect(cx - 2, cy + 3, 5, 2);
        fillRect(cx - 2, cy + 6, 5, 2);
        // Diagonal leaf/twig marks
        setPixel(cx + 3, cy - 4);
        setPixel(cx + 4, cy - 5);
        setPixel(cx - 3, cy + 1);
        setPixel(cx - 4, cy);
    }

    // --- Sword (Spade) ---
    function drawSword(cx, cy) {
        // Blade (vertical)
        fillRect(cx - 1, cy - 8, 3, 12);
        setPixel(cx, cy - 9);
        // Cross guard
        fillRect(cx - 5, cy + 3, 11, 2);
        // Handle
        fillRect(cx - 1, cy + 5, 3, 4);
        // Pommel
        fillRect(cx - 2, cy + 9, 5, 2);
    }

    drawCup(suitStartX, suitY);
    drawSmallCoin(suitStartX + suitSpacing, suitY);
    drawBaton(suitStartX + 2 * suitSpacing, suitY);
    drawSword(suitStartX + 3 * suitSpacing, suitY);

    // Suit attributes (row 19-20)
    // Each suit gets its own colour
    const cupCol = Math.floor(suitStartX / 8);
    const coinCol = Math.floor((suitStartX + suitSpacing) / 8);
    const batonCol = Math.floor((suitStartX + 2 * suitSpacing) / 8);
    const swordCol = Math.floor((suitStartX + 3 * suitSpacing) / 8);

    // Cup: bright blue; Coin: bright yellow; Baton: bright green; Sword: bright red
    const suitRow = Math.floor(suitY / 8);
    // Cup area (roughly 2 char cells wide)
    fillAttrRect(cupCol - 1, suitRow, 3, 2, attr(CYAN, BLACK, true, false));
    // Coin area
    fillAttrRect(coinCol - 1, suitRow, 3, 2, attr(YELLOW, BLACK, true, false));
    // Baton area
    fillAttrRect(batonCol - 1, suitRow, 3, 2, attr(GREEN, BLACK, true, false));
    // Sword area
    fillAttrRect(swordCol - 1, suitRow, 3, 2, attr(RED, BLACK, true, false));

    // =========================================================================
    // "ZX SPECTRUM" text (character row 21, pixel row 168)
    // =========================================================================
    drawMiniStringCentered(168, 'ZX SPECTRUM');

    // Attributes for ZX Spectrum text: BRIGHT WHITE on BLACK (row 21)
    const zxAttrValue = attr(WHITE, BLACK, true, false);
    fillAttrRect(0, 21, 32, 1, zxAttrValue);

    // =========================================================================
    // "(c) 2026" text (character row 22-23, pixel row 180)
    // =========================================================================
    drawMiniStringCentered(181, '(C) 2026');

    // Attributes for copyright: CYAN (not bright) on BLACK (rows 22-23)
    const copyAttrValue = attr(CYAN, BLACK, false, false);
    fillAttrRect(0, 22, 32, 2, copyAttrValue);

    // =========================================================================
    // Set remaining attributes to BLACK on BLACK (background)
    // Only set cells that haven't been set yet (value 0 means we haven't set them,
    // which also happens to be BLACK on BLACK with no bright, which is what we want)
    // But let's be explicit about the entire screen background.
    // =========================================================================

    // Row 0-1: black background (above title)
    fillAttrRect(0, 0, 32, 2, attr(BLACK, BLACK, false, false));

    // Row 6: between border and coin (bridge area)
    fillAttrRect(0, 6, 32, 1, attr(BLACK, BLACK, false, false));

    // Rows that aren't covered by other elements - fill with black
    // We need to make sure the outside-title columns on rows 2-4 are black ink on black paper
    // (so stray pixels don't show up in white)
    for (let row = 2; row <= 4; row++) {
        for (let col = 0; col < 32; col++) {
            if (col < titleAttrColStart || col >= titleAttrColEnd) {
                setAttr(col, row, attr(BLACK, BLACK, false, false));
            }
        }
    }

    // Row 20 (between ZX spectrum row and suit row)
    fillAttrRect(0, 20, 32, 1, attr(WHITE, BLACK, true, false));

    // Fill any remaining zero-valued attr cells with explicit black on black
    for (let i = 0; i < 768; i++) {
        if (attrs[i] === 0) {
            attrs[i] = attr(BLACK, BLACK, false, false);
        }
    }

    // =========================================================================
    // ADDITIONAL DECORATIVE ELEMENTS
    // =========================================================================

    // Small stars / dots in the background (rows 6-9 area, and rows 18-19)
    // These add atmosphere. They'll be in the cells set to yellow-on-black from the coin area
    // or in dedicated cells.

    // Stars above the coin
    const starPositions = [
        [40, 56], [72, 52], [96, 60], [160, 58], [184, 54], [216, 56],
        [52, 68], [204, 70], [32, 62], [224, 64],
    ];
    for (const [sx, sy] of starPositions) {
        setPixel(sx, sy);
        setPixel(sx - 1, sy);
        setPixel(sx + 1, sy);
        setPixel(sx, sy - 1);
        setPixel(sx, sy + 1);
    }
    // Set attributes for star area rows (7-8) to BRIGHT YELLOW on BLACK
    fillAttrRect(0, 7, 32, 2, attr(YELLOW, BLACK, true, false));

    // Decorative corner flourishes at top corners
    // Top-left
    for (let i = 0; i < 6; i++) {
        setPixel(i, 0);
        setPixel(0, i);
        setPixel(i, 1);
        setPixel(1, i);
    }
    // Top-right
    for (let i = 0; i < 6; i++) {
        setPixel(255 - i, 0);
        setPixel(255, i);
        setPixel(255 - i, 1);
        setPixel(254, i);
    }
    // Bottom-left
    for (let i = 0; i < 6; i++) {
        setPixel(i, 191);
        setPixel(0, 191 - i);
        setPixel(i, 190);
        setPixel(1, 191 - i);
    }
    // Bottom-right
    for (let i = 0; i < 6; i++) {
        setPixel(255 - i, 191);
        setPixel(255, 191 - i);
        setPixel(255 - i, 190);
        setPixel(254, 191 - i);
    }

    // Set corner cell attributes to bright cyan
    setAttr(0, 0, attr(CYAN, BLACK, true, false));
    setAttr(31, 0, attr(CYAN, BLACK, true, false));
    setAttr(0, 23, attr(CYAN, BLACK, true, false));
    setAttr(31, 23, attr(CYAN, BLACK, true, false));

    // Decorative line flanking the "ZX Spectrum" text
    const zxTextY = 168;
    const zxTextLeft = Math.floor((256 - 11 * 6 + 1) / 2);
    const zxTextRight = zxTextLeft + 11 * 6;
    // Left flourish
    drawHLine(zxTextLeft - 24, zxTextLeft - 4, zxTextY + 3);
    setPixel(zxTextLeft - 25, zxTextY + 2);
    setPixel(zxTextLeft - 25, zxTextY + 4);
    setPixel(zxTextLeft - 3, zxTextY + 2);
    setPixel(zxTextLeft - 3, zxTextY + 4);
    // Right flourish
    drawHLine(zxTextRight + 4, zxTextRight + 24, zxTextY + 3);
    setPixel(zxTextRight + 3, zxTextY + 2);
    setPixel(zxTextRight + 3, zxTextY + 4);
    setPixel(zxTextRight + 25, zxTextY + 2);
    setPixel(zxTextRight + 25, zxTextY + 4);

    // =========================================================================
    // PACK INTO SPECTRUM FORMAT
    // =========================================================================

    const pixelBuffer = new Uint8Array(6144);

    for (let y = 0; y < 192; y++) {
        for (let col = 0; col < 32; col++) {
            let byte = 0;
            for (let bit = 0; bit < 8; bit++) {
                if (linear[y * 256 + col * 8 + bit]) {
                    byte |= (1 << (7 - bit));
                }
            }
            pixelBuffer[pixelAddress(col * 8, y)] = byte;
        }
    }

    // Combine into final 6912-byte buffer
    const result = new Uint8Array(6912);
    result.set(pixelBuffer, 0);
    result.set(attrs, 6144);
    return result;
}

export const LOADING_SCREEN_DATA = generateLoadingScreen();
