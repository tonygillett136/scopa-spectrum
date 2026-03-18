import * as C from '../spectrum/constants.js';
import { getCardSprite, getCardBack, CARD_COLS, CARD_ROWS, CARD_H } from '../data/cards.js';
import { SFX_MENU_MOVE, SFX_MENU_SELECT } from '../audio/sfx.js';
import { TITLE_MELODY, TITLE_MELODY_DURATION } from '../audio/music.js';

/**
 * Title / main menu screen.
 * Shows title art, large digitized cards as showcase, menu, and instructions.
 *
 * Layout with 10x16 cards:
 *   Row 0:     Decorative top border
 *   Row 1:     "S C O P A"
 *   Row 2:     "S P E C T R U M"
 *   Row 3:     Decorative line
 *   Rows 4-19: 3 large sample cards (16 rows = full card height)
 *   Row 20:    Menu line 1
 *   Row 21:    Menu line 2
 *   Row 22:    Flashing prompt / match toggle
 *   Row 23:    Copyright
 */

const VIEW_MENU = 0;
const VIEW_INSTRUCTIONS = 1;
const VIEW_STATS = 2;

export class TitleScreen {
    constructor(beeper, onStartGame, stats) {
        this.beeper = beeper;
        this.onStartGame = onStartGame;
        this.stats = stats;
        this.view = VIEW_MENU;
        this.flashTimer = 0;
        this.flashVisible = true;
        this.ctx = null;
        this.needsRedraw = true;
        this.musicTimer = 0;
        this.musicPlaying = false;
        this.bestOf3 = false;
    }

    _sfx(notes) {
        if (this.beeper) this.beeper.playSequence(notes);
    }

    _startMusic() {
        if (!this.beeper || !this.beeper.audioCtx) return;
        this.beeper.playSequence(TITLE_MELODY);
        this.musicPlaying = true;
        this.musicTimer = 0;
    }

    _stopMusic() {
        if (this.beeper) this.beeper.stopAll();
        this.musicPlaying = false;
    }

    enter(ctx) {
        this.ctx = ctx;
        this.view = VIEW_MENU;
        this.needsRedraw = true;
        this._startMusic();
    }

    update(dt) {
        this.flashTimer += dt;
        if (this.flashTimer >= 500) {
            this.flashTimer = 0;
            this.flashVisible = !this.flashVisible;
            this.needsRedraw = true;
        }

        // Loop the title music
        if (this.musicPlaying) {
            this.musicTimer += dt;
            if (this.musicTimer >= TITLE_MELODY_DURATION * 1000 + 200) {
                this._startMusic();
            }
        }
    }

    render(gfx) {
        if (!this.needsRedraw) return;
        this.needsRedraw = false;

        if (this.view === VIEW_MENU) {
            this._renderMenu(gfx);
        } else if (this.view === VIEW_INSTRUCTIONS) {
            this._renderInstructions(gfx);
        } else if (this.view === VIEW_STATS) {
            this._renderStats(gfx);
        }
    }

    _renderMenu(gfx) {
        const { border, fb } = this.ctx;

        border.setColour(C.BLACK);
        gfx.ink(C.WHITE);
        gfx.paper(C.BLACK);
        gfx.bright(false);
        gfx.cls();

        // === Row 0: Decorative top border ===
        gfx.ink(C.RED);
        gfx.paper(C.BLACK);
        gfx.bright(false);
        gfx.printAtStr(0, 0, '================================');

        // === Title: large centred ===
        gfx.ink(C.YELLOW);
        gfx.bright(true);
        gfx.printAtStr(1, 5, 'S C O P A');
        gfx.ink(C.CYAN);
        gfx.bright(true);
        gfx.printAtStr(2, 5, 'S P E C T R U M');

        // === Decorative line ===
        gfx.ink(C.RED);
        gfx.bright(false);
        gfx.printAtStr(3, 0, '================================');

        // === Display three sample cards (showcase of digitized art) ===
        const sampleCards = [
            { suit: 0, value: 1 },  // Asso di Coppe
            { suit: 1, value: 7 },  // Settebello
            { suit: 3, value: 10 }, // Re di Spade
        ];

        const positions = [0, 11, 22];
        for (let i = 0; i < 3; i++) {
            const sprite = getCardSprite(sampleCards[i].suit, sampleCards[i].value);
            this._drawCardAt(positions[i], 4, sprite, fb);
        }

        // === Menu options ===
        gfx.ink(C.GREEN);
        gfx.bright(true);
        gfx.printAtStr(20, 1, '1:Easy 2:Med 3:Hard');
        gfx.ink(C.CYAN);
        gfx.printAtStr(20, 21, '4:2Player');

        gfx.ink(C.WHITE);
        gfx.bright(true);
        gfx.printAtStr(21, 1, '5:Stats  I:Info');
        gfx.ink(C.MAGENTA);
        gfx.bright(true);
        const bo3Label = this.bestOf3 ? 'B:Bo3 ON ' : 'B:Bo3 OFF';
        gfx.printAtStr(21, 21, bo3Label);

        // Flashing prompt
        if (this.flashVisible) {
            gfx.ink(C.YELLOW);
            gfx.bright(true);
            gfx.printAtStr(22, 5, 'Press 1-3 to start game');
        } else {
            gfx.ink(C.BLACK);
            gfx.paper(C.BLACK);
            gfx.printAtStr(22, 5, '                       ');
        }

        gfx.ink(C.WHITE);
        gfx.bright(false);
        gfx.printAtStr(23, 5, '(c) 2026 Tony Gillett');
    }

    _renderInstructions(gfx) {
        const { border } = this.ctx;

        border.setColour(C.BLACK);
        gfx.ink(C.WHITE);
        gfx.paper(C.BLACK);
        gfx.bright(false);
        gfx.cls();

        gfx.ink(C.YELLOW);
        gfx.bright(true);
        gfx.printAtStr(0, 8, 'HOW TO PLAY');

        gfx.ink(C.RED);
        gfx.bright(false);
        gfx.printAtStr(1, 0, '================================');

        gfx.ink(C.CYAN);
        gfx.bright(true);
        gfx.printAtStr(3, 0, 'GOAL:');
        gfx.ink(C.WHITE);
        gfx.bright(false);
        gfx.printAtStr(3, 6, 'Score 11 points first.');

        gfx.ink(C.CYAN);
        gfx.bright(true);
        gfx.printAtStr(5, 0, 'PLAY:');
        gfx.ink(C.WHITE);
        gfx.bright(false);
        gfx.printAtStr(5, 6, 'Select a card and play');
        gfx.printAtStr(6, 0, 'it. Capture table cards whose');
        gfx.printAtStr(7, 0, 'values match or add up to your');
        gfx.printAtStr(8, 0, 'card. If no capture, your card');
        gfx.printAtStr(9, 0, 'is added to the table.');

        gfx.ink(C.CYAN);
        gfx.bright(true);
        gfx.printAtStr(11, 0, 'SCORING:');
        gfx.ink(C.GREEN);
        gfx.bright(false);
        gfx.printAtStr(12, 1, 'Carte    - Most cards    (1pt)');
        gfx.printAtStr(13, 1, 'Denari   - Most coins    (1pt)');
        gfx.printAtStr(14, 1, 'Sette B. - 7 of Denari   (1pt)');
        gfx.printAtStr(15, 1, 'Primiera - Best 7s/6s/As (1pt)');
        gfx.printAtStr(16, 1, 'Scopa    - Clear table   (1pt)');

        gfx.ink(C.CYAN);
        gfx.bright(true);
        gfx.printAtStr(18, 0, 'CONTROLS:');
        gfx.ink(C.WHITE);
        gfx.bright(false);
        gfx.printAtStr(19, 1, 'Left/Right - Select card');
        gfx.printAtStr(20, 1, 'Up/Down    - Hand/Table view');
        gfx.printAtStr(21, 1, 'Space/Enter - Play card');

        if (this.flashVisible) {
            gfx.ink(C.YELLOW);
            gfx.bright(true);
            gfx.printAtStr(23, 4, 'Press any key to go back');
        } else {
            gfx.ink(C.BLACK);
            gfx.paper(C.BLACK);
            gfx.printAtStr(23, 4, '                        ');
        }
    }

    _renderStats(gfx) {
        const { border } = this.ctx;
        const s = this.stats;

        border.setColour(C.BLACK);
        gfx.ink(C.WHITE);
        gfx.paper(C.BLACK);
        gfx.bright(false);
        gfx.cls();

        gfx.ink(C.YELLOW);
        gfx.bright(true);
        gfx.printAtStr(0, 9, 'STATISTICS');

        gfx.ink(C.RED);
        gfx.bright(false);
        gfx.printAtStr(1, 0, '================================');

        if (!s) {
            gfx.ink(C.WHITE);
            gfx.bright(false);
            gfx.printAtStr(10, 6, 'No stats available.');
        } else {
            gfx.ink(C.CYAN);
            gfx.bright(true);
            gfx.printAtStr(3, 1, 'OVERALL');
            gfx.ink(C.WHITE);
            gfx.bright(false);
            const winPct = s.gamesPlayed > 0 ? Math.round(s.gamesWon / s.gamesPlayed * 100) : 0;
            gfx.printAtStr(4, 1, `Games: ${s.gamesPlayed}  Won: ${s.gamesWon}  Lost: ${s.gamesLost}`);
            gfx.printAtStr(5, 1, `Tied: ${s.gamesTied}  Win rate: ${winPct}%`);
            gfx.printAtStr(6, 1, `Streak: ${s.currentWinStreak} (Best: ${s.bestWinStreak})`);

            gfx.ink(C.RED);
            gfx.bright(false);
            gfx.printAtStr(7, 0, '================================');

            gfx.ink(C.CYAN);
            gfx.bright(true);
            gfx.printAtStr(8, 1, 'ACHIEVEMENTS');
            gfx.ink(C.WHITE);
            gfx.bright(false);
            gfx.printAtStr(9, 1, `Hands played: ${s.handsPlayed}`);
            gfx.printAtStr(10, 1, `Scope scored: ${s.scopeScored}`);
            gfx.printAtStr(11, 1, `Settebello captured: ${s.settebelloCaptured}`);

            gfx.ink(C.RED);
            gfx.bright(false);
            gfx.printAtStr(12, 0, '================================');

            gfx.ink(C.CYAN);
            gfx.bright(true);
            gfx.printAtStr(13, 1, 'BY DIFFICULTY');
            gfx.ink(C.GREEN);
            gfx.bright(false);
            gfx.printAtStr(14, 1, `Easy:   ${s.easyWins}/${s.easyPlayed} wins`);
            gfx.ink(C.YELLOW);
            gfx.bright(false);
            gfx.printAtStr(15, 1, `Medium: ${s.mediumWins}/${s.mediumPlayed} wins`);
            gfx.ink(C.RED);
            gfx.bright(false);
            gfx.printAtStr(16, 1, `Hard:   ${s.hardWins}/${s.hardPlayed} wins`);
            gfx.ink(C.CYAN);
            gfx.bright(false);
            gfx.printAtStr(17, 1, `2P Games: ${s.twoPlayerGames}`);

            gfx.ink(C.RED);
            gfx.bright(false);
            gfx.printAtStr(19, 0, '================================');

            gfx.ink(C.MAGENTA);
            gfx.bright(false);
            gfx.printAtStr(21, 3, 'R:Reset stats');
        }

        if (this.flashVisible) {
            gfx.ink(C.YELLOW);
            gfx.bright(true);
            gfx.printAtStr(23, 4, 'Press any key to go back');
        } else {
            gfx.ink(C.BLACK);
            gfx.paper(C.BLACK);
            gfx.printAtStr(23, 4, '                        ');
        }
    }

    /**
     * Draw a card sprite at character cell position.
     */
    _drawCardAt(col, row, sprite, fb) {
        const py = row * 8;
        let byteIdx = 0;
        for (let y = 0; y < CARD_H; y++) {
            for (let c = 0; c < CARD_COLS; c++) {
                if (col + c < 32 && py + y < 192) {
                    fb.setByte(col + c, py + y, sprite.pixels[byteIdx]);
                }
                byteIdx++;
            }
        }

        let attrIdx = 0;
        for (let r = 0; r < CARD_ROWS; r++) {
            for (let c = 0; c < CARD_COLS; c++) {
                if (col + c < 32 && row + r < 24) {
                    fb.setAttrByte(col + c, row + r, sprite.attrs[attrIdx]);
                }
                attrIdx++;
            }
        }
    }

    handleInput(key) {
        // Stats view
        if (this.view === VIEW_STATS) {
            if (key === 'r' || key === 'R') {
                if (this.stats) {
                    this.stats.resetAll();
                    this._sfx(SFX_MENU_SELECT);
                    this.needsRedraw = true;
                }
                return;
            }
            this._sfx(SFX_MENU_MOVE);
            this.view = VIEW_MENU;
            this.needsRedraw = true;
            return;
        }

        // Instructions view
        if (this.view === VIEW_INSTRUCTIONS) {
            this._sfx(SFX_MENU_MOVE);
            this.view = VIEW_MENU;
            this.needsRedraw = true;
            return;
        }

        // Menu view
        const matchType = this.bestOf3 ? 'bo3' : 'single';

        switch (key) {
            case '1':
                this._sfx(SFX_MENU_SELECT);
                if (this.onStartGame) this.onStartGame({ difficulty: 'easy', mode: 'vs_cpu', matchType });
                break;
            case '2':
                this._sfx(SFX_MENU_SELECT);
                if (this.onStartGame) this.onStartGame({ difficulty: 'medium', mode: 'vs_cpu', matchType });
                break;
            case '3':
                this._sfx(SFX_MENU_SELECT);
                if (this.onStartGame) this.onStartGame({ difficulty: 'hard', mode: 'vs_cpu', matchType });
                break;
            case '4':
                this._sfx(SFX_MENU_SELECT);
                if (this.onStartGame) this.onStartGame({ difficulty: 'medium', mode: 'vs_human', matchType });
                break;
            case '5':
            case 's':
            case 'S':
                this._sfx(SFX_MENU_MOVE);
                this.view = VIEW_STATS;
                this.needsRedraw = true;
                break;
            case 'i':
            case 'I':
                this._sfx(SFX_MENU_MOVE);
                this.view = VIEW_INSTRUCTIONS;
                this.needsRedraw = true;
                break;
            case 'b':
            case 'B':
                this._sfx(SFX_MENU_MOVE);
                this.bestOf3 = !this.bestOf3;
                this.needsRedraw = true;
                break;
            case ' ':
            case 'Enter':
                // Default: start medium game
                this._sfx(SFX_MENU_SELECT);
                if (this.onStartGame) this.onStartGame({ difficulty: 'medium', mode: 'vs_cpu', matchType });
                break;
        }
    }

    exit() {
        this._stopMusic();
    }
}
