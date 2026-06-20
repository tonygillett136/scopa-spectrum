#!/usr/bin/env python3
"""Wrap scopa.tap into a TZX (ZXTape! v1.20) container with archive metadata.

Each TAP block becomes a TZX Turbo-Speed Data Block (ID 0x11) with the STANDARD ROM
bit timings but a LONGER pilot tone (leader). The standard data leader (3223 pulses)
proved marginal on a TZXDuino -- a continuously-playing tape can stream a block past
the Spectrum while it's briefly busy (the BASIC POKE loop, or the ZX0 pop-in decode),
so it misses the leader. A longer leader gives it room to catch up. The Archive Info
block (ID 0x32) carries the title / author / year. Run after build_tap.py.
"""
def u16(b, i): return b[i] | (b[i + 1] << 8)

tap = open("scopa.tap", "rb").read()

# split the TAP into its raw blocks: each is [len:2][ len bytes = flag+data+checksum ]
blocks, i = [], 0
while i < len(tap):
    n = u16(tap, i); i += 2
    blocks.append(tap[i:i + n]); i += n

PILOT_HEADER = 8063        # pilot pulses for a header block (flag < 128) -- the standard long leader
PILOT_DATA   = 5000        # pilot pulses for a data block -- well above the standard 3223 so a TZXDuino
                           # (or a Spectrum still in the BASIC POKE loop) reliably syncs on the leader
PAUSE_MS     = 1500        # silence after each block

def turbo_block(data, pause=PAUSE_MS):            # TZX ID 0x11 = Turbo Speed Data Block
    pilot = PILOT_HEADER if data[0] < 128 else PILOT_DATA
    return (bytes([0x11])
            + (2168).to_bytes(2, "little")        # pilot pulse length (T-states) -- standard
            + (667).to_bytes(2, "little")         # sync first pulse
            + (735).to_bytes(2, "little")         # sync second pulse
            + (855).to_bytes(2, "little")         # zero-bit pulse
            + (1710).to_bytes(2, "little")        # one-bit pulse
            + pilot.to_bytes(2, "little")         # PILOT TONE LENGTH (number of pulses) -- the leader
            + bytes([8])                          # used bits in the last byte
            + pause.to_bytes(2, "little")         # pause after the block (ms)
            + len(data).to_bytes(3, "little")
            + data)

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
    tzx += turbo_block(b)

open("scopa.tzx", "wb").write(tzx)
print(f"scopa.tzx = {len(tzx)} bytes | ZXTape! v1.20 + archive-info + {len(blocks)} turbo blocks "
      f"(pilot {PILOT_HEADER}/{PILOT_DATA} pulses, {PAUSE_MS}ms pause; from {len(tap)}B scopa.tap)")
