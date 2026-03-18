// ZX Spectrum colour palette — exact hardware RGB values
// PALETTE[bright][colourIndex] = [r, g, b]
export const PALETTE = [
    // BRIGHT 0 (normal)
    [
        [0, 0, 0],       // 0 Black
        [0, 0, 215],     // 1 Blue
        [215, 0, 0],     // 2 Red
        [215, 0, 215],   // 3 Magenta
        [0, 215, 0],     // 4 Green
        [0, 215, 215],   // 5 Cyan
        [215, 215, 0],   // 6 Yellow
        [215, 215, 215], // 7 White
    ],
    // BRIGHT 1
    [
        [0, 0, 0],       // 0 Black
        [0, 0, 255],     // 1 Blue
        [255, 0, 0],     // 2 Red
        [255, 0, 255],   // 3 Magenta
        [0, 255, 0],     // 4 Green
        [0, 255, 255],   // 5 Cyan
        [255, 255, 0],   // 6 Yellow
        [255, 255, 255], // 7 White
    ],
];

// Colour name constants
export const BLACK   = 0;
export const BLUE    = 1;
export const RED     = 2;
export const MAGENTA = 3;
export const GREEN   = 4;
export const CYAN    = 5;
export const YELLOW  = 6;
export const WHITE   = 7;

// Display dimensions
export const SCREEN_W = 256;
export const SCREEN_H = 192;
export const CHAR_COLS = 32;
export const CHAR_ROWS = 24;
export const CELL_SIZE = 8;

// Pixel buffer size (256x192 / 8 bits per byte)
export const PIXEL_BUFFER_SIZE = 6144;
// Attribute buffer size (32x24 cells)
export const ATTR_BUFFER_SIZE = 768;

// Timing
export const FRAME_RATE = 50; // PAL 50Hz
export const FRAME_MS = 1000 / FRAME_RATE;
export const FLASH_INTERVAL_MS = 320; // Flash toggles every 16 frames

// Border area (in native pixels around the 256x192 display)
export const BORDER_SIZE = 32;

// Total canvas size including border (native resolution)
export const CANVAS_W = SCREEN_W + BORDER_SIZE * 2; // 320
export const CANVAS_H = SCREEN_H + BORDER_SIZE * 2; // 256
