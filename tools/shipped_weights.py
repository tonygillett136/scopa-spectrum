"""THE single source of truth for the SHIPPED Z80 AI evaluation weights.

These mirror scopa.asm exactly (CardBonus / EvalCapture / EvalDrop / EvalSafety / NapolaBonus).
If a weight changes in the asm, change it HERE and re-run each consumer's selftest -- every host
mirror (ai_watch, ai_audit, ...) must import from this module, never carry its own copy.
(Historical note: before this module existed there were FIVE divergent copies across tools/;
ai_tune.py's W0 is intentionally NOT this -- it is the frozen PRE-TUNE baseline the optimiser
measured against.)

Verified against scopa.asm 2026-06-30 (comments cite the asm sites):
"""

SHIPPED = dict(
    card_count=3,          # EvalCapture: (captured+1) * 3     ("CARD_COUNT weight = *3")
    denari=5,              # CardBonus: coin card
    settebello_cap=35,     # CardBonus: id 6
    seven=12,              # CardBonus: value 7 ("self-play tuned, was 15")
    six=8,                 # CardBonus: value 6
    ace=6,                 # CardBonus: value 1
    sweep=50,              # EvalCapture: table cleared (not ace-sweep)
    napola=35,             # NapolaBonus: per napola point locked in (run delta x35)
    drop_settebello=-40,   # EvalDrop
    drop_seven=-5,         # EvalDrop ("was -12")
    drop_six=-5,           # EvalDrop ("was -6")
    drop_denari=-4,        # EvalDrop
    drop_face=3,           # EvalDrop: value >= 8
    leave_sweep_risk=-9,   # EvalSafety: leftover sum <= 10 ("was -20"), ThreatLive-gated
    leave_easy_capture=-5, # EvalSafety: per matchable value ("was -2"), ThreatLive-gated
    ace_guard_card=-1,     # EvalSafety (asso rule on): per leftover card, no ace on table
    ace_guard_settebello=-25,  # EvalSafety (asso rule on): settebello exposed to an ace sweep
)
