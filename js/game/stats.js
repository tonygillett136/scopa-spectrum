/**
 * Game statistics — persisted via localStorage.
 */

export class Statistics {
    constructor() {
        this._load();
    }

    _load() {
        try {
            const data = localStorage.getItem('scopa_stats');
            if (data) {
                Object.assign(this, this._defaults(), JSON.parse(data));
                return;
            }
        } catch (e) { /* ignore */ }
        Object.assign(this, this._defaults());
    }

    _defaults() {
        return {
            gamesPlayed: 0,
            gamesWon: 0,
            gamesLost: 0,
            gamesTied: 0,
            handsPlayed: 0,
            scopeScored: 0,
            settebelloCaptured: 0,
            bestWinStreak: 0,
            currentWinStreak: 0,
            easyWins: 0,
            easyPlayed: 0,
            mediumWins: 0,
            mediumPlayed: 0,
            hardWins: 0,
            hardPlayed: 0,
            twoPlayerGames: 0,
        };
    }

    save() {
        try {
            const data = {};
            for (const key of Object.keys(this._defaults())) {
                data[key] = this[key];
            }
            localStorage.setItem('scopa_stats', JSON.stringify(data));
        } catch (e) { /* ignore */ }
    }

    recordGame(winner, difficulty, mode) {
        this.gamesPlayed++;

        if (mode === 'vs_human') {
            this.twoPlayerGames++;
        } else {
            if (difficulty === 'easy') {
                this.easyPlayed++;
                if (winner === 'player') this.easyWins++;
            } else if (difficulty === 'medium') {
                this.mediumPlayed++;
                if (winner === 'player') this.mediumWins++;
            } else if (difficulty === 'hard') {
                this.hardPlayed++;
                if (winner === 'player') this.hardWins++;
            }
        }

        if (winner === 'player') {
            this.gamesWon++;
            this.currentWinStreak++;
            if (this.currentWinStreak > this.bestWinStreak) {
                this.bestWinStreak = this.currentWinStreak;
            }
        } else if (winner === 'computer') {
            this.gamesLost++;
            this.currentWinStreak = 0;
        } else {
            this.gamesTied++;
        }

        this.save();
    }

    recordHand(playerSweeps, computerSweeps, playerCapturedSettebello) {
        this.handsPlayed++;
        this.scopeScored += playerSweeps;
        if (playerCapturedSettebello) {
            this.settebelloCaptured++;
        }
        this.save();
    }

    resetAll() {
        Object.assign(this, this._defaults());
        this.save();
    }
}
