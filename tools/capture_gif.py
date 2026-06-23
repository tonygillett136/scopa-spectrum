#!/usr/bin/env python3
"""Capture a sequence of emulator frames from ONE ZEsarUX session and assemble a looping GIF.
Usage: capture_gif.py <sna> <n_frames> <interval_s> <start_s> <out.gif>  [scale]
Each frame is the live ZX screen (0x4000-0x5AFF) read over ZRCP. RUN FROM scopa/."""
import sys, time, subprocess, os
sys.path.insert(0, "/Volumes/SSD1/code/retro_computing/zxspectrum/mastery/tools")
from PIL import Image

sna, n, dt, start, out = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
scale = int(sys.argv[6]) if len(sys.argv) > 6 else 2
subprocess.run(["pkill", "-9", "-f", "zesarux"], capture_output=True); time.sleep(1)
from zx_shot import Speccy
frames = []
with Speccy(port=10000) as zx:
    zx.smartload(os.path.abspath(sna))
    zx.sleep(start)
    for i in range(n):
        p = f"/tmp/gifcap_{i:03d}.png"
        zx.screenshot(p)
        frames.append(Image.open(p).convert("RGB"))
        time.sleep(dt)
subprocess.run(["pkill", "-9", "-f", "zesarux"], capture_output=True)
W, H = frames[0].size
frames = [f.resize((W*scale, H*scale), Image.NEAREST).quantize(colors=16, dither=Image.NONE) for f in frames]
frames[0].save(out, save_all=True, append_images=frames[1:], duration=120, loop=0, optimize=True, disposal=2)
print(f"wrote {out}: {len(frames)} frames, {os.path.getsize(out)} bytes")
