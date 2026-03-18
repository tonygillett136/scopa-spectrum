import { SUIT_COPPE, SUIT_DENARI, SUIT_BASTONI, SUIT_SPADE, SUIT_NAMES, VALUE_NAMES } from '../data/cards.js';

/**
 * Card and deck management for the 40-card Italian (Napoletane) deck.
 */

/**
 * Create a card object.
 */
export function createCard(suit, value) {
    return {
        suit,
        value,
        id: suit * 10 + (value - 1), // Unique ID 0-39
    };
}

/**
 * Create a full 40-card deck.
 */
export function createDeck() {
    const deck = [];
    const suits = [SUIT_COPPE, SUIT_DENARI, SUIT_BASTONI, SUIT_SPADE];
    for (const suit of suits) {
        for (let value = 1; value <= 10; value++) {
            deck.push(createCard(suit, value));
        }
    }
    return deck;
}

/**
 * Fisher-Yates shuffle (in place).
 */
export function shuffle(deck) {
    for (let i = deck.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [deck[i], deck[j]] = [deck[j], deck[i]];
    }
    return deck;
}

/**
 * Get a human-readable card name.
 */
export function cardName(card) {
    return `${VALUE_NAMES[card.value]} di ${SUIT_NAMES[card.suit]}`;
}

/**
 * Check if two cards are the same (by ID).
 */
export function sameCard(a, b) {
    return a.id === b.id;
}
