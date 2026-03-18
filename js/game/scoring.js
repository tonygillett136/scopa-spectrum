import { SUIT_DENARI } from '../data/cards.js';

/**
 * Scopa scoring system.
 *
 * Points awarded per hand:
 *   Carte     - 1 point for most cards captured (tie = no point)
 *   Denari    - 1 point for most coin-suit cards (tie = no point)
 *   Settebello - 1 point for capturing the 7 of Denari
 *   Primiera  - 1 point for highest Primiera total (tie = no point)
 *   Scope     - 1 point per sweep
 */

// Primiera values for each card face value
const PRIMIERA_VALUES = {
    7: 21,
    6: 18,
    1: 16, // Ace
    5: 15,
    4: 14,
    3: 13,
    2: 12,
    8: 10, // Fante
    9: 10, // Cavallo
    10: 10, // Re
};

/**
 * Calculate the Primiera score for a capture pile.
 * Takes the highest primiera-value card from each suit.
 * Must have at least one card in all 4 suits to score.
 * Returns 0 if any suit is missing.
 */
export function calculatePrimiera(captures) {
    const bestPerSuit = {};

    for (const card of captures) {
        const pVal = PRIMIERA_VALUES[card.value];
        if (!bestPerSuit[card.suit] || pVal > bestPerSuit[card.suit]) {
            bestPerSuit[card.suit] = pVal;
        }
    }

    // Must have at least one card in each of the 4 suits
    const suits = [0, 1, 2, 3];
    if (suits.some(s => !bestPerSuit[s])) {
        return 0; // Cannot score primiera — missing a suit
    }

    return suits.reduce((sum, s) => sum + bestPerSuit[s], 0);
}

/**
 * Score a completed hand.
 *
 * Returns {
 *   player: { total, carte, denari, settebello, primiera, scope },
 *   computer: { total, carte, denari, settebello, primiera, scope },
 *   breakdown: [] // Array of {category, player, computer, winner} for display
 * }
 */
export function scoreHand(playerCaptures, computerCaptures, playerSweeps, computerSweeps) {
    const player = { total: 0, carte: 0, denari: 0, settebello: 0, primiera: 0, scope: 0 };
    const computer = { total: 0, carte: 0, denari: 0, settebello: 0, primiera: 0, scope: 0 };
    const breakdown = [];

    // 1. Carte (most cards)
    const pCards = playerCaptures.length;
    const cCards = computerCaptures.length;
    if (pCards > cCards) {
        player.carte = 1;
        player.total += 1;
        breakdown.push({ category: 'Carte', player: pCards, computer: cCards, winner: 'player' });
    } else if (cCards > pCards) {
        computer.carte = 1;
        computer.total += 1;
        breakdown.push({ category: 'Carte', player: pCards, computer: cCards, winner: 'computer' });
    } else {
        breakdown.push({ category: 'Carte', player: pCards, computer: cCards, winner: 'tie' });
    }

    // 2. Denari (most coin-suit cards)
    const pDenari = playerCaptures.filter(c => c.suit === SUIT_DENARI).length;
    const cDenari = computerCaptures.filter(c => c.suit === SUIT_DENARI).length;
    if (pDenari > cDenari) {
        player.denari = 1;
        player.total += 1;
        breakdown.push({ category: 'Denari', player: pDenari, computer: cDenari, winner: 'player' });
    } else if (cDenari > pDenari) {
        computer.denari = 1;
        computer.total += 1;
        breakdown.push({ category: 'Denari', player: pDenari, computer: cDenari, winner: 'computer' });
    } else {
        breakdown.push({ category: 'Denari', player: pDenari, computer: cDenari, winner: 'tie' });
    }

    // 3. Settebello (7 of Denari)
    const playerHasSettebello = playerCaptures.some(c => c.suit === SUIT_DENARI && c.value === 7);
    if (playerHasSettebello) {
        player.settebello = 1;
        player.total += 1;
        breakdown.push({ category: 'Settebello', player: 1, computer: 0, winner: 'player' });
    } else {
        computer.settebello = 1;
        computer.total += 1;
        breakdown.push({ category: 'Settebello', player: 0, computer: 1, winner: 'computer' });
    }

    // 4. Primiera
    const pPrimiera = calculatePrimiera(playerCaptures);
    const cPrimiera = calculatePrimiera(computerCaptures);
    if (pPrimiera > cPrimiera) {
        player.primiera = 1;
        player.total += 1;
        breakdown.push({ category: 'Primiera', player: pPrimiera, computer: cPrimiera, winner: 'player' });
    } else if (cPrimiera > pPrimiera) {
        computer.primiera = 1;
        computer.total += 1;
        breakdown.push({ category: 'Primiera', player: pPrimiera, computer: cPrimiera, winner: 'computer' });
    } else {
        breakdown.push({ category: 'Primiera', player: pPrimiera, computer: cPrimiera, winner: 'tie' });
    }

    // 5. Scope (sweeps)
    player.scope = playerSweeps;
    player.total += playerSweeps;
    computer.scope = computerSweeps;
    computer.total += computerSweeps;
    if (playerSweeps > 0 || computerSweeps > 0) {
        breakdown.push({
            category: 'Scope',
            player: playerSweeps,
            computer: computerSweeps,
            winner: playerSweeps > computerSweeps ? 'player' :
                    computerSweeps > playerSweeps ? 'computer' : 'tie'
        });
    }

    return { player, computer, breakdown };
}
