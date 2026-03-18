/**
 * Title screen music — Tarantella-inspired melody for ZX Spectrum beeper.
 * Notes are [frequency, duration] pairs, same format as SFX.
 */

// Note frequencies (Hz)
const C4 = 262, D4 = 294, E4 = 330, F4 = 349, G4 = 392;
const A4 = 440, B4 = 494, C5 = 523, D5 = 587, E5 = 659;
const F5 = 698, G5 = 784, A5 = 880;
const R = 0; // rest

// Durations at ~140 BPM
const S = 0.055;  // sixteenth
const E = 0.11;   // eighth
const Q = 0.22;   // quarter
const H = 0.44;   // half
const g = 0.015;  // tiny gap between phrases

export const TITLE_MELODY = [
    // Phrase 1: Energetic ascending tarantella motif
    [E4, E], [E4, S], [F4, S], [G4, E], [A4, E],
    [B4, Q], [A4, E], [G4, E],
    [A4, Q], [G4, S], [F4, S], [E4, E],
    [R, g],

    // Phrase 2: Descending response
    [C5, E], [B4, E], [A4, E], [G4, E],
    [A4, Q], [G4, E], [F4, E],
    [E4, Q], [D4, E], [E4, E],
    [R, g],

    // Phrase 3: Dancing repeat with higher energy
    [E4, S], [E4, S], [F4, S], [G4, S],
    [A4, S], [A4, S], [B4, S], [C5, S],
    [B4, E], [A4, E], [G4, E], [A4, E],
    [B4, Q], [R, E],
    [R, g],

    // Phrase 4: Grand resolution
    [C5, E], [B4, S], [A4, S], [G4, E], [A4, E],
    [E4, E], [F4, S], [E4, S], [D4, E],
    [E4, H],
    [R, Q],
];

// Pre-calculate total duration for looping
export const TITLE_MELODY_DURATION = TITLE_MELODY.reduce((sum, [, d]) => sum + d, 0);
