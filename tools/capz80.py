#!/usr/bin/env python3
"""Capture the two play-in-browser .z80 snapshots for the JSSpeccy embed.

JSSpeccy needs a snapshot that (a) has IFF1=1 (else its keyboard handler sees a DI'd CPU
and keys do nothing) and (b) resumes at a clean PC in the game code, NOT mid-ROM-ISR. The
title wait runs with interrupts OFF (beeper music DI'd, never re-enabled), so we drive to the
HOW TO PLAY screen (press H at the title) -- a HALT keywait with interrupts ON -- and snapshot
there, retrying until the SAVED file verifies IFF1=1 and 0x8000<=PC<0xC000 (the keywait HALTs,
so snapshot-save often samples the ISR at 0x38; we just retry). FORCETITLE 1/2 fixes which of
the two title screens appears after SPACE, giving the play-a/play-b rotation. Run from scopa/.
"""
import sys, os, time, subprocess, shutil
sys.path.insert(0, "/Volumes/SSD1/code/retro_computing/zxspectrum/mastery/tools")
ROOT = "/Volumes/SSD1/code/retro_computing/zxspectrum/scopa"
SJASM = "/Volumes/SSD1/code/retro_computing/zxspectrum/mastery/tools/sjasmplus"

# set-ui-io-ports matrix is ACTIVE-LOW: 0=pressed, neutral row = 0x1F. ([0]*9 = ALL keys down!)
# 8 half-rows (0xFE,0xFD,0xFB,0xF7,0xEF,0xDF,0xBF,0x7F) + joystick. H = idx6 bit4 -> 0x1F&~0x10 = 0x0F.
NEUTRAL = [0x1F] * 8 + [0x00]
KEY_H   = [0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x0F, 0x1F, 0x00]

def realpc(d):
    pc = d[6] | d[7] << 8
    return (d[32] | d[33] << 8) if pc == 0 else pc

def capture(forcetitle, out_name):
    print(f"=== building FORCETITLE={forcetitle} ===")
    r = subprocess.run([SJASM, "scopa.asm", f"-DFORCETITLE={forcetitle}"], cwd=ROOT,
                       capture_output=True, text=True)
    log = r.stdout + r.stderr
    if "Errors: 0" not in log:
        print(log[-400:]); raise SystemExit("build failed")
    subprocess.run(["pkill", "-9", "-f", "zesarux"], capture_output=True); time.sleep(1)
    from zx_shot import Speccy
    tmp = f"/tmp/cap_{out_name}"
    ok = False
    with Speccy(port=10000) as zx:
        zx.smartload(f"{ROOT}/scopa.sna")
        zx.sleep(9)                          # title shows, music finishes (interrupts still off here)
        zx.hold_rows(KEY_H); time.sleep(0.4) # press H -> enters HOW TO PLAY
        zx.hold_rows(NEUTRAL); time.sleep(1.0)
        for attempt in range(40):
            if os.path.exists(tmp): os.remove(tmp)
            zx.cmd(f"snapshot-save {tmp}"); time.sleep(0.25)
            if not os.path.exists(tmp):
                continue
            d = open(tmp, "rb").read()
            pc, iff1 = realpc(d), d[27]
            if iff1 and 0x8000 <= pc < 0xC000:
                print(f"  clean snapshot on attempt {attempt}: PC={pc:#06x} IFF1={iff1} ({len(d)} B)")
                ok = True; break
            time.sleep(0.15)                 # land between HALTs / catch interrupts enabled
    subprocess.run(["pkill", "-9", "-f", "zesarux"], capture_output=True)
    if not ok:
        raise SystemExit(f"could not capture a clean snapshot for {out_name}")
    shutil.copy(tmp, f"{ROOT}/site/{out_name}")
    print(f"  -> site/{out_name}")

if __name__ == "__main__":
    capture(1, "play-a.z80")
    capture(2, "play-b.z80")
    print("done: both snapshots captured (IFF1=1, clean PC).")
