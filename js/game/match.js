/**
 * Match state for best-of-N series.
 */

export class MatchState {
    constructor(targetWins = 2) {
        this.targetWins = targetWins;
        this.playerWins = 0;
        this.computerWins = 0;
        this.gamesPlayed = 0;
    }

    recordGame(winner) {
        this.gamesPlayed++;
        if (winner === 'player') this.playerWins++;
        else if (winner === 'computer') this.computerWins++;
    }

    isMatchOver() {
        return this.playerWins >= this.targetWins ||
               this.computerWins >= this.targetWins;
    }

    getMatchWinner() {
        if (this.playerWins > this.computerWins) return 'player';
        if (this.computerWins > this.playerWins) return 'computer';
        return 'tie';
    }

    reset() {
        this.playerWins = 0;
        this.computerWins = 0;
        this.gamesPlayed = 0;
    }
}
