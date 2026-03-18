/**
 * Tape loading sound generator.
 * Simulates the characteristic ZX Spectrum tape loading noise:
 * - Pilot tone: continuous ~807Hz square wave
 * - Sync pulse: brief transition
 * - Data blocks: alternating ~1kHz and ~2kHz pulses (0-bits and 1-bits)
 *
 * The Spectrum used two pulse widths:
 *   0-bit: 855 T-states per half-pulse ≈ 2046Hz
 *   1-bit: 1710 T-states per half-pulse ≈ 1023Hz
 *   Pilot: 2168 T-states per half-pulse ≈ 807Hz
 */
export class TapeSound {
    constructor(beeper) {
        this.beeper = beeper;
        this.sources = [];
    }

    /**
     * Generate and play the full tape loading sound sequence.
     * Returns the total duration in seconds.
     *
     * Timeline:
     *   0.0 - 2.0s  : Pilot tone (header)
     *   2.0 - 2.05s : Sync pulse
     *   2.05 - 3.5s : Header data block
     *   3.5 - 4.0s  : Silence
     *   4.0 - 5.0s  : Pilot tone (data)
     *   5.0 - 5.05s : Sync pulse
     *   5.05 - 12.0s: Main data block (screen data)
     */
    play() {
        if (!this.beeper.audioCtx) return 0;

        this.stop(); // Stop any previous playback

        // Phase 1: Header pilot tone (0 - 2s)
        this.sources.push(
            this.beeper.playTone(807, 2.0, 0)
        );

        // Phase 2: Header data block (2.05 - 3.5s)
        const headerBuf = this._generateDataBlock(1.45);
        this.sources.push(
            this.beeper.playBuffer(headerBuf, 2.05)
        );

        // Phase 3: Data pilot tone (4.0 - 5.0s)
        this.sources.push(
            this.beeper.playTone(807, 1.0, 4.0)
        );

        // Phase 4: Main data block (5.05 - 12.0s)
        const dataBuf = this._generateDataBlock(6.95);
        this.sources.push(
            this.beeper.playBuffer(dataBuf, 5.05)
        );

        return 12.0;
    }

    /**
     * Stop all tape playback sounds.
     */
    stop() {
        for (const source of this.sources) {
            try {
                if (source) source.stop();
            } catch (e) {
                // Already stopped
            }
        }
        this.sources = [];
    }

    /**
     * Generate a data block audio buffer.
     * Simulates the alternating 0-bit/1-bit pulse pattern that creates
     * the characteristic Spectrum loading screech.
     */
    _generateDataBlock(duration) {
        const sampleRate = this.beeper.sampleRate;
        const buffer = this.beeper.createBuffer(duration);
        const data = buffer.getChannelData(0);
        const totalSamples = data.length;

        // Use a simple PRNG for deterministic "data" pattern
        let seed = 42;
        const nextBit = () => {
            seed = (seed * 1103515245 + 12345) & 0x7fffffff;
            return (seed >> 16) & 1;
        };

        let sampleIdx = 0;
        let phase = 1; // Current square wave phase (+1 or -1)

        while (sampleIdx < totalSamples) {
            const bit = nextBit();

            // Samples per half-pulse period
            // 0-bit: higher frequency (shorter period) ≈ 2046Hz
            // 1-bit: lower frequency (longer period) ≈ 1023Hz
            const halfPeriodSamples = bit
                ? Math.floor(sampleRate / 1023 / 2)
                : Math.floor(sampleRate / 2046 / 2);

            // Write one full cycle (two half-periods)
            for (let half = 0; half < 2 && sampleIdx < totalSamples; half++) {
                for (let s = 0; s < halfPeriodSamples && sampleIdx < totalSamples; s++) {
                    data[sampleIdx++] = phase * 0.35;
                }
                phase = -phase;
            }
        }

        return buffer;
    }
}
