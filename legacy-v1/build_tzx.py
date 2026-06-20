#!/usr/bin/env python3
"""Wrap scopa.tap into a TZX (ZXTape! v1.20) container with archive metadata.

Each TAP block becomes a TZX Standard-Speed Data Block (ID 0x10) carrying the
identical [flag][data][checksum] bytes, so the tape loads exactly as the .tap does
on real hardware. The Archive Info block (ID 0x32) adds the title / author / year /
description that the TAP format simply can't hold. Run after build_tap.py.
"""
def u16(b, i): return b[i] | (b[i + 1] << 8)

tap = open("scopa.tap", "rb").read()

# split the TAP into its raw blocks: each is [len:2][ len bytes = flag+data+checksum ]
blocks, i = [], 0
while i < len(tap):
    n = u16(tap, i); i += 2
    blocks.append(tap[i:i + n]); i += n

PAUSE_MS = 1000                                   # standard silence after each block

def std_block(data, pause=PAUSE_MS):              # TZX ID 0x10 = Standard Speed Data Block
    return bytes([0x10]) + pause.to_bytes(2, "little") + len(data).to_bytes(2, "little") + data

def archive_info(strings):                        # TZX ID 0x32 = Archive Info
    body = bytes([len(strings)])
    for tid, txt in strings:
        t = txt.encode("ascii")[:255]
        body += bytes([tid, len(t)]) + t
    return bytes([0x32]) + len(body).to_bytes(2, "little") + body

tzx = b"ZXTape!\x1a" + bytes([1, 20])             # signature + version 1.20
tzx += archive_info([
    (0x00, "Scopa"),                              # full title
    (0x02, "Tony Gillett"),                       # author
    (0x03, "2026"),                               # year
    (0x05, "Card game"),                          # type
    (0xFF, "Italian card game Scopa for the 48K ZX Spectrum. "
           "Based on an original ZX Spectrum game by Angelo Colucci."),
])
for b in blocks:
    tzx += std_block(b)

open("scopa.tzx", "wb").write(tzx)
print(f"scopa.tzx = {len(tzx)} bytes | ZXTape! v1.20 + archive-info + "
      f"{len(blocks)} standard-speed blocks (re-wrapped from {len(tap)}B scopa.tap)")
