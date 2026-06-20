#!/usr/bin/env python3
"""Reusable ZEsarUX test helper. Always pkills stale instances first, loads a fresh one.
Usage: python3 zxtest.py <file.sna|.tap> [sleep_s] [shot.png] [readhex:ADDR:LEN ...]
Prints PC and any requested memory reads; saves a screenshot if given.
"""
import sys, os, subprocess, time
sys.path.insert(0, "/Volumes/SSD1/code/retro_computing/zxspectrum/mastery/tools")

def main():
    path = os.path.abspath(sys.argv[1])
    sleep = float(sys.argv[2]) if len(sys.argv) > 2 and _isnum(sys.argv[2]) else 1.5
    shot = next((a for a in sys.argv[3:] if a.endswith(".png")), None)
    reads = [a for a in sys.argv[3:] if a.startswith("readhex:")]
    subprocess.run(["pkill", "-9", "-f", "zesarux"], capture_output=True); time.sleep(1.0)
    from zx_shot import Speccy
    try:
        with Speccy(port=10000) as zx:
            zx.smartload(path)
            zx.sleep(sleep)
            print("PC:", hex(zx.registers().get("PC", 0)))
            for r in reads:
                _, addr, length = r.split(":")
                data = bytes(zx.read_mem(int(addr, 0), int(length)))
                print(f"  {addr}[{length}] = {data.hex()}")
            if shot:
                zx.screenshot(shot); print("shot:", shot)
    finally:
        subprocess.run(["pkill", "-9", "-f", "zesarux"], capture_output=True)

def _isnum(s):
    try:
        float(s); return True
    except ValueError:
        return False

if __name__ == "__main__":
    main()
