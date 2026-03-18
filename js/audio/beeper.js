/**
 * ZX Spectrum beeper emulation via Web Audio API.
 * The Spectrum had a 1-bit speaker that could only produce square waves.
 * All sounds are built from square wave tones at various frequencies.
 */
export class Beeper {
    constructor() {
        this.audioCtx = null;
        this.masterGain = null;
        this.muted = false;
    }

    /**
     * Initialise the AudioContext. Must be called from a user interaction
     * (click/keypress) to satisfy browser autoplay policies.
     */
    init() {
        if (this.audioCtx) return;
        this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        this.masterGain = this.audioCtx.createGain();
        this.masterGain.gain.value = 0.25;
        this.masterGain.connect(this.audioCtx.destination);
    }

    /**
     * Ensure audio context is running (resume if suspended).
     */
    resume() {
        if (this.audioCtx && this.audioCtx.state === 'suspended') {
            this.audioCtx.resume();
        }
    }

    toggleMute() {
        this.muted = !this.muted;
        if (this.masterGain) {
            this.masterGain.gain.value = this.muted ? 0 : 0.25;
        }
        return this.muted;
    }

    /**
     * Play a square wave tone at the given frequency for the given duration.
     * Returns the oscillator node (for stopping early if needed).
     */
    playTone(frequency, duration, startDelay = 0) {
        if (!this.audioCtx) return null;

        const osc = this.audioCtx.createOscillator();
        osc.type = 'square';
        osc.frequency.value = frequency;

        const gain = this.audioCtx.createGain();
        gain.gain.value = 0.3;
        // Quick fade-out to prevent clicks
        const t = this.audioCtx.currentTime + startDelay;
        gain.gain.setValueAtTime(0.3, t);
        gain.gain.setValueAtTime(0.3, t + duration - 0.005);
        gain.gain.linearRampToValueAtTime(0, t + duration);

        osc.connect(gain);
        gain.connect(this.masterGain);

        osc.start(t);
        osc.stop(t + duration + 0.01);

        return osc;
    }

    /**
     * Play a sequence of [frequency, duration] pairs.
     * frequency of 0 = silence (rest).
     * Returns total duration in seconds.
     */
    playSequence(notes, startDelay = 0) {
        let time = startDelay;
        for (const [freq, dur] of notes) {
            if (freq > 0) {
                this.playTone(freq, dur, time);
            }
            time += dur;
        }
        return time - startDelay;
    }

    /**
     * Create a custom audio buffer and play it.
     * Used for complex sounds like tape loading noise.
     * Returns the source node.
     */
    playBuffer(buffer, startDelay = 0) {
        if (!this.audioCtx) return null;

        const source = this.audioCtx.createBufferSource();
        source.buffer = buffer;
        source.connect(this.masterGain);
        source.start(this.audioCtx.currentTime + startDelay);

        return source;
    }

    /**
     * Get the current audio context time.
     */
    get currentTime() {
        return this.audioCtx ? this.audioCtx.currentTime : 0;
    }

    get sampleRate() {
        return this.audioCtx ? this.audioCtx.sampleRate : 44100;
    }

    /**
     * Stop all currently playing sounds by disconnecting and
     * recreating the master gain node.
     */
    stopAll() {
        if (!this.audioCtx || !this.masterGain) return;
        this.masterGain.disconnect();
        this.masterGain = this.audioCtx.createGain();
        this.masterGain.gain.value = this.muted ? 0 : 0.25;
        this.masterGain.connect(this.audioCtx.destination);
    }

    /**
     * Create an empty AudioBuffer of the given duration.
     */
    createBuffer(duration) {
        if (!this.audioCtx) return null;
        const length = Math.floor(this.audioCtx.sampleRate * duration);
        return this.audioCtx.createBuffer(1, length, this.audioCtx.sampleRate);
    }
}
