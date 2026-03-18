import { sameCard } from './deck.js';

/**
 * Scopa rules engine.
 *
 * Core rules:
 * - Play a card from hand to table
 * - If the played card's value matches a single table card, capture it
 * - If the played card's value equals the sum of multiple table cards, capture them
 * - If a single-card match exists, you MUST take the single card (priority rule)
 * - If you can capture, you MUST capture (mandatory capture)
 * - Capturing ALL table cards is a "scopa" (sweep) worth 1 bonus point
 * - Exception: the very last capture of the last deal is never a scopa
 */

/**
 * Find all possible capture sets for a played card against the table.
 * Returns an array of capture options, where each option is an array of table cards.
 *
 * If single-card matches exist, ONLY single-card options are returned (priority rule).
 * If no captures possible, returns an empty array.
 */
export function findCaptures(playedCard, tableCards) {
    const value = playedCard.value;

    // 1. Check single-card matches first
    const singles = [];
    for (const card of tableCards) {
        if (card.value === value) {
            singles.push([card]);
        }
    }

    // Priority rule: if single match exists, must take single card
    if (singles.length > 0) {
        return singles;
    }

    // 2. Find all multi-card subsets that sum to the played card's value
    // Table typically has ≤10 cards, so 2^10 = 1024 combinations is trivial
    const multiCaptures = [];
    const n = tableCards.length;

    for (let mask = 3; mask < (1 << n); mask++) { // Start at 3 (skip 0, 1, 2 = single cards)
        // Skip single-card subsets (already handled above)
        if ((mask & (mask - 1)) === 0) continue; // Power of 2 = single bit = single card

        let sum = 0;
        const subset = [];
        for (let i = 0; i < n; i++) {
            if (mask & (1 << i)) {
                sum += tableCards[i].value;
                subset.push(tableCards[i]);
                if (sum > value) break; // Early exit if sum exceeds target
            }
        }
        if (sum === value) {
            multiCaptures.push(subset);
        }
    }

    return multiCaptures;
}

/**
 * Check if a played card can capture anything.
 */
export function canCapture(playedCard, tableCards) {
    return findCaptures(playedCard, tableCards).length > 0;
}

/**
 * Check if any card in a hand can capture something from the table.
 */
export function hasAnyCapture(hand, tableCards) {
    return hand.some(card => canCapture(card, tableCards));
}

/**
 * Execute a capture: remove captured cards from table, add them + played card to capture pile.
 * Returns { capturedCards, isScopa }
 *
 * @param playedCard - The card played from hand
 * @param capturedSet - Array of table cards being captured
 * @param tableCards - Current table cards (will be mutated — cards removed)
 * @param isLastPlay - Whether this is the very last play of the hand (no scopa)
 */
export function executeCapture(playedCard, capturedSet, tableCards, isLastPlay = false) {
    // Remove captured cards from table
    for (const captured of capturedSet) {
        const idx = tableCards.findIndex(c => sameCard(c, captured));
        if (idx !== -1) {
            tableCards.splice(idx, 1);
        }
    }

    // All captured cards (played card + captured set)
    const allCaptured = [playedCard, ...capturedSet];

    // Check for scopa (table cleared, and not the last play)
    const isScopa = tableCards.length === 0 && !isLastPlay;

    return { capturedCards: allCaptured, isScopa };
}

/**
 * Execute a drop: place a card on the table (no capture possible).
 */
export function executeDrop(playedCard, tableCards) {
    tableCards.push(playedCard);
}
