/**
 * Sound effect definitions for the Scopa game.
 * Each effect is an array of [frequency, duration] pairs.
 * Frequency 0 = silence (rest note).
 * All sounds are designed to feel authentic to the ZX Spectrum beeper.
 */

// Menu / UI sounds
export const SFX_MENU_MOVE = [
    [440, 0.03],
];

export const SFX_MENU_SELECT = [
    [880, 0.05],
    [1100, 0.05],
];

export const SFX_ERROR = [
    [150, 0.1],
    [100, 0.15],
];

// Card play (dropping on table) — descending thud
export const SFX_CARD_PLAY = [
    [400, 0.02], [300, 0.02], [200, 0.03], [150, 0.04],
];

// Card capture — ascending triumphant arpeggio
export const SFX_CARD_CAPTURE = [
    [440, 0.03], [550, 0.03], [660, 0.03], [880, 0.05],
    [0, 0.02], [1100, 0.08],
];

// Deal start — rapid shuffle sound
export const SFX_DEAL = [
    [800, 0.015], [600, 0.015], [800, 0.015], [600, 0.015],
    [400, 0.03],
];

// Per-card deal arrival — short click
export const SFX_DEAL_CARD = [
    [300, 0.02], [200, 0.015],
];

// Scopa (sweep) fanfare — dramatic ascending
export const SFX_SCOPA = [
    [523, 0.06], [0, 0.02], [659, 0.06], [0, 0.02],
    [784, 0.06], [0, 0.02], [1047, 0.12],
    [0, 0.04], [784, 0.06], [1047, 0.06],
    [1319, 0.06], [0, 0.02], [1568, 0.25],
];

// End of round — descending finality
export const SFX_ROUND_END = [
    [880, 0.08], [784, 0.08], [660, 0.08],
    [523, 0.08], [440, 0.15],
];

// Score point awarded
export const SFX_SCORE_POINT = [
    [800, 0.05],
    [1000, 0.08],
];

// Game over — bright celebratory fanfare
export const SFX_WIN = [
    [523, 0.1], [0, 0.03], [659, 0.1], [0, 0.03],
    [784, 0.1], [0, 0.03], [1047, 0.2],
    [0, 0.08], [784, 0.06], [1047, 0.06], [1319, 0.06],
    [0, 0.03], [1047, 0.06], [1319, 0.06], [1568, 0.4],
];

// Game over — slow melancholic descent
export const SFX_LOSE = [
    [440, 0.15], [0, 0.05], [370, 0.15], [0, 0.05],
    [330, 0.2], [0, 0.05], [294, 0.2], [0, 0.05],
    [262, 0.4],
];

// AI thinking "blip"
export const SFX_THINK = [
    [200, 0.02],
];

// Key press acknowledgement (very short)
export const SFX_KEY = [
    [600, 0.015],
];
