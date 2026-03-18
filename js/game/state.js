import { createDeck, shuffle, sameCard } from './deck.js';
import { findCaptures, executeCapture, executeDrop, canCapture } from './rules.js';
import { scoreHand } from './scoring.js';

/**
 * Game state machine for Scopa.
 *
 * States:
 *   DEALING       - Dealing cards animation
 *   PLAYER_TURN   - Waiting for player to select and play a card
 *   PLAYER_CAPTURE- Player must choose which capture set to take
 *   AI_TURN       - AI is "thinking" and will play
 *   CAPTURE_ANIM  - Brief animation of capture
 *   SWEEP_ANIM    - Scopa celebration
 *   ROUND_END     - Check if more cards to deal or hand is over
 *   HAND_END      - Score the hand, show breakdown
 *   GAME_OVER     - Final result
 */

export const STATE = {
    DEAL_ANIM:      'DEAL_ANIM',
    DEALING:        'DEALING',
    PLAYER_TURN:    'PLAYER_TURN',
    PLAYER_CAPTURE: 'PLAYER_CAPTURE',
    AI_TURN:        'AI_TURN',
    CAPTURE_ANIM:   'CAPTURE_ANIM',
    SWEEP_ANIM:     'SWEEP_ANIM',
    ROUND_END:      'ROUND_END',
    HAND_END:       'HAND_END',
    GAME_OVER:      'GAME_OVER',
    HANDOVER:       'HANDOVER',
    PLAYER2_TURN:   'PLAYER2_TURN',
    PLAYER2_CAPTURE:'PLAYER2_CAPTURE',
};

export const WINNING_SCORE = 11;

export class GameState {
    constructor() {
        this.reset();
    }

    reset() {
        // Overall game state
        this.playerTotalScore = 0;
        this.computerTotalScore = 0;
        this.handNumber = 0;
        this.playerGoesFirst = true; // Alternates each hand

        // Current hand state
        this.deck = [];
        this.playerHand = [];
        this.computerHand = [];
        this.tableCards = [];
        this.playerCaptures = [];
        this.computerCaptures = [];
        this.playerSweeps = 0;
        this.computerSweeps = 0;
        this.lastCapturer = null; // 'player' or 'computer'
        this.dealsRemaining = 0;  // How many more 3-card deals are left

        // Turn state
        this.currentState = STATE.DEALING;
        this.selectedCardIndex = 0; // Player's selected card in hand
        this.selectedCaptureIndex = 0; // Selected capture option
        this.captureOptions = [];   // Available capture sets
        this.currentPlayer = 'player'; // 'player' or 'computer'

        // Animation timers
        this.stateTimer = 0;
        this.animData = null;

        // Last hand score breakdown (for display)
        this.lastScoreBreakdown = null;

        // Message to display
        this.message = '';

        // Deal animation queue
        this.dealAnimQueue = [];

        // Game mode: 'vs_cpu' or 'vs_human'
        this.gameMode = 'vs_cpu';

        // Difficulty: 'easy', 'medium', 'hard'
        this.difficulty = 'medium';
    }

    /**
     * Start a new hand.
     */
    startHand() {
        this.handNumber++;
        this.deck = shuffle(createDeck());
        this.playerHand = [];
        this.computerHand = [];
        this.tableCards = [];
        this.playerCaptures = [];
        this.computerCaptures = [];
        this.playerSweeps = 0;
        this.computerSweeps = 0;
        this.lastCapturer = null;

        // Deal 4 cards to table
        for (let i = 0; i < 4; i++) {
            this.tableCards.push(this.deck.pop());
        }

        // Deal 3 to each player
        this.dealToPlayers();

        // Determine who goes first (alternates)
        this.currentPlayer = this.playerGoesFirst ? 'player' : 'computer';

        // Calculate deals remaining (deck has 40-4-6 = 30 cards left, 6 per round = 5 more deals)
        this.dealsRemaining = Math.floor(this.deck.length / 6);

        // Build deal animation queue
        this._buildDealAnimQueue(true);

        this.currentState = STATE.DEAL_ANIM;
        this.stateTimer = 0;
        this.message = '';
    }

    /**
     * Deal 3 cards to each player from the deck.
     */
    dealToPlayers() {
        for (let i = 0; i < 3; i++) {
            if (this.deck.length > 0) this.playerHand.push(this.deck.pop());
            if (this.deck.length > 0) this.computerHand.push(this.deck.pop());
        }
    }

    /**
     * Build the deal animation queue.
     * @param {boolean} includeTable - true for first deal (include 4 table cards)
     */
    _buildDealAnimQueue(includeTable) {
        this.dealAnimQueue = [];
        if (includeTable) {
            for (let i = 0; i < this.tableCards.length; i++) {
                this.dealAnimQueue.push({ type: 'table', index: i, card: this.tableCards[i] });
            }
        }
        for (let i = 0; i < this.playerHand.length; i++) {
            this.dealAnimQueue.push({ type: 'player', index: i, card: this.playerHand[i] });
        }
        for (let i = 0; i < this.computerHand.length; i++) {
            this.dealAnimQueue.push({ type: 'cpu', index: i, card: this.computerHand[i] });
        }
    }

    /**
     * Check if the current deal round is finished (both hands empty).
     */
    isRoundOver() {
        return this.playerHand.length === 0 && this.computerHand.length === 0;
    }

    /**
     * Check if the entire hand is finished (no more cards anywhere).
     */
    isHandOver() {
        return this.isRoundOver() && this.deck.length === 0;
    }

    /**
     * Check if this is the very last play of the hand.
     */
    isLastPlay() {
        const totalCardsLeft = this.playerHand.length + this.computerHand.length + this.deck.length;
        return totalCardsLeft <= 1; // The card about to be played is the last one
    }

    /**
     * Player plays a card from their hand.
     * Returns the new state to transition to.
     */
    playerPlayCard(handIndex) {
        if (handIndex < 0 || handIndex >= this.playerHand.length) return this.currentState;

        const card = this.playerHand[handIndex];
        const captures = findCaptures(card, this.tableCards);

        // Remove card from hand
        this.playerHand.splice(handIndex, 1);

        if (captures.length === 0) {
            // No capture — drop the card on the table
            executeDrop(card, this.tableCards);
            this.message = '';
            this.animData = { card, action: 'drop' };
            return this._afterPlay('player');
        } else if (captures.length === 1) {
            // Single capture option — auto-execute
            return this._executePlayerCapture(card, captures[0]);
        } else {
            // Multiple capture options — player must choose
            this.captureOptions = captures;
            this.selectedCaptureIndex = 0;
            this.animData = { card };
            this.currentState = STATE.PLAYER_CAPTURE;
            return STATE.PLAYER_CAPTURE;
        }
    }

    /**
     * Player selects a capture set (when multiple options).
     */
    playerSelectCapture(captureIndex) {
        if (captureIndex < 0 || captureIndex >= this.captureOptions.length) return;

        const card = this.animData.card;
        const captureSet = this.captureOptions[captureIndex];
        return this._executePlayerCapture(card, captureSet);
    }

    _executePlayerCapture(card, captureSet) {
        const isLast = this.isLastPlay() && this.computerHand.length === 0 && this.deck.length === 0;
        const result = executeCapture(card, captureSet, this.tableCards, isLast);

        this.playerCaptures.push(...result.capturedCards);
        this.lastCapturer = 'player';

        if (result.isScopa) {
            this.playerSweeps++;
            this.message = 'SCOPA!';
            this.animData = { card, action: 'scopa', captured: captureSet };
            this.currentState = STATE.SWEEP_ANIM;
            this.stateTimer = 0;
            return STATE.SWEEP_ANIM;
        }

        this.message = '';
        this.animData = { card, action: 'capture', captured: captureSet };
        return this._afterPlay('player');
    }

    /**
     * AI plays a card. Called by the gameplay screen after AI thinking delay.
     * The AI module provides the play decision externally.
     */
    aiPlayCard(card, captureSet) {
        // Remove card from computer hand
        const idx = this.computerHand.findIndex(c => sameCard(c, card));
        if (idx !== -1) this.computerHand.splice(idx, 1);

        if (!captureSet) {
            // Drop
            executeDrop(card, this.tableCards);
            this.message = '';
            this.animData = { card, action: 'drop' };
            return this._afterPlay('computer');
        }

        const isLast = this.isLastPlay() && this.playerHand.length === 0 && this.deck.length === 0;
        const result = executeCapture(card, captureSet, this.tableCards, isLast);

        this.computerCaptures.push(...result.capturedCards);
        this.lastCapturer = 'computer';

        if (result.isScopa) {
            this.computerSweeps++;
            this.message = 'Computer SCOPA!';
            this.animData = { card, action: 'scopa', captured: captureSet };
            this.currentState = STATE.SWEEP_ANIM;
            this.stateTimer = 0;
            return STATE.SWEEP_ANIM;
        }

        this.message = '';
        this.animData = { card, action: 'capture', captured: captureSet };
        return this._afterPlay('computer');
    }

    /**
     * After a player or AI plays, determine next state.
     */
    _afterPlay(who) {
        // Switch to the other player
        this.currentPlayer = (who === 'player') ? 'computer' : 'player';

        // If a capture happened, go through capture animation first
        if (this.animData && this.animData.action === 'capture') {
            this.currentState = STATE.CAPTURE_ANIM;
            this.stateTimer = 0;
            this._afterPlayWho = who;
            return STATE.CAPTURE_ANIM;
        }

        return this._continueAfterPlay();
    }

    /**
     * Continue after capture animation completes.
     */
    _continueAfterPlay() {
        // Check if round is over
        if (this.isRoundOver()) {
            if (this.isHandOver()) {
                // Give remaining table cards to last capturer
                if (this.lastCapturer === 'player') {
                    this.playerCaptures.push(...this.tableCards);
                } else if (this.lastCapturer === 'computer') {
                    this.computerCaptures.push(...this.tableCards);
                }
                this.tableCards = [];

                this.currentState = STATE.HAND_END;
                this.stateTimer = 0;
                return STATE.HAND_END;
            } else {
                // Deal more cards
                this.currentState = STATE.ROUND_END;
                this.stateTimer = 0;
                return STATE.ROUND_END;
            }
        }

        // In 2P mode, always go through handover between turns
        if (this.gameMode === 'vs_human') {
            this.currentState = STATE.HANDOVER;
            this.stateTimer = 0;
            return STATE.HANDOVER;
        }

        // Next player's turn (vs CPU)
        if (this.currentPlayer === 'player') {
            this.currentState = STATE.PLAYER_TURN;
            this.selectedCardIndex = Math.min(this.selectedCardIndex, this.playerHand.length - 1);
            if (this.selectedCardIndex < 0) this.selectedCardIndex = 0;
        } else {
            this.currentState = STATE.AI_TURN;
            this.stateTimer = 0;
        }
        return this.currentState;
    }

    /**
     * Player 2 plays a card from the computer hand (2P mode).
     */
    player2PlayCard(handIndex) {
        if (handIndex < 0 || handIndex >= this.computerHand.length) return this.currentState;

        const card = this.computerHand[handIndex];
        const captures = findCaptures(card, this.tableCards);

        this.computerHand.splice(handIndex, 1);

        if (captures.length === 0) {
            executeDrop(card, this.tableCards);
            this.message = '';
            this.animData = { card, action: 'drop' };
            return this._afterPlay('computer');
        } else if (captures.length === 1) {
            return this._executePlayer2Capture(card, captures[0]);
        } else {
            this.captureOptions = captures;
            this.selectedCaptureIndex = 0;
            this.animData = { card };
            this.currentState = STATE.PLAYER2_CAPTURE;
            return STATE.PLAYER2_CAPTURE;
        }
    }

    /**
     * Player 2 selects a capture set (when multiple options).
     */
    player2SelectCapture(captureIndex) {
        if (captureIndex < 0 || captureIndex >= this.captureOptions.length) return;
        const card = this.animData.card;
        const captureSet = this.captureOptions[captureIndex];
        return this._executePlayer2Capture(card, captureSet);
    }

    _executePlayer2Capture(card, captureSet) {
        const isLast = this.isLastPlay() && this.playerHand.length === 0 && this.deck.length === 0;
        const result = executeCapture(card, captureSet, this.tableCards, isLast);

        this.computerCaptures.push(...result.capturedCards);
        this.lastCapturer = 'computer';

        if (result.isScopa) {
            this.computerSweeps++;
            this.message = 'Player 2 SCOPA!';
            this.animData = { card, action: 'scopa', captured: captureSet };
            this.currentState = STATE.SWEEP_ANIM;
            this.stateTimer = 0;
            return STATE.SWEEP_ANIM;
        }

        this.message = '';
        this.animData = { card, action: 'capture', captured: captureSet };
        return this._afterPlay('computer');
    }

    /**
     * Start a redeal (3 cards to each player) with animation.
     * Called from gameplay screen when ROUND_END timer expires.
     */
    startRedeal() {
        this.dealToPlayers();
        this.dealsRemaining = Math.floor(this.deck.length / 6);
        this._buildDealAnimQueue(false);
        this.currentState = STATE.DEAL_ANIM;
        this.stateTimer = 0;
    }

    /**
     * Score the current hand and update totals.
     */
    scoreCurrentHand() {
        const result = scoreHand(
            this.playerCaptures,
            this.computerCaptures,
            this.playerSweeps,
            this.computerSweeps
        );

        this.playerTotalScore += result.player.total;
        this.computerTotalScore += result.computer.total;
        this.lastScoreBreakdown = result;

        // Alternate who goes first
        this.playerGoesFirst = !this.playerGoesFirst;

        return result;
    }

    /**
     * Check if the game is over (either player reached winning score).
     */
    isGameOver() {
        return this.playerTotalScore >= WINNING_SCORE ||
               this.computerTotalScore >= WINNING_SCORE;
    }

    /**
     * Get the winner. Returns 'player', 'computer', or 'tie'.
     */
    getWinner() {
        if (this.playerTotalScore > this.computerTotalScore) return 'player';
        if (this.computerTotalScore > this.playerTotalScore) return 'computer';
        return 'tie';
    }
}
