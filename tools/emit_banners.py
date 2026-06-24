#!/usr/bin/env python3
"""Generate the celebration / header banner .bin files in Rockwell.
Format (matches BlitBanner): 1024 bitmap bytes (256x32, 32 rows x 32 bytes, MSB=leftmost) +
128 attr bytes (4 char-rows x 32 cols). The base attr is bright-gold (0x46); the runtime
SweepBanner routine overrides the attrs to animate the light-sweep, so the stored colour is
just the resting gold. RUN FROM scopa/."""
import os, subprocess
from PIL import Image, ImageDraw, ImageFont

ZX0 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zx0")

ROCK = "/System/Library/Fonts/Supplemental/Rockwell.ttc"
W, H = 256, 32
GOLD = 0x46                                   # bright yellow ink on black paper

def render_mask(word):
    md = ImageDraw.Draw(Image.new("L", (4, 4)))
    sz = 40
    while sz > 8:
        f = ImageFont.truetype(ROCK, sz, index=0)
        bb = md.textbbox((0, 0), word, font=f)
        if bb[2]-bb[0] <= W-6 and bb[3]-bb[1] <= H-2:
            break
        sz -= 1
    f = ImageFont.truetype(ROCK, sz, index=0)
    bb = md.textbbox((0, 0), word, font=f)
    img = Image.new("L", (W, H), 0); d = ImageDraw.Draw(img)
    d.text(((W-(bb[2]-bb[0]))//2 - bb[0], (H-(bb[3]-bb[1]))//2 - bb[1]), word, font=f, fill=255)
    return img.point(lambda v: 1 if v >= 110 else 0)

def emit(word, path):
    m = render_mask(word).load()
    out = bytearray()
    for row in range(32):
        for bx in range(32):
            byte = 0
            for bit in range(8):
                if m[bx*8+bit, row]:
                    byte |= (0x80 >> bit)
            out.append(byte)
    out += bytes([GOLD]) * 128
    open(path, "wb").write(out)
    zpath = path.rsplit(".", 1)[0] + ".zx0"      # ZX0-compress for decode-on-show (saves code space)
    subprocess.run([ZX0, "-f", path, zpath], check=True, capture_output=True)
    print(f"  {path}: {len(out)} B  -> {zpath}: {os.path.getsize(zpath)} B  ('{word}', Rockwell, gold)")

emit("SCOPA!",     "scopa_banner.bin")
emit("NEAPOLITAN", "neapolitan_banner.bin")
emit("PALLE DEL CANE", "palle_banner.bin")
emit("SCOPA",      "scopa_flag.bin")           # scores header, now gold Rockwell (was tricolore)
print("done -- INCBIN'd by scopa.asm; rebuild the tape after.")
