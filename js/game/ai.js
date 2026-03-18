import { findCaptures } from './rules.js';
import { SUIT_DENARI } from '../data/cards.js';

/**
 * AI opponent for Scopa.
 *
 * Uses a weighted evaluation algorithm to assess every legal play.
 * Supports three difficulty levels:
 *   EASY   - 30% chance of suboptimal play, no sweep avoidance
 *   MEDIUM - Current balanced AI (default)
 *   HARD   - Enhanced card counting, never makes mistakes
 */

export const DIFFICULTY = {
    EASY: 'easy',
    MEDIUM: 'medium',
    HARD: 'hard',
};

// Evaluation weights
const W = {
    SWEEP:              50,  // Clearing the table
    SETTEBELLO_CAPTURE: 35,  // Capturing the 7 of Denari
    PRIMIERA_7:         15,  // Capturing any 7
    PRIMIERA_6:          8,  // Capturing a 6
    PRIMIERA_ACE:        6,  // Capturing an Ace
    DENARI_CARD:         5,  // Each Denari-suit card
    CARD_COUNT:          2,  // Each card captured
    SETTEBELLO_DROP:   -40,  // Dropping the Settebello (!!)
    DROP_7:            -12,  // Dropping any 7
    DROP_6:             -6,  // Dropping a 6
    DROP_DENARI:        -4,  // Dropping a Denari card
    LEAVE_SWEEP_RISK: -20,  // Leaving table sum <= 10
    LEAVE_EASY_CAPTURE: -2,  // Each value that can capture from table
};

// Primiera values for reference
const PRIMIERA = { 7: 21, 6: 18, 1: 16, 5: 15, 4: 14, 3: 13, 2: 12, 8: 10, 9: 10, 10: 10 };

// Difficulty configurations
const DIFF_CONFIG = {
    easy: {
        mistakeChance: 0.30,
        useSweepAvoidance: false,
        useCardCounting: false,
    },
    medium: {
        mistakeChance: 0,
        useSweepAvoidance: true,
        useCardCounting: false,
    },
    hard: {
        mistakeChance: 0,
        useSweepAvoidance: true,
        useCardCounting: true,
    },
};

/**
 * Card tracker -- tracks all cards that have been seen during the hand.
 */
export class CardTracker {
    constructor() {
        this.seen = new Set();
    }

    markSeen(card) {
        this.seen.add(card.id);
    }

    markMultipleSeen(cards) {
        for (const card of cards) {
            this.seen.add(card.id);
        }
    }

    isSeen(card) {
        return this.seen.has(card.id);
    }

    unseenCount() {
        return 40 - this.seen.size;
    }

    reset() {
        this.seen.clear();
    }
}

/**
 * Select the best play for the AI.
 *
 * @param hand - AI's current hand
 * @param tableCards - Current table cards
 * @param tracker - CardTracker instance
 * @param difficulty - 'easy', 'medium', or 'hard'
 * @returns { card, captureSet } where captureSet is null for drops
 */
export function aiSelectPlay(hand, tableCards, tracker, difficulty = DIFFICULTY.MEDIUM) {
    const config = DIFF_CONFIG[difficulty] || DIFF_CONFIG.medium;
    const plays = [];

    for (const card of hand) {
        const captures = findCaptures(card, tableCards);

        if (captures.length === 0) {
            const score = evaluateDrop(card, tableCards, config);
            plays.push({ card, captureSet: null, score });
        } else {
            for (const captureSet of captures) {
                let score = evaluateCapture(card, captureSet, tableCards, config);

                // Hard mode: card counting bonus
                if (config.useCardCounting) {
                    score += evaluateCardCounting(card, captureSet, tracker);
                }

                plays.push({ card, captureSet, score });
            }
        }
    }

    // Sort by score descending
    plays.sort((a, b) => b.score - a.score);

    if (plays.length === 0) return null;

    // Easy mode: chance of picking a suboptimal play
    if (config.mistakeChance > 0 && Math.random() < config.mistakeChance && plays.length > 1) {
        const idx = 1 + Math.floor(Math.random() * Math.min(plays.length - 1, 3));
        return { card: plays[idx].card, captureSet: plays[idx].captureSet };
    }

    return { card: plays[0].card, captureSet: plays[0].captureSet };
}

/**
 * Evaluate the desirability of a capture.
 */
function evaluateCapture(playedCard, capturedSet, tableCards, config) {
    let score = 0;
    const allCaptured = [playedCard, ...capturedSet];

    // Total cards captured
    score += allCaptured.length * W.CARD_COUNT;

    // Denari cards
    for (const c of allCaptured) {
        if (c.suit === SUIT_DENARI) {
            score += W.DENARI_CARD;
        }
    }

    // Settebello
    if (allCaptured.some(c => c.suit === SUIT_DENARI && c.value === 7)) {
        score += W.SETTEBELLO_CAPTURE;
    }

    // Primiera-valuable cards
    for (const c of allCaptured) {
        if (c.value === 7) score += W.PRIMIERA_7;
        else if (c.value === 6) score += W.PRIMIERA_6;
        else if (c.value === 1) score += W.PRIMIERA_ACE;
    }

    // Sweep check
    const remaining = tableCards.filter(tc =>
        !capturedSet.some(cc => cc.id === tc.id)
    );
    if (remaining.length === 0) {
        score += W.SWEEP;
    } else if (config.useSweepAvoidance) {
        score += evaluateTableSafety(remaining);
    }

    return score;
}

/**
 * Evaluate the cost of dropping a card (no capture available).
 */
function evaluateDrop(card, tableCards, config) {
    let score = 0;

    // Penalise dropping valuable cards
    if (card.suit === SUIT_DENARI && card.value === 7) {
        score += W.SETTEBELLO_DROP;
    } else if (card.value === 7) {
        score += W.DROP_7;
    } else if (card.value === 6) {
        score += W.DROP_6;
    }

    if (card.suit === SUIT_DENARI) {
        score += W.DROP_DENARI;
    }

    // Prefer dropping face cards (low primiera value)
    if (card.value >= 8) {
        score += 3;
    }

    // Evaluate what the table looks like after dropping this card
    if (config.useSweepAvoidance) {
        const newTable = [...tableCards, card];
        score += evaluateTableSafety(newTable);
    }

    return score;
}

/**
 * Hard mode: card counting bonus.
 * Uses knowledge of seen cards to make better decisions.
 */
function evaluateCardCounting(card, captureSet, tracker) {
    let bonus = 0;
    const allCaptured = [card, ...captureSet];

    // Count unseen 7s -- if most are captured/seen, remaining ones are more valuable
    let sevensSeen = 0;
    for (let suit = 0; suit < 4; suit++) {
        if (tracker.isSeen({ id: suit * 10 + 6 })) { // value 7 = index 6
            sevensSeen++;
        }
    }

    // If capturing a 7 and we've already seen 2+ others, extra bonus
    const capturing7 = allCaptured.some(c => c.value === 7);
    if (capturing7 && sevensSeen >= 2) {
        bonus += 10;
    }

    // Late-game Denari awareness
    let denariSeen = 0;
    for (let v = 0; v < 10; v++) {
        if (tracker.isSeen({ id: 10 + v })) { // suit 1 (Denari) * 10 + value offset
            denariSeen++;
        }
    }
    const capturingDenari = allCaptured.filter(c => c.suit === SUIT_DENARI).length;
    if (capturingDenari > 0 && denariSeen >= 6) {
        bonus += 5; // Late-game Denari more valuable
    }

    // Avoid giving opponent opportunities for valuable cards
    // If few cards remain unseen, be more aggressive about capturing
    if (tracker.unseenCount() <= 15) {
        bonus += allCaptured.length * 1; // Extra value per card in late game
    }

    return bonus;
}

/**
 * Evaluate how "safe" the table state is (negative = dangerous for us).
 */
function evaluateTableSafety(tableCards) {
    if (tableCards.length === 0) return 0;

    let score = 0;
    const totalSum = tableCards.reduce((s, c) => s + c.value, 0);

    // If total sum <= 10, opponent could sweep with one card
    if (totalSum <= 10) {
        score += W.LEAVE_SWEEP_RISK;
    }

    // Count how many card values (1-10) could capture something from this table
    for (let v = 1; v <= 10; v++) {
        const hasMatch = tableCards.some(c => c.value === v);
        if (hasMatch) {
            score += W.LEAVE_EASY_CAPTURE;
        }
    }

    return score;
}
