import { GameState, STATE, WINNING_SCORE } from '../game/state.js';
import { aiSelectPlay, CardTracker, DIFFICULTY } from '../game/ai.js';
import { findCaptures, canCapture } from '../game/rules.js';
import {
    getCardSprite, getCardBack, SUIT_NAMES, VALUE_NAMES,
    CARD_COLS, CARD_ROWS, CARD_H, SUIT_DENARI
} from '../data/cards.js';
import { cardName } from '../game/deck.js';
import * as C from '../spectrum/constants.js';
import {
    SFX_CARD_PLAY, SFX_CARD_CAPTURE, SFX_SCOPA, SFX_DEAL, SFX_DEAL_CARD,
    SFX_MENU_MOVE, SFX_SCORE_POINT, SFX_WIN, SFX_LOSE,
    SFX_ROUND_END, SFX_KEY
} from '../audio/sfx.js';

/**
 * Main gameplay screen.
 *
 * Layout (32x24 character grid) for 10x16 cell cards:
 *   Row 0:        Score header (You:XX CPU:XX Deck:XX)
 *   Row 1:        View label ("=== YOUR HAND ===" / "=== TABLE ===")
 *   Rows 2-17:    Card display area (16 rows = 1 card height)
 *   Row 18:       Card info / cursor (^^^^^^^^^^ under selected card)
 *   Rows 19-21:   Messages / capture choice
 *   Row 22:       Nav hints (Up:Table / Down:Hand)
 *   Row 23:       Status / controls
 *
 * Up/Down arrows toggle between Hand View and Table View.
 * Auto-switching: PLAYER_TURN->Hand, AI_TURN->Table, PLAYER_CAPTURE->Table.
 */

const AI_THINK_MIN = 600;
const AI_THINK_MAX = 1400;
const DEAL_PAUSE_TIME = 300;
const SWEEP_ANIM_TIME = 1500;
const HANDOVER_MIN_TIME = 300; // Minimum time before space is accepted
const AI_RESULT_DISPLAY_MS = 1200; // Time to show CPU's play before transitioning

// Animation speeds (ms per character-cell step)
const DEAL_STEP_MS = 35;
const CAPTURE_STEP_MS = 30;
const DEAL_COLS_PER_STEP = 2;
const CAPTURE_COLS_PER_STEP = 2;

// View modes
const VIEW_HAND = 0;
const VIEW_TABLE = 1;

// Layout rows
const CARD_START_ROW = 2;
const CARD_INFO_ROW = 18;
const MESSAGE_ROW = 19;
const NAV_ROW = 22;
const STATUS_ROW = 23;

// Card spacing: 3 cards x 10 cols + 2 x 1-col gap = 32 cols
const CARD_POSITIONS_3 = [0, 11, 22];

// Deck position (right edge, off-screen)
const DECK_COL = 30;

// Rainbow colours for scopa celebration
const RAINBOW = [C.RED, C.YELLOW, C.GREEN, C.CYAN, C.BLUE, C.MAGENTA];

export class GameplayScreen {
    constructor(beeper, options, onGameOver) {
        this.beeper = beeper;
        this.onGameOver = onGameOver;

        // Options
        this.difficulty = (options && options.difficulty) || 'medium';
        this.mode = (options && options.mode) || 'vs_cpu';
        this.matchState = (options && options.matchState) || null;
        this.stats = (options && options.stats) || null;

        this.game = new GameState();
        this.tracker = new CardTracker();
        this.needsRedraw = true;
        this.aiThinkTime = 0;
        this.aiDecision = null;
        this.aiResultTimer = 0;
        this.aiResultPending = false;
        this.ctx = null;
        this.currentView = VIEW_HAND;

        // Deal animation state
        this.dealAnim = null;

        // Capture animation state
        this.captureAnim = null;

        // Border state
        this.prevBorderState = null;
        this.borderFlashTimer = 0;
        this.scopaStripeBuffer = null;
    }

    _sfx(notes) {
        if (this.beeper) this.beeper.playSequence(notes);
    }

    _is2P() {
        return this.mode === 'vs_human';
    }

    enter(ctx) {
        this.ctx = ctx;
        this.game.reset();
        this.game.gameMode = this.mode;
        this.game.difficulty = this.difficulty;
        this.tracker.reset();
        this.game.startHand();

        // Mark initial table cards as seen
        this.tracker.markMultipleSeen(this.game.tableCards);

        // Start with deal animation
        this._initDealAnim();
        this.currentView = VIEW_TABLE;
        this.needsRedraw = true;

        // Allocate stripe buffer for scopa celebration
        this.scopaStripeBuffer = new Uint8Array(C.CANVAS_H);
    }

    // ================================================================
    // Deal animation
    // ================================================================

    _initDealAnim() {
        const g = this.game;
        const queue = g.dealAnimQueue;
        if (!queue || queue.length === 0) {
            this._finishDealAnim();
            return;
        }

        // In 2P mode with no table cards (redeal), skip animation
        if (this._is2P() && !queue.some(e => e.type === 'table')) {
            this._finishDealAnim();
            return;
        }

        // Calculate target positions for each card in the queue
        const targets = [];
        for (const entry of queue) {
            let col;
            if (entry.type === 'table') {
                const tablePositions = this._tableCardPositions(g.tableCards.length);
                col = tablePositions[entry.index] ?? 11;
            } else if (entry.type === 'player') {
                if (this._is2P()) {
                    // Skip player card visuals in 2P mode
                    col = -CARD_COLS;
                } else {
                    const handPositions = this._handCardPositions(g.playerHand.length);
                    col = handPositions[entry.index] ?? 11;
                }
            } else {
                // CPU cards — slide to left edge (off-screen)
                col = -CARD_COLS;
            }
            targets.push(col);
        }

        this.dealAnim = {
            queue,
            targets,
            index: 0,
            currentCol: DECK_COL,
            timer: 0,
            arrivedCount: 0,
        };

        // Show table view for table cards
        if (queue[0].type === 'table') {
            this.currentView = VIEW_TABLE;
        }

        this._sfx(SFX_DEAL);
    }

    _updateDealAnim(dt) {
        const anim = this.dealAnim;
        if (!anim) return;

        anim.timer += dt;

        if (anim.timer >= DEAL_STEP_MS) {
            anim.timer -= DEAL_STEP_MS;

            const entry = anim.queue[anim.index];
            const target = anim.targets[anim.index];

            // Move toward target
            if (anim.currentCol > target) {
                anim.currentCol = Math.max(target, anim.currentCol - DEAL_COLS_PER_STEP);
            } else if (anim.currentCol < target) {
                anim.currentCol = Math.min(target, anim.currentCol + DEAL_COLS_PER_STEP);
            }

            // Check if arrived
            if (anim.currentCol === target) {
                anim.arrivedCount++;
                this._sfx(SFX_DEAL_CARD);

                // Move to next card
                anim.index++;
                if (anim.index < anim.queue.length) {
                    anim.currentCol = DECK_COL;

                    const nextEntry = anim.queue[anim.index];

                    if (nextEntry.type === 'player' && this.currentView !== VIEW_HAND) {
                        if (this._is2P()) {
                            // In 2P mode, skip all player and cpu cards
                            while (anim.index < anim.queue.length) {
                                anim.arrivedCount++;
                                anim.index++;
                            }
                            this._finishDealAnim();
                            return;
                        }
                        this.currentView = VIEW_HAND;
                    } else if (nextEntry.type === 'cpu') {
                        // Skip CPU cards visually
                        while (anim.index < anim.queue.length && anim.queue[anim.index].type === 'cpu') {
                            anim.arrivedCount++;
                            anim.index++;
                        }
                        if (anim.index >= anim.queue.length) {
                            this._finishDealAnim();
                            return;
                        }
                        anim.currentCol = DECK_COL;
                    }
                } else {
                    // All cards dealt
                    this._finishDealAnim();
                    return;
                }
            }

            this.needsRedraw = true;
        }
    }

    _finishDealAnim() {
        this.dealAnim = null;
        const g = this.game;

        // Brief pause then start play
        g.currentState = STATE.DEALING;
        g.stateTimer = 0;
    }

    _drawDealAnim(gfx) {
        const anim = this.dealAnim;
        if (!anim) return;

        const g = this.game;

        if (this.currentView === VIEW_TABLE) {
            // Draw arrived table cards
            for (let i = 0; i < anim.arrivedCount && i < g.tableCards.length; i++) {
                const positions = this._tableCardPositions(g.tableCards.length);
                const sprite = getCardSprite(g.tableCards[i].suit, g.tableCards[i].value);
                this._drawCardAt(positions[i], CARD_START_ROW, sprite);
            }

            // Draw currently animating card (if it's a table card)
            if (anim.index < anim.queue.length && anim.queue[anim.index].type === 'table') {
                const entry = anim.queue[anim.index];
                const sprite = getCardSprite(entry.card.suit, entry.card.value);
                if (anim.currentCol >= 0 && anim.currentCol < 32) {
                    this._drawCardAt(anim.currentCol, CARD_START_ROW, sprite);
                }
            }
        } else if (this.currentView === VIEW_HAND) {
            // Draw arrived player cards
            const handPositions = this._handCardPositions(g.playerHand.length);
            let arrivedPlayerCards = 0;
            for (const e of anim.queue) {
                if (e.type === 'player') {
                    const entryIdx = anim.queue.indexOf(e);
                    if (entryIdx < anim.index) {
                        if (arrivedPlayerCards < handPositions.length) {
                            const sprite = getCardSprite(e.card.suit, e.card.value);
                            this._drawCardAt(handPositions[arrivedPlayerCards], CARD_START_ROW, sprite);
                        }
                        arrivedPlayerCards++;
                    }
                }
            }

            // Draw currently animating player card
            if (anim.index < anim.queue.length && anim.queue[anim.index].type === 'player') {
                const entry = anim.queue[anim.index];
                const sprite = getCardSprite(entry.card.suit, entry.card.value);
                if (anim.currentCol >= 0 && anim.currentCol < 32) {
                    this._drawCardAt(anim.currentCol, CARD_START_ROW, sprite);
                }
            }
        }

        // Draw deck indicator
        if (g.deck.length > 0 && DECK_COL < 32) {
            const back = getCardBack();
            this._drawCardPartial(DECK_COL, CARD_START_ROW, back, 32 - DECK_COL);
        }
    }

    // ================================================================
    // Capture animation
    // ================================================================

    _initCaptureAnim(who) {
        const g = this.game;
        const captured = g.animData?.captured;
        if (!captured || captured.length === 0) {
            this._finishCaptureAnim();
            return;
        }

        const count = captured.length;
        const positions = [];
        const totalWidth = count * CARD_COLS + (count - 1);
        const startCol = Math.max(0, Math.floor((32 - totalWidth) / 2));
        for (let i = 0; i < count; i++) {
            positions.push(startCol + i * (CARD_COLS + 1));
        }

        const direction = who === 'player' ? -1 : 1;
        const targetCol = direction === -1 ? -CARD_COLS - 1 : 33;

        this.captureAnim = {
            cards: captured,
            sprites: captured.map(c => getCardSprite(c.suit, c.value)),
            currentCols: [...positions],
            targetCol,
            direction,
            timer: 0,
        };

        this.currentView = VIEW_TABLE;
        this.needsRedraw = true;
    }

    _updateCaptureAnim(dt) {
        const anim = this.captureAnim;
        if (!anim) return;

        anim.timer += dt;

        if (anim.timer >= CAPTURE_STEP_MS) {
            anim.timer -= CAPTURE_STEP_MS;

            let allDone = true;
            for (let i = 0; i < anim.currentCols.length; i++) {
                if (anim.direction === -1) {
                    anim.currentCols[i] -= CAPTURE_COLS_PER_STEP;
                    if (anim.currentCols[i] > anim.targetCol) allDone = false;
                } else {
                    anim.currentCols[i] += CAPTURE_COLS_PER_STEP;
                    if (anim.currentCols[i] < anim.targetCol) allDone = false;
                }
            }

            this.needsRedraw = true;

            if (allDone) {
                this._finishCaptureAnim();
            }
        }
    }

    _finishCaptureAnim() {
        this.captureAnim = null;
        const g = this.game;
        g._continueAfterPlay();
        this._handlePostPlay();
        this.needsRedraw = true;
    }

    _drawCaptureAnim(gfx) {
        const anim = this.captureAnim;
        if (!anim) return;

        // Draw the remaining table cards
        this._drawTableCards(gfx);

        // Draw captured cards sliding away
        for (let i = 0; i < anim.cards.length; i++) {
            const col = anim.currentCols[i];
            if (col >= -CARD_COLS && col < 32) {
                this._drawCardAt(col, CARD_START_ROW, anim.sprites[i]);
            }
        }
    }

    // ================================================================
    // Border management
    // ================================================================

    _updateBorder() {
        const g = this.game;
        const { border } = this.ctx;

        switch (g.currentState) {
            case STATE.DEAL_ANIM:
            case STATE.DEALING:
                border.clearStripes();
                border.setColour(C.YELLOW);
                break;
            case STATE.PLAYER_TURN:
            case STATE.PLAYER_CAPTURE:
                border.clearStripes();
                border.setColour(C.BLUE);
                break;
            case STATE.PLAYER2_TURN:
            case STATE.PLAYER2_CAPTURE:
                border.clearStripes();
                border.setColour(C.RED);
                break;
            case STATE.AI_TURN:
                border.clearStripes();
                border.setColour(C.RED);
                break;
            case STATE.CAPTURE_ANIM:
                border.clearStripes();
                border.setColour(C.CYAN);
                break;
            case STATE.SWEEP_ANIM:
                this._generateScopaStripes();
                border.setStripes(this.scopaStripeBuffer);
                break;
            case STATE.ROUND_END:
                border.clearStripes();
                border.setColour(C.YELLOW);
                break;
            case STATE.HAND_END:
                border.clearStripes();
                border.setColour(C.GREEN);
                break;
            case STATE.HANDOVER:
                border.clearStripes();
                border.setColour(C.BLACK);
                break;
            case STATE.GAME_OVER: {
                border.clearStripes();
                const w = g.getWinner();
                if (this._is2P()) {
                    border.setColour(w === 'player' ? C.BLUE : w === 'computer' ? C.RED : C.CYAN);
                } else {
                    border.setColour(w === 'player' ? C.GREEN : w === 'computer' ? C.RED : C.CYAN);
                }
                break;
            }
            default:
                border.clearStripes();
                border.setColour(C.BLACK);
        }
    }

    _generateScopaStripes() {
        const buf = this.scopaStripeBuffer;
        if (!buf) return;
        const bandHeight = 6;
        const offset = Math.floor(this.game.stateTimer / 30) % (RAINBOW.length * bandHeight);
        for (let y = 0; y < C.CANVAS_H; y++) {
            const idx = Math.floor(((y + offset) % (RAINBOW.length * bandHeight)) / bandHeight);
            buf[y] = RAINBOW[idx];
        }
    }

    // ================================================================
    // Update
    // ================================================================

    update(dt) {
        const g = this.game;
        g.stateTimer += dt;

        switch (g.currentState) {
            case STATE.DEAL_ANIM:
                this._updateDealAnim(dt);
                break;

            case STATE.DEALING:
                if (g.stateTimer >= DEAL_PAUSE_TIME) {
                    if (this._is2P()) {
                        // In 2P mode, always handover after dealing
                        g.currentState = STATE.HANDOVER;
                        g.stateTimer = 0;
                        this.needsRedraw = true;
                    } else if (g.currentPlayer === 'player') {
                        g.currentState = STATE.PLAYER_TURN;
                        g.selectedCardIndex = 0;
                        this.currentView = VIEW_HAND;
                        this.needsRedraw = true;
                    } else {
                        g.currentState = STATE.AI_TURN;
                        this.currentView = VIEW_TABLE;
                        this._startAiThink();
                        this.needsRedraw = true;
                    }
                }
                break;

            case STATE.AI_TURN:
                if (this.aiResultPending) {
                    // Phase 2: showing result message, wait before executing
                    this.aiResultTimer -= dt;
                    if (this.aiResultTimer <= 0) {
                        this.aiResultPending = false;
                        this._executeAiPlay();
                    }
                } else {
                    // Phase 1: waiting for AI to "think"
                    this.aiThinkTime -= dt;
                    if (this.aiThinkTime <= 0 && this.aiDecision) {
                        const { card, captureSet } = this.aiDecision;

                        // Show the result message but don't execute yet
                        if (captureSet) {
                            const capNames = captureSet.map(c => VALUE_NAMES[c.value]).join('+');
                            g.message = `CPU takes ${capNames}`;
                            this._sfx(SFX_CARD_CAPTURE);
                        } else {
                            g.message = `CPU drops ${VALUE_NAMES[card.value]}`;
                            this._sfx(SFX_CARD_PLAY);
                        }

                        this.needsRedraw = true;

                        // Hold the message on screen before executing the play
                        this.aiResultPending = true;
                        this.aiResultTimer = AI_RESULT_DISPLAY_MS;
                    }
                }
                break;

            case STATE.SWEEP_ANIM:
                this.needsRedraw = true;
                if (g.stateTimer >= SWEEP_ANIM_TIME) {
                    this._handlePostSweep();
                    this.needsRedraw = true;
                }
                break;

            case STATE.CAPTURE_ANIM:
                this._updateCaptureAnim(dt);
                break;

            case STATE.ROUND_END:
                if (g.stateTimer >= 800) {
                    g.startRedeal();
                    this._initDealAnim();
                    this.needsRedraw = true;
                }
                break;

            case STATE.HAND_END:
                if (g.stateTimer <= dt + 1) {
                    this.needsRedraw = true;
                }
                break;

            case STATE.HANDOVER:
                // Just wait for input, but ensure minimum display time
                break;

            case STATE.PLAYER2_TURN:
            case STATE.PLAYER2_CAPTURE:
                // Input-driven, no update logic needed
                break;

            case STATE.GAME_OVER:
                break;
        }
    }

    _startAiThink() {
        if (this.game.computerHand.length === 0) {
            this.game.currentState = STATE.ROUND_END;
            this.game.stateTimer = 0;
            this.needsRedraw = true;
            return;
        }
        this.aiThinkTime = AI_THINK_MIN + Math.random() * (AI_THINK_MAX - AI_THINK_MIN);
        this.aiDecision = aiSelectPlay(
            this.game.computerHand,
            this.game.tableCards,
            this.tracker,
            this.difficulty
        );
        this.game.message = 'Computer is thinking...';
        this.needsRedraw = true;
    }

    _executeAiPlay() {
        const g = this.game;
        const { card, captureSet } = this.aiDecision;

        this.tracker.markSeen(card);
        if (captureSet) {
            this.tracker.markMultipleSeen(captureSet);
        }

        g.aiPlayCard(card, captureSet);
        this.aiDecision = null;
        this.needsRedraw = true;

        if (g.currentState === STATE.CAPTURE_ANIM) {
            this._initCaptureAnim(g._afterPlayWho || 'computer');
        } else {
            this._handlePostPlay();
        }
    }

    _handlePostPlay() {
        const g = this.game;

        if (g.currentState === STATE.SWEEP_ANIM) {
            this._sfx(SFX_SCOPA);
            return;
        }

        if (g.currentState === STATE.CAPTURE_ANIM) {
            return;
        }

        if (g.currentState === STATE.HAND_END) {
            this._scoreHand();
            return;
        }

        if (g.currentState === STATE.ROUND_END) {
            g.message = 'Dealing more cards...';
            this.needsRedraw = true;
            return;
        }

        if (g.currentState === STATE.HANDOVER) {
            // 2P mode: go to handover
            this.needsRedraw = true;
            return;
        }

        if (g.currentState === STATE.AI_TURN) {
            this.currentView = VIEW_TABLE;
            this._startAiThink();
            return;
        }

        if (g.currentState === STATE.PLAYER_TURN) {
            this.currentView = VIEW_HAND;
            g.selectedCardIndex = Math.min(g.selectedCardIndex, g.playerHand.length - 1);
            if (g.selectedCardIndex < 0) g.selectedCardIndex = 0;
        }
    }

    _handlePostSweep() {
        const g = this.game;

        g.currentPlayer = (g.currentPlayer === 'player') ? 'computer' : 'player';

        if (g.isRoundOver()) {
            if (g.isHandOver()) {
                g.currentState = STATE.HAND_END;
                g.stateTimer = 0;
                this._scoreHand();
            } else {
                g.currentState = STATE.ROUND_END;
                g.stateTimer = 0;
                g.message = 'Dealing more cards...';
            }
        } else if (this._is2P()) {
            g.currentState = STATE.HANDOVER;
            g.stateTimer = 0;
        } else {
            if (g.currentPlayer === 'player') {
                g.currentState = STATE.PLAYER_TURN;
                this.currentView = VIEW_HAND;
                g.selectedCardIndex = Math.min(g.selectedCardIndex, g.playerHand.length - 1);
                if (g.selectedCardIndex < 0) g.selectedCardIndex = 0;
            } else {
                g.currentState = STATE.AI_TURN;
                this.currentView = VIEW_TABLE;
                this._startAiThink();
            }
        }
    }

    _scoreHand() {
        const g = this.game;
        const result = g.scoreCurrentHand();
        g.lastScoreBreakdown = result;
        g.currentState = STATE.HAND_END;
        g.message = '';
        this._sfx(SFX_ROUND_END);

        // Record hand stats
        if (this.stats) {
            const capturedSettebello = g.playerCaptures.some(
                c => c.suit === SUIT_DENARI && c.value === 7
            );
            this.stats.recordHand(g.playerSweeps, g.computerSweeps, capturedSettebello);
        }

        this.needsRedraw = true;
    }

    // ================================================================
    // Input handling
    // ================================================================

    handleInput(key) {
        const g = this.game;

        if (key === 'm' || key === 'M') {
            if (this.beeper) {
                const muted = this.beeper.toggleMute();
                g.message = muted ? 'Sound OFF' : 'Sound ON';
                this.needsRedraw = true;
            }
            return;
        }

        switch (g.currentState) {
            case STATE.PLAYER_TURN:
                this._handlePlayerTurnInput(key, g.playerHand, 'player');
                break;

            case STATE.PLAYER_CAPTURE:
                this._handleCaptureChoiceInput(key, 'player');
                break;

            case STATE.PLAYER2_TURN:
                this._handlePlayerTurnInput(key, g.computerHand, 'player2');
                break;

            case STATE.PLAYER2_CAPTURE:
                this._handleCaptureChoiceInput(key, 'player2');
                break;

            case STATE.AI_TURN:
                // Allow skipping the AI result display
                if (this.aiResultPending && (key === ' ' || key === 'Enter')) {
                    this.aiResultPending = false;
                    this._executeAiPlay();
                }
                break;

            case STATE.HANDOVER:
                if ((key === ' ' || key === 'Enter') && g.stateTimer >= HANDOVER_MIN_TIME) {
                    this._sfx(SFX_KEY);
                    if (g.currentPlayer === 'player') {
                        g.currentState = STATE.PLAYER_TURN;
                        g.selectedCardIndex = Math.min(g.selectedCardIndex, g.playerHand.length - 1);
                        if (g.selectedCardIndex < 0) g.selectedCardIndex = 0;
                        this.currentView = VIEW_HAND;
                    } else {
                        g.currentState = STATE.PLAYER2_TURN;
                        g.selectedCardIndex = Math.min(g.selectedCardIndex, g.computerHand.length - 1);
                        if (g.selectedCardIndex < 0) g.selectedCardIndex = 0;
                        this.currentView = VIEW_HAND;
                    }
                    this.needsRedraw = true;
                }
                break;

            case STATE.HAND_END:
                if (key === ' ' || key === 'Enter') {
                    if (g.isGameOver()) {
                        g.currentState = STATE.GAME_OVER;
                        const winner = g.getWinner();

                        if (this._is2P()) {
                            this._sfx(winner === 'player' ? SFX_WIN : winner === 'computer' ? SFX_WIN : SFX_ROUND_END);
                        } else {
                            this._sfx(winner === 'player' ? SFX_WIN : SFX_LOSE);
                        }

                        // Record match
                        if (this.matchState) {
                            this.matchState.recordGame(winner);
                        }
                        // Record stats
                        if (this.stats) {
                            this.stats.recordGame(winner, this.difficulty, this.mode);
                        }

                        this.needsRedraw = true;
                    } else {
                        this.tracker.reset();
                        g.startHand();
                        this.tracker.markMultipleSeen(g.tableCards);
                        this._initDealAnim();
                        this.currentView = VIEW_TABLE;
                        this.needsRedraw = true;
                    }
                }
                break;

            case STATE.GAME_OVER:
                if (key === ' ' || key === 'Enter') {
                    if (this.matchState && !this.matchState.isMatchOver()) {
                        // Next game in match
                        this.game.reset();
                        this.game.gameMode = this.mode;
                        this.game.difficulty = this.difficulty;
                        this.tracker.reset();
                        this.game.startHand();
                        this.tracker.markMultipleSeen(this.game.tableCards);
                        this._initDealAnim();
                        this.currentView = VIEW_TABLE;
                        this.needsRedraw = true;
                    } else {
                        if (this.onGameOver) this.onGameOver();
                    }
                }
                break;
        }
    }

    _handlePlayerTurnInput(key, hand, who) {
        const g = this.game;

        switch (key) {
            case 'ArrowUp':
                if (this.currentView !== VIEW_TABLE) {
                    this.currentView = VIEW_TABLE;
                    this._sfx(SFX_MENU_MOVE);
                    this.needsRedraw = true;
                }
                break;

            case 'ArrowDown':
                if (this.currentView !== VIEW_HAND) {
                    this.currentView = VIEW_HAND;
                    this._sfx(SFX_MENU_MOVE);
                    this.needsRedraw = true;
                }
                break;

            case 'ArrowLeft':
                if (this.currentView === VIEW_HAND) {
                    if (g.selectedCardIndex > 0) {
                        g.selectedCardIndex--;
                        this._sfx(SFX_MENU_MOVE);
                    }
                    this.needsRedraw = true;
                }
                break;

            case 'ArrowRight':
                if (this.currentView === VIEW_HAND) {
                    if (g.selectedCardIndex < hand.length - 1) {
                        g.selectedCardIndex++;
                        this._sfx(SFX_MENU_MOVE);
                    }
                    this.needsRedraw = true;
                }
                break;

            case '1': case '2': case '3':
                {
                    const idx = parseInt(key) - 1;
                    if (idx < hand.length) {
                        g.selectedCardIndex = idx;
                        this.currentView = VIEW_HAND;
                        this.needsRedraw = true;
                    }
                }
                break;

            case ' ':
            case 'Enter':
                {
                    if (hand.length === 0) break;

                    const card = hand[g.selectedCardIndex];
                    if (!card) break;
                    this.tracker.markSeen(card);

                    const captures = findCaptures(card, g.tableCards);
                    if (captures.length > 0) {
                        this._sfx(SFX_CARD_CAPTURE);
                        this.tracker.markMultipleSeen(captures.length === 1 ? captures[0] : []);
                    } else {
                        this._sfx(SFX_CARD_PLAY);
                    }

                    if (who === 'player2') {
                        g.player2PlayCard(g.selectedCardIndex);
                    } else {
                        g.playerPlayCard(g.selectedCardIndex);
                    }
                    this.needsRedraw = true;

                    const captureState = who === 'player2' ? STATE.PLAYER2_CAPTURE : STATE.PLAYER_CAPTURE;

                    if (g.currentState === captureState) {
                        this.currentView = VIEW_TABLE;
                    } else if (g.currentState === STATE.CAPTURE_ANIM) {
                        if (g.animData && g.animData.captured) {
                            this.tracker.markMultipleSeen(g.animData.captured);
                        }
                        this._initCaptureAnim(g._afterPlayWho || (who === 'player2' ? 'computer' : 'player'));
                    } else {
                        if (g.animData && g.animData.captured) {
                            this.tracker.markMultipleSeen(g.animData.captured);
                        }
                        this._handlePostPlay();
                    }
                }
                break;
        }
    }

    _handleCaptureChoiceInput(key, who) {
        const g = this.game;

        switch (key) {
            case 'ArrowLeft':
            case 'ArrowUp':
                g.selectedCaptureIndex = Math.max(0, g.selectedCaptureIndex - 1);
                this.needsRedraw = true;
                break;

            case 'ArrowRight':
            case 'ArrowDown':
                g.selectedCaptureIndex = Math.min(g.captureOptions.length - 1, g.selectedCaptureIndex + 1);
                this.needsRedraw = true;
                break;

            case ' ':
            case 'Enter':
                {
                    const captureSet = g.captureOptions[g.selectedCaptureIndex];
                    this.tracker.markMultipleSeen(captureSet);

                    if (who === 'player2') {
                        g.player2SelectCapture(g.selectedCaptureIndex);
                    } else {
                        g.playerSelectCapture(g.selectedCaptureIndex);
                    }
                    this.needsRedraw = true;

                    if (g.currentState === STATE.CAPTURE_ANIM) {
                        this._initCaptureAnim(g._afterPlayWho || (who === 'player2' ? 'computer' : 'player'));
                    } else {
                        this._handlePostPlay();
                    }
                }
                break;
        }
    }

    // ================================================================
    // Rendering
    // ================================================================

    render(gfx) {
        if (!this.needsRedraw) return;
        this.needsRedraw = false;

        const g = this.game;

        // Update border colour for current state
        this._updateBorder();

        // Handover screen is a full black overlay
        if (g.currentState === STATE.HANDOVER) {
            this._drawHandover(gfx);
            return;
        }

        // Clear screen
        gfx.ink(C.WHITE);
        gfx.paper(C.BLACK);
        gfx.bright(false);
        gfx.cls();

        // === Row 0: Score header ===
        this._drawScoreHeader(gfx);

        // === Row 1: View label ===
        this._drawViewLabel(gfx);

        // === Rows 2-17: Card display area ===
        if (g.currentState === STATE.DEAL_ANIM) {
            this._drawDealAnim(gfx);
        } else if (g.currentState === STATE.CAPTURE_ANIM && this.captureAnim) {
            this._drawCaptureAnim(gfx);
        } else if (this.currentView === VIEW_HAND) {
            this._drawPlayerHand(gfx);
        } else {
            this._drawTableCards(gfx);
        }

        // === Row 18: Card info / cursor ===
        this._drawCardInfo(gfx);

        // === Rows 19-21: Messages / capture choice ===
        this._drawMessages(gfx);

        // === Row 22: Nav hints ===
        this._drawNavHints(gfx);

        // === Row 23: Status ===
        this._drawStatus(gfx);

        // Handle special overlay states
        if (g.currentState === STATE.HAND_END) {
            this._drawScoreBreakdown(gfx);
        } else if (g.currentState === STATE.GAME_OVER) {
            this._drawGameOver(gfx);
        } else if (g.currentState === STATE.SWEEP_ANIM) {
            this._drawScopaOverlay(gfx);
        }
    }

    _drawHandover(gfx) {
        const g = this.game;

        gfx.ink(C.WHITE);
        gfx.paper(C.BLACK);
        gfx.bright(false);
        gfx.cls();

        gfx.ink(C.RED);
        gfx.bright(false);
        gfx.printAtStr(6, 0, '================================');

        const playerName = g.currentPlayer === 'player' ? 'PLAYER 1' : 'PLAYER 2';
        const colour = g.currentPlayer === 'player' ? C.BLUE : C.RED;

        gfx.ink(colour);
        gfx.bright(true);
        const label = `${playerName}'s TURN`;
        const col = Math.floor((32 - label.length) / 2);
        gfx.printAtStr(9, col, label);

        gfx.ink(C.WHITE);
        gfx.bright(false);
        gfx.printAtStr(12, 3, 'Press Space when ready');

        gfx.ink(C.RED);
        gfx.bright(false);
        gfx.printAtStr(15, 0, '================================');

        // Show match score if applicable
        if (this.matchState) {
            gfx.ink(C.YELLOW);
            gfx.bright(false);
            gfx.printAtStr(17, 5, `Match: P1 ${this.matchState.playerWins} - ${this.matchState.computerWins} P2`);
        }
    }

    _drawScoreHeader(gfx) {
        const g = this.game;

        if (this._is2P()) {
            gfx.ink(C.BLUE);
            gfx.bright(true);
            const p1Score = String(g.playerTotalScore).padStart(2);
            gfx.printAtStr(0, 0, `P1:${p1Score}`);
            gfx.ink(C.RED);
            const p2Score = String(g.computerTotalScore).padStart(2);
            gfx.printAtStr(0, 7, `P2:${p2Score}`);
        } else {
            gfx.ink(C.YELLOW);
            gfx.bright(true);
            const pScore = String(g.playerTotalScore).padStart(2);
            gfx.printAtStr(0, 0, `You:${pScore}`);
            gfx.ink(C.CYAN);
            const cScore = String(g.computerTotalScore).padStart(2);
            gfx.printAtStr(0, 8, `CPU:${cScore}`);
        }

        gfx.ink(C.WHITE);
        gfx.bright(false);
        const deckLeft = String(g.deck.length).padStart(2);
        gfx.printAtStr(0, 15, `Dk:${deckLeft}`);
        gfx.ink(C.GREEN);
        gfx.printAtStr(0, 22, `T:${g.tableCards.length}`);

        if (this._is2P()) {
            // Show current player's hand count
            const isP2Turn = g.currentState === STATE.PLAYER2_TURN || g.currentState === STATE.PLAYER2_CAPTURE;
            const handCount = isP2Turn ? g.computerHand.length : g.playerHand.length;
            gfx.printAtStr(0, 27, `H:${handCount}`);
        } else {
            const cpuCards = g.computerHand.length;
            const pCards = g.playerHand.length;
            gfx.printAtStr(0, 22, `H:${pCards} T:${g.tableCards.length} C:${cpuCards}`);
        }
    }

    _drawViewLabel(gfx) {
        const g = this.game;
        gfx.paper(C.BLACK);
        gfx.bright(true);

        if (g.currentState === STATE.DEAL_ANIM || g.currentState === STATE.DEALING) {
            gfx.ink(C.YELLOW);
            gfx.printAtStr(1, 7, '=== DEALING ===');
        } else if (g.currentState === STATE.PLAYER2_TURN || g.currentState === STATE.PLAYER2_CAPTURE) {
            if (this.currentView === VIEW_HAND) {
                gfx.ink(C.RED);
                gfx.printAtStr(1, 5, '=== P2 HAND ===');
            } else {
                gfx.ink(C.CYAN);
                gfx.printAtStr(1, 8, '=== TABLE ===');
            }
        } else if (this.currentView === VIEW_HAND) {
            gfx.ink(C.GREEN);
            if (this._is2P()) {
                gfx.printAtStr(1, 5, '=== P1 HAND ===');
            } else {
                gfx.printAtStr(1, 6, '=== YOUR HAND ===');
            }
        } else {
            gfx.ink(C.CYAN);
            gfx.printAtStr(1, 8, '=== TABLE ===');
        }
    }

    _drawPlayerHand(gfx) {
        const g = this.game;
        const isP2 = g.currentState === STATE.PLAYER2_TURN || g.currentState === STATE.PLAYER2_CAPTURE;
        const cards = isP2 ? g.computerHand : g.playerHand;

        if (cards.length === 0) {
            gfx.ink(C.WHITE);
            gfx.paper(C.BLACK);
            gfx.bright(false);
            gfx.printAtStr(9, 10, 'Hand empty');
            return;
        }

        const positions = this._handCardPositions(cards.length);

        for (let i = 0; i < cards.length; i++) {
            const sprite = getCardSprite(cards[i].suit, cards[i].value);
            const col = positions[i];
            this._drawCardAt(col, CARD_START_ROW, sprite);
        }
    }

    _handCardPositions(count) {
        if (count === 3) return CARD_POSITIONS_3;
        if (count === 2) return [6, 17];
        if (count === 1) return [11];
        return CARD_POSITIONS_3.slice(0, count);
    }

    _drawTableCards(gfx) {
        const g = this.game;
        const cards = g.tableCards;

        if (cards.length === 0) {
            gfx.ink(C.WHITE);
            gfx.paper(C.BLACK);
            gfx.bright(false);
            gfx.printAtStr(9, 10, 'Table empty');
            return;
        }

        const positions = this._tableCardPositions(cards.length);

        for (let i = 0; i < cards.length; i++) {
            const sprite = getCardSprite(cards[i].suit, cards[i].value);
            const col = positions[i];

            if (i < cards.length - 1) {
                const nextCol = positions[i + 1];
                const visibleCols = Math.min(CARD_COLS, nextCol - col);
                if (visibleCols < CARD_COLS) {
                    this._drawCardPartial(col, CARD_START_ROW, sprite, visibleCols);
                } else {
                    this._drawCardAt(col, CARD_START_ROW, sprite);
                }
            } else {
                this._drawCardAt(col, CARD_START_ROW, sprite);
            }
        }
    }

    _tableCardPositions(count) {
        if (count === 1) return [11];
        if (count === 2) return [6, 17];
        if (count === 3) return CARD_POSITIONS_3;
        const lastStart = 32 - CARD_COLS;
        const step = Math.min(CARD_COLS, Math.floor(lastStart / (count - 1)));
        return Array.from({ length: count }, (_, i) =>
            i < count - 1 ? i * step : lastStart);
    }

    _drawCardInfo(gfx) {
        const g = this.game;
        gfx.ink(C.WHITE);
        gfx.paper(C.BLACK);
        gfx.bright(false);

        const isPlayerTurn = g.currentState === STATE.PLAYER_TURN || g.currentState === STATE.PLAYER2_TURN;
        const isP2 = g.currentState === STATE.PLAYER2_TURN || g.currentState === STATE.PLAYER2_CAPTURE;
        const hand = isP2 ? g.computerHand : g.playerHand;

        if (this.currentView === VIEW_HAND && isPlayerTurn) {
            if (hand.length > 0) {
                const positions = this._handCardPositions(hand.length);
                const sel = g.selectedCardIndex;
                const col = positions[sel];

                const card = hand[sel];
                const name = `${VALUE_NAMES[card.value]} di ${SUIT_NAMES[card.suit]}`;
                const cursorEnd = col + CARD_COLS;
                let nameCol;
                if (cursorEnd + 1 + name.length <= 32) {
                    nameCol = cursorEnd + 1;
                } else if (col - 1 - name.length >= 0) {
                    nameCol = col - 1 - name.length;
                } else {
                    nameCol = Math.max(0, Math.floor((32 - name.length) / 2));
                    gfx.ink(C.YELLOW);
                    gfx.bright(true);
                    gfx.printAtStr(CARD_INFO_ROW + 1, nameCol, name);
                    nameCol = -1;
                }

                gfx.ink(C.WHITE);
                gfx.bright(true);
                gfx.flash(true);
                const cursor = '^'.repeat(CARD_COLS);
                gfx.printAtStr(CARD_INFO_ROW, col, cursor);
                gfx.flash(false);

                if (nameCol >= 0) {
                    gfx.ink(C.YELLOW);
                    gfx.bright(true);
                    gfx.printAtStr(CARD_INFO_ROW, nameCol, name);
                }
            }
        } else if (this.currentView === VIEW_TABLE &&
                   g.currentState !== STATE.DEAL_ANIM &&
                   g.currentState !== STATE.CAPTURE_ANIM) {
            const count = g.tableCards.length;
            const info = count === 0 ? 'Table empty' :
                         count === 1 ? '1 card on table' :
                         `${count} cards on table`;
            const infoCol = Math.floor((32 - info.length) / 2);
            gfx.ink(C.CYAN);
            gfx.bright(false);
            gfx.printAtStr(CARD_INFO_ROW, infoCol, info);
        }
    }

    _drawMessages(gfx) {
        const g = this.game;

        if (g.currentState === STATE.PLAYER_CAPTURE || g.currentState === STATE.PLAYER2_CAPTURE) {
            gfx.ink(C.WHITE);
            gfx.paper(C.BLACK);
            gfx.bright(true);
            gfx.printAtStr(MESSAGE_ROW, 0, 'Choose capture:             ');

            for (let i = 0; i < g.captureOptions.length && i < 2; i++) {
                const opt = g.captureOptions[i];
                const desc = opt.map(c => VALUE_NAMES[c.value]).join('+');
                const isSelected = i === g.selectedCaptureIndex;

                if (isSelected) {
                    gfx.ink(C.YELLOW);
                    gfx.bright(true);
                } else {
                    gfx.ink(C.WHITE);
                    gfx.bright(false);
                }

                const label = (isSelected ? '> ' : '  ') + desc;
                gfx.printAtStr(MESSAGE_ROW + 1 + i, 1, label.padEnd(30).substring(0, 30));
            }
            return;
        }

        if (g.message && g.currentState !== STATE.PLAYER_TURN && g.currentState !== STATE.PLAYER2_TURN) {
            gfx.ink(C.YELLOW);
            gfx.paper(C.BLACK);
            gfx.bright(true);
            const padded = g.message.substring(0, 30);
            const col = Math.floor((32 - padded.length) / 2);
            gfx.printAtStr(MESSAGE_ROW, col, padded);
        }
    }

    _drawNavHints(gfx) {
        const g = this.game;
        if (g.currentState !== STATE.PLAYER_TURN &&
            g.currentState !== STATE.PLAYER_CAPTURE &&
            g.currentState !== STATE.PLAYER2_TURN &&
            g.currentState !== STATE.PLAYER2_CAPTURE) return;

        gfx.ink(C.WHITE);
        gfx.paper(C.BLACK);
        gfx.bright(false);

        const isP2 = g.currentState === STATE.PLAYER2_TURN || g.currentState === STATE.PLAYER2_CAPTURE;
        const captures = isP2 ? g.computerCaptures : g.playerCaptures;

        if (this.currentView === VIEW_HAND) {
            gfx.printAtStr(NAV_ROW, 2, 'Up:View Table');
            gfx.printAtStr(NAV_ROW, 20, `Capt:${String(captures.length).padStart(2)}`);
        } else {
            gfx.printAtStr(NAV_ROW, 2, 'Down:View Hand');
            gfx.printAtStr(NAV_ROW, 20, `Capt:${String(captures.length).padStart(2)}`);
        }
    }

    _drawStatus(gfx) {
        const g = this.game;
        gfx.ink(C.GREEN);
        gfx.paper(C.BLACK);
        gfx.bright(false);

        switch (g.currentState) {
            case STATE.PLAYER_TURN:
            case STATE.PLAYER2_TURN: {
                const muteStr = (this.beeper && this.beeper.muted) ? '[MUTE]' : '';
                if (this.currentView === VIEW_HAND) {
                    gfx.printAtStr(STATUS_ROW, 0, `L/R:Sel Spc:Play M:Snd${muteStr}`);
                } else {
                    gfx.printAtStr(STATUS_ROW, 0, `Down:Hand  1-3:Quick select   `);
                }
                break;
            }
            case STATE.PLAYER_CAPTURE:
            case STATE.PLAYER2_CAPTURE:
                gfx.printAtStr(STATUS_ROW, 0, 'L/R:Choose  Space:Confirm    ');
                break;
            case STATE.AI_TURN:
                gfx.printAtStr(STATUS_ROW, 0, 'Computer is thinking...     ');
                break;
            case STATE.DEAL_ANIM:
            case STATE.DEALING:
                gfx.printAtStr(STATUS_ROW, 0, 'Dealing cards...            ');
                break;
            case STATE.SWEEP_ANIM:
                gfx.ink(C.YELLOW);
                gfx.bright(true);
                gfx.printAtStr(STATUS_ROW, 0, '*** S C O P A ! ***         ');
                break;
            case STATE.HAND_END:
                gfx.ink(C.YELLOW);
                gfx.bright(true);
                gfx.printAtStr(STATUS_ROW, 0, 'Hand complete! Check scores');
                break;
            case STATE.ROUND_END:
                gfx.printAtStr(STATUS_ROW, 0, 'Dealing more cards...       ');
                break;
            case STATE.HANDOVER:
                gfx.printAtStr(STATUS_ROW, 0, '                            ');
                break;
            default:
                gfx.printAtStr(STATUS_ROW, 0, '                            ');
        }
    }

    _drawScopaOverlay(gfx) {
        const g = this.game;
        const flashIdx = Math.floor(g.stateTimer / 100) % 2;
        const msgColour = flashIdx === 0 ? C.YELLOW : C.WHITE;
        gfx.ink(msgColour);
        gfx.paper(C.BLACK);
        gfx.bright(true);

        let who;
        if (this._is2P()) {
            who = g.message.startsWith('Player 2') ? 'Player 2' : 'Player 1';
        } else {
            who = g.message.startsWith('Computer') ? 'Computer' : 'Player';
        }
        gfx.printAtStr(MESSAGE_ROW, 5, `*** S C O P A ! ***`);
        gfx.printAtStr(MESSAGE_ROW + 1, 8, who + ' sweeps!');
        this.needsRedraw = true;
    }

    _drawScoreBreakdown(gfx) {
        const g = this.game;
        const result = g.lastScoreBreakdown;
        if (!result) return;

        gfx.ink(C.WHITE);
        gfx.paper(C.BLUE);
        gfx.bright(true);

        for (let r = 2; r <= 21; r++) {
            gfx.printAtStr(r, 1, '                              ');
        }

        gfx.ink(C.YELLOW);
        gfx.paper(C.BLUE);
        gfx.bright(true);
        gfx.printAtStr(2, 6, `HAND ${g.handNumber} SCORE`);

        gfx.ink(C.WHITE);
        gfx.printAtStr(3, 2, '----------------------------');

        gfx.ink(C.WHITE);
        gfx.bright(true);
        const p1Label = this._is2P() ? ' P1' : 'You';
        const p2Label = this._is2P() ? '  P2' : ' CPU';
        gfx.printAtStr(5, 3, `Category    ${p1Label}${p2Label}`);

        let row = 7;
        for (const item of result.breakdown) {
            const pStr = String(item.player).padStart(4);
            const cStr = String(item.computer).padStart(4);
            let marker = '  ';
            if (item.winner === 'player') marker = '<-';
            else if (item.winner === 'computer') marker = '->';

            gfx.ink(item.winner === 'player' ? C.GREEN :
                    item.winner === 'computer' ? C.RED : C.WHITE);
            gfx.paper(C.BLUE);
            gfx.bright(true);

            const cat = item.category.padEnd(10);
            gfx.printAtStr(row, 3, `${cat}${pStr}${cStr} ${marker}`);
            row++;
        }

        row++;
        gfx.ink(C.WHITE);
        gfx.paper(C.BLUE);
        gfx.printAtStr(row, 2, '----------------------------');

        row++;
        gfx.ink(C.YELLOW);
        gfx.paper(C.BLUE);
        gfx.bright(true);
        gfx.printAtStr(row, 3, `This hand:   +${result.player.total}   +${result.computer.total}`);
        row++;
        gfx.ink(C.WHITE);
        gfx.printAtStr(row, 3, `RUNNING:    ${String(g.playerTotalScore).padStart(3)}  ${String(g.computerTotalScore).padStart(3)}`);

        row += 2;
        gfx.ink(C.YELLOW);
        gfx.bright(true);
        if (g.isGameOver()) {
            gfx.printAtStr(row, 5, 'Space for final result');
        } else {
            gfx.printAtStr(row, 5, 'Space to continue');
        }
    }

    _drawGameOver(gfx) {
        const g = this.game;
        const winner = g.getWinner();

        gfx.ink(C.WHITE);
        gfx.paper(C.BLACK);
        gfx.bright(false);
        gfx.cls();

        gfx.ink(C.RED);
        gfx.bright(false);
        gfx.printAtStr(2, 0, '================================');

        if (this._is2P()) {
            // Two-player result
            if (winner === 'player') {
                gfx.ink(C.BLUE);
                gfx.bright(true);
                gfx.printAtStr(4, 5, '* PLAYER 1 WINS! *');
            } else if (winner === 'computer') {
                gfx.ink(C.RED);
                gfx.bright(true);
                gfx.printAtStr(4, 5, '* PLAYER 2 WINS! *');
            } else {
                gfx.ink(C.CYAN);
                gfx.bright(true);
                gfx.printAtStr(4, 7, "* IT'S A TIE! *");
            }
        } else {
            // vs CPU result
            if (winner === 'player') {
                gfx.ink(C.YELLOW);
                gfx.bright(true);
                gfx.printAtStr(4, 6, '* * YOU WIN! * *');
                gfx.ink(C.GREEN);
                gfx.bright(true);
                gfx.printAtStr(6, 6, 'Congratulations!');
            } else if (winner === 'computer') {
                gfx.ink(C.RED);
                gfx.bright(true);
                gfx.printAtStr(4, 5, '* COMPUTER WINS *');
                gfx.ink(C.WHITE);
                gfx.bright(false);
                gfx.printAtStr(6, 4, 'Better luck next time.');
            } else {
                gfx.ink(C.CYAN);
                gfx.bright(true);
                gfx.printAtStr(4, 7, "* IT'S A TIE! *");
            }
        }

        gfx.ink(C.RED);
        gfx.bright(false);
        gfx.printAtStr(8, 0, '================================');

        gfx.ink(C.WHITE);
        gfx.bright(true);
        gfx.printAtStr(10, 7, 'FINAL SCORE');

        const p1Label = this._is2P() ? 'Player 1:' : 'You:     ';
        const p2Label = this._is2P() ? 'Player 2:' : 'Computer:';

        gfx.ink(this._is2P() ? C.BLUE : C.YELLOW);
        gfx.bright(true);
        const pFinal = String(g.playerTotalScore).padStart(3);
        gfx.printAtStr(12, 6, `${p1Label}${pFinal}`);

        gfx.ink(this._is2P() ? C.RED : C.CYAN);
        const cFinal = String(g.computerTotalScore).padStart(3);
        gfx.printAtStr(13, 6, `${p2Label}${cFinal}`);

        gfx.ink(C.WHITE);
        gfx.bright(false);
        gfx.printAtStr(15, 4, `Hands played: ${g.handNumber}`);

        // Match info
        if (this.matchState) {
            gfx.ink(C.RED);
            gfx.bright(false);
            gfx.printAtStr(16, 0, '================================');

            gfx.ink(C.YELLOW);
            gfx.bright(true);
            const mp1 = this.matchState.playerWins;
            const mp2 = this.matchState.computerWins;
            const matchLabel = this._is2P()
                ? `Match: P1 ${mp1} - ${mp2} P2`
                : `Match: You ${mp1} - ${mp2} CPU`;
            const matchCol = Math.floor((32 - matchLabel.length) / 2);
            gfx.printAtStr(17, matchCol, matchLabel);

            if (this.matchState.isMatchOver()) {
                const mw = this.matchState.getMatchWinner();
                gfx.ink(C.GREEN);
                gfx.bright(true);
                let matchWinMsg;
                if (this._is2P()) {
                    matchWinMsg = mw === 'player' ? 'P1 wins the match!' : 'P2 wins the match!';
                } else {
                    matchWinMsg = mw === 'player' ? 'You win the match!' : 'CPU wins the match!';
                }
                const mwCol = Math.floor((32 - matchWinMsg.length) / 2);
                gfx.printAtStr(18, mwCol, matchWinMsg);
            }
        }

        gfx.ink(C.RED);
        gfx.bright(false);
        gfx.printAtStr(20, 0, '================================');

        gfx.ink(C.GREEN);
        gfx.bright(false);
        if (this.matchState && !this.matchState.isMatchOver()) {
            gfx.printAtStr(22, 3, 'Press Space for next game');
        } else {
            gfx.printAtStr(22, 3, 'Press Space for main menu');
        }
    }

    // ================================================================
    // Card drawing primitives
    // ================================================================

    _drawCardAt(col, row, sprite) {
        const fb = this.ctx.fb;
        const py = row * 8;
        let byteIdx = 0;

        for (let y = 0; y < CARD_H; y++) {
            for (let c = 0; c < CARD_COLS; c++) {
                if (col + c >= 0 && col + c < 32 && py + y < 192) {
                    fb.setByte(col + c, py + y, sprite.pixels[byteIdx]);
                }
                byteIdx++;
            }
        }

        let attrIdx = 0;
        for (let r = 0; r < CARD_ROWS; r++) {
            for (let c = 0; c < CARD_COLS; c++) {
                if (col + c >= 0 && col + c < 32 && row + r < 24) {
                    fb.setAttrByte(col + c, row + r, sprite.attrs[attrIdx]);
                }
                attrIdx++;
            }
        }
    }

    _drawCardPartial(col, row, sprite, visibleCols) {
        const fb = this.ctx.fb;
        const py = row * 8;

        for (let y = 0; y < CARD_H; y++) {
            for (let c = 0; c < visibleCols && c < CARD_COLS; c++) {
                if (col + c >= 0 && col + c < 32 && py + y < 192) {
                    fb.setByte(col + c, py + y, sprite.pixels[y * CARD_COLS + c]);
                }
            }
        }

        for (let r = 0; r < CARD_ROWS; r++) {
            for (let c = 0; c < visibleCols && c < CARD_COLS; c++) {
                if (col + c >= 0 && col + c < 32 && row + r < 24) {
                    fb.setAttrByte(col + c, row + r, sprite.attrs[r * CARD_COLS + c]);
                }
            }
        }
    }

    exit() {}
}
