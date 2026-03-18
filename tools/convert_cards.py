#!/usr/bin/env python3
"""
Convert 40 Napoletane card JPG images to ZX Spectrum sprite format.

Each card is converted to 80x128 pixels (10x16 character cells).
For each 8x8 cell, tries all 128 ink/paper/bright combinations,
uses Bayer 8x8 ordered dithering, picks the combo with lowest error.

Output: ES module with base64-encoded sprite data.

Usage: python3 tools/convert_cards.py [input_dir] [output_file]
Defaults: reference_cards/ js/data/card-sprites.js
"""

import os
import sys
import base64
import math
from PIL import Image

INPUT_DIR = sys.argv[1] if len(sys.argv) > 1 else 'reference_cards'
OUTPUT_FILE = sys.argv[2] if len(sys.argv) > 2 else 'js/data/card-sprites.js'

# Card dimensions in Spectrum format
CARD_W = 80       # pixels wide
CARD_H = 128      # pixels tall
CARD_COLS = 10    # character cells wide
CARD_ROWS = 16    # character cells tall
BPR = 10          # bytes per pixel row (80 / 8)
CELL = 8          # pixels per cell

# ZX Spectrum colour palette (non-bright and bright)
# Format: (R, G, B) for each colour 0-7
PALETTE_NORMAL = [
    (0, 0, 0),       # 0 BLACK
    (0, 0, 205),     # 1 BLUE
    (205, 0, 0),     # 2 RED
    (205, 0, 205),   # 3 MAGENTA
    (0, 205, 0),     # 4 GREEN
    (0, 205, 205),   # 5 CYAN
    (205, 205, 0),   # 6 YELLOW
    (205, 205, 205), # 7 WHITE
]

PALETTE_BRIGHT = [
    (0, 0, 0),       # 0 BLACK
    (0, 0, 255),     # 1 BLUE
    (255, 0, 0),     # 2 RED
    (255, 0, 255),   # 3 MAGENTA
    (0, 255, 0),     # 4 GREEN
    (0, 255, 255),   # 5 CYAN
    (255, 255, 0),   # 6 YELLOW
    (255, 255, 255), # 7 WHITE
]

# Bayer 8x8 ordered dithering matrix (normalized to 0..1)
BAYER_8x8 = [
    [ 0/64,  32/64,  8/64, 40/64,  2/64, 34/64, 10/64, 42/64],
    [48/64,  16/64, 56/64, 24/64, 50/64, 18/64, 58/64, 26/64],
    [12/64,  44/64,  4/64, 36/64, 14/64, 46/64,  6/64, 38/64],
    [60/64,  28/64, 52/64, 20/64, 62/64, 30/64, 54/64, 22/64],
    [ 3/64,  35/64, 11/64, 43/64,  1/64, 33/64,  9/64, 41/64],
    [51/64,  19/64, 59/64, 27/64, 49/64, 17/64, 57/64, 25/64],
    [15/64,  47/64,  7/64, 39/64, 13/64, 45/64,  5/64, 37/64],
    [63/64,  31/64, 55/64, 23/64, 61/64, 29/64, 53/64, 21/64],
]


def colour_distance_sq(r1, g1, b1, r2, g2, b2):
    """Weighted Euclidean colour distance (perceptual weighting)."""
    dr = r1 - r2
    dg = g1 - g2
    db = b1 - b2
    return 2 * dr * dr + 4 * dg * dg + 3 * db * db


def convert_cell(pixels_rgb, cell_x, cell_y):
    """
    Convert one 8x8 cell of the image to Spectrum format.

    pixels_rgb: list of (r,g,b) tuples, indexed as [y * CARD_W + x]
    cell_x, cell_y: cell position in character cells

    Returns: (pixel_bytes[8], attr_byte)
    """
    # Extract 64 source pixels for this cell
    src = []
    px0 = cell_x * CELL
    py0 = cell_y * CELL
    for dy in range(CELL):
        row = []
        for dx in range(CELL):
            idx = (py0 + dy) * CARD_W + (px0 + dx)
            row.append(pixels_rgb[idx])
        src.append(row)

    best_error = float('inf')
    best_bytes = None
    best_attr = 0

    # Try all ink/paper combinations for both bright=0 and bright=1
    for bright in range(2):
        palette = PALETTE_BRIGHT if bright else PALETTE_NORMAL
        for ink in range(8):
            for paper in range(8):
                if ink == paper:
                    continue  # Skip identical ink/paper (waste)

                ink_rgb = palette[ink]
                paper_rgb = palette[paper]

                # Penalize low-contrast pairs where both colours are light.
                # Yellow/white, cyan/white, green/yellow etc. look washed out
                # on the Spectrum. Compute perceived luminance for both.
                ink_lum = 0.299 * ink_rgb[0] + 0.587 * ink_rgb[1] + 0.114 * ink_rgb[2]
                paper_lum = 0.299 * paper_rgb[0] + 0.587 * paper_rgb[1] + 0.114 * paper_rgb[2]
                lum_contrast = abs(ink_lum - paper_lum)
                # If both are very light (high lum) and contrast is low, skip
                min_lum = min(ink_lum, paper_lum)
                if min_lum > 150 and lum_contrast < 60:
                    continue

                total_error = 0
                cell_bytes = []

                for dy in range(CELL):
                    byte_val = 0
                    for dx in range(CELL):
                        sr, sg, sb = src[dy][dx]
                        threshold = BAYER_8x8[dy][dx]

                        # Distance to ink and paper colours
                        d_ink = colour_distance_sq(sr, sg, sb, *ink_rgb)
                        d_paper = colour_distance_sq(sr, sg, sb, *paper_rgb)

                        # Interpolation factor: 0 = paper, 1 = ink
                        total_d = d_ink + d_paper
                        if total_d == 0:
                            shade = 0.5
                        else:
                            shade = d_paper / total_d  # Higher = closer to ink

                        # Apply Bayer dithering
                        if shade > threshold:
                            byte_val |= (0x80 >> dx)
                            # Error: distance between source and ink colour
                            total_error += d_ink
                        else:
                            # Error: distance between source and paper colour
                            total_error += d_paper

                    cell_bytes.append(byte_val)

                if total_error < best_error:
                    best_error = total_error
                    best_bytes = cell_bytes
                    attr = (bright << 6) | (paper << 3) | ink
                    best_attr = attr

    return best_bytes, best_attr


def convert_card(image_path):
    """
    Convert a single card image to Spectrum sprite format.

    Returns: (pixel_data: bytes, attr_data: bytes)
        pixel_data: BPR * CARD_H bytes (10 bytes/row * 128 rows = 1280 bytes)
        attr_data: CARD_COLS * CARD_ROWS bytes (10 * 16 = 160 bytes)
    """
    img = Image.open(image_path).convert('RGB')
    img = img.resize((CARD_W, CARD_H), Image.LANCZOS)

    # Get all pixels as flat list
    pixels_rgb = list(img.getdata())

    # Process each cell
    pixel_data = bytearray(BPR * CARD_H)
    attr_data = bytearray(CARD_COLS * CARD_ROWS)

    for cy in range(CARD_ROWS):
        for cx in range(CARD_COLS):
            cell_bytes, attr_byte = convert_cell(pixels_rgb, cx, cy)

            # Store pixel bytes (8 rows per cell)
            for dy in range(CELL):
                row_offset = (cy * CELL + dy) * BPR + cx
                pixel_data[row_offset] = cell_bytes[dy]

            # Store attribute
            attr_data[cy * CARD_COLS + cx] = attr_byte

    return bytes(pixel_data), bytes(attr_data)


# File mapping: file number -> (suit_index, value)
# Files 01-10 = Denari (suit 1), 11-20 = Coppe (suit 0),
# 21-30 = Spade (suit 3), 31-40 = Bastoni (suit 2)
# Internal order: Coppe=0, Denari=1, Bastoni=2, Spade=3
# Values: 1-10 (Asso=1 ... Re=10)
# Wikimedia naming: 1=Asso,2=Due,3=Tre,4=Quattro,5=Cinque,6=Sei,7=Sette,
#   8=Otto(Fante),9=Nove(Cavallo),10=Dieci(Re)

FILE_SUIT_MAP = {
    range(1, 11):  1,   # Denari
    range(11, 21): 0,   # Coppe
    range(21, 31): 3,   # Spade
    range(31, 41): 2,   # Bastoni
}

FILENAMES = [
    "01_Asso_di_denari.jpg",
    "02_Due_di_denari.jpg",
    "03_Tre_di_denari.jpg",
    "04_Quattro_di_denari.jpg",
    "05_Cinque_di_denari.jpg",
    "06_Sei_di_denari.jpg",
    "07_Sette_di_denari.jpg",
    "08_Otto_di_denari.jpg",
    "09_Nove_di_denari.jpg",
    "10_Dieci_di_denari.jpg",
    "11_Asso_di_coppe.jpg",
    "12_Due_di_coppe.jpg",
    "13_Tre_di_coppe.jpg",
    "14_Quattro_di_coppe.jpg",
    "15_Cinque_di_coppe.jpg",
    "16_Sei_di_coppe.jpg",
    "17_Sette_di_coppe.jpg",
    "18_Otto_di_coppe.jpg",
    "19_Nove_di_coppe.jpg",
    "20_Dieci_di_coppe.jpg",
    "21_Asso_di_spade.jpg",
    "22_Due_di_spade.jpg",
    "23_Tre_di_spade.jpg",
    "24_Quattro_di_spade.jpg",
    "25_Cinque_di_spade.jpg",
    "26_Sei_di_spade.jpg",
    "27_Sette_di_spade.jpg",
    "28_Otto_di_spade.jpg",
    "29_Nove_di_spade.jpg",
    "30_Dieci_di_spade.jpg",
    "31_Asso_di_bastoni.jpg",
    "32_Due_di_bastoni.jpg",
    "33_Tre_di_bastoni.jpg",
    "34_Quattro_di_bastoni.jpg",
    "35_Cinque_di_bastoni.jpg",
    "36_Sei_di_bastoni.jpg",
    "37_Sette_di_bastoni.jpg",
    "38_Otto_di_bastoni.jpg",
    "39_Nove_di_bastoni.jpg",
    "40_Dieci_di_Bastoni.jpg",
]


def get_suit_value(file_index):
    """Map 0-based file index to (suit, value)."""
    num = file_index + 1  # 1-based
    value = ((num - 1) % 10) + 1  # 1-10 within suit

    if num <= 10:
        suit = 1   # Denari
    elif num <= 20:
        suit = 0   # Coppe
    elif num <= 30:
        suit = 3   # Spade
    else:
        suit = 2   # Bastoni

    # Map Wikimedia values to game values:
    # Wiki: 1=Asso, 2=Due, ..., 7=Sette, 8=Otto, 9=Nove, 10=Dieci
    # Game: 1=Asso, 2=Due, ..., 7=Sette, 8=Fante, 9=Cavallo, 10=Re
    # The values 1-7 map directly.
    # 8(Otto) -> 8(Fante), 9(Nove) -> 9(Cavallo), 10(Dieci) -> 10(Re)
    # The images at positions 8,9,10 in each suit ARE the face cards,
    # they're just named by their numerical order.

    return suit, value


def main():
    print(f"Converting {len(FILENAMES)} cards from {INPUT_DIR}/ to {OUTPUT_FILE}")
    print(f"Card size: {CARD_W}x{CARD_H}px ({CARD_COLS}x{CARD_ROWS} cells)")
    print()

    # Convert all cards, organized by suit and value
    # sprites[suit][value] = (pixel_b64, attr_b64)
    sprites = {}

    for i, filename in enumerate(FILENAMES):
        path = os.path.join(INPUT_DIR, filename)
        if not os.path.exists(path):
            print(f"  MISSING: {filename}")
            continue

        suit, value = get_suit_value(i)
        print(f"  [{i+1:2d}/40] {filename} -> suit={suit} value={value} ...", end=' ', flush=True)

        pixel_data, attr_data = convert_card(path)
        pixel_b64 = base64.b64encode(pixel_data).decode('ascii')
        attr_b64 = base64.b64encode(attr_data).decode('ascii')

        key = f"{suit}_{value}"
        sprites[key] = (pixel_b64, attr_b64)

        print(f"OK (pixels={len(pixel_data)}B, attrs={len(attr_data)}B)")

    # Generate JS module
    print(f"\nWriting {OUTPUT_FILE} ...")

    lines = []
    lines.append("/**")
    lines.append(" * card-sprites.js — Pre-converted ZX Spectrum card sprites")
    lines.append(f" * Generated by tools/convert_cards.py")
    lines.append(f" * {len(sprites)} cards, {CARD_W}x{CARD_H}px ({CARD_COLS}x{CARD_ROWS} cells) each")
    lines.append(" *")
    lines.append(" * Each entry: { p: base64_pixels, a: base64_attrs }")
    lines.append(f" * Pixels: {BPR * CARD_H} bytes (BPR={BPR} * H={CARD_H})")
    lines.append(f" * Attrs: {CARD_COLS * CARD_ROWS} bytes ({CARD_COLS} * {CARD_ROWS})")
    lines.append(" */")
    lines.append("")
    lines.append("// Sprite data indexed by 'suit_value' key")
    lines.append("// Suits: 0=Coppe, 1=Denari, 2=Bastoni, 3=Spade")
    lines.append("// Values: 1-10 (1=Asso ... 7=Sette, 8=Fante, 9=Cavallo, 10=Re)")
    lines.append("export const CARD_SPRITE_DATA = {")

    for suit in range(4):
        for value in range(1, 11):
            key = f"{suit}_{value}"
            if key not in sprites:
                continue
            pixel_b64, attr_b64 = sprites[key]
            lines.append(f'  "{key}": {{')
            lines.append(f'    p: "{pixel_b64}",')
            lines.append(f'    a: "{attr_b64}"')
            lines.append(f'  }},')

    lines.append("};")
    lines.append("")

    os.makedirs(os.path.dirname(OUTPUT_FILE) or '.', exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        f.write('\n'.join(lines))

    file_size = os.path.getsize(OUTPUT_FILE)
    print(f"Done! {OUTPUT_FILE}: {file_size:,} bytes ({file_size/1024:.1f} KB)")


if __name__ == '__main__':
    main()
