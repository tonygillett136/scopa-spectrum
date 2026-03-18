import { Framebuffer } from './spectrum/framebuffer.js';
import { Renderer } from './spectrum/renderer.js';
import { Border } from './spectrum/border.js';
import { Gfx } from './spectrum/gfx.js';
import { CRT } from './spectrum/crt.js';
import { FLASH_INTERVAL_MS } from './spectrum/constants.js';
import * as C from './spectrum/constants.js';
import { LoadingScreen } from './screens/loading.js';
import { TitleScreen } from './screens/title.js';
import { GameplayScreen } from './screens/gameplay.js';
import { Statistics } from './game/stats.js';
import { MatchState } from './game/match.js';

// --- Initialisation ---

const canvas = document.getElementById('screen');
const fb = new Framebuffer();
const renderer = new Renderer(canvas, fb, 3);
const border = new Border(renderer);
const gfx = new Gfx(fb);
const crt = new CRT(canvas, 3);

// Persistent statistics
const stats = new Statistics();

// --- Game loop state ---
let lastTime = 0;
let flashTimer = 0;

// Shared context passed to all screens
const ctx = { fb, renderer, border, gfx };

// Export globals for other modules
export { fb, renderer, border, gfx };

// --- Screen manager ---
let currentScreen = null;

function setScreen(screen) {
    if (currentScreen && currentScreen.exit) {
        currentScreen.exit();
    }
    currentScreen = screen;
    if (currentScreen && currentScreen.enter) {
        currentScreen.enter(ctx);
    }
}

// --- Input ---
const keyState = {};

document.addEventListener('keydown', (e) => {
    keyState[e.key] = true;
    if (currentScreen && currentScreen.handleInput) {
        currentScreen.handleInput(e.key, e);
    }
});

document.addEventListener('keyup', (e) => {
    keyState[e.key] = false;
});

export function isKeyDown(key) {
    return !!keyState[key];
}

// --- Game loop ---

function gameLoop(timestamp) {
    if (!lastTime) lastTime = timestamp;
    const dt = timestamp - lastTime;
    lastTime = timestamp;

    // Flash timer (toggle every 320ms)
    flashTimer += dt;
    if (flashTimer >= FLASH_INTERVAL_MS) {
        flashTimer -= FLASH_INTERVAL_MS;
        renderer.toggleFlash();
    }

    // Update current screen
    if (currentScreen && currentScreen.update) {
        currentScreen.update(dt);
    }

    // Render current screen
    if (currentScreen && currentScreen.render) {
        currentScreen.render(gfx);
    }

    // Render the framebuffer to the offscreen source canvas
    renderer.renderFrame();

    // Apply CRT post-processing
    crt.applyEffects();

    requestAnimationFrame(gameLoop);
}

// --- Screen flow ---

let storedBeeper = null;

function showTitle(beeper) {
    if (beeper) storedBeeper = beeper;
    const title = new TitleScreen(storedBeeper, (options) => {
        startGame(options);
    }, stats);
    setScreen(title);
}

function startGame(options = {}) {
    const matchState = options.matchType === 'bo3' ? new MatchState(2) : null;
    const gameplay = new GameplayScreen(storedBeeper, {
        difficulty: options.difficulty || 'medium',
        mode: options.mode || 'vs_cpu',
        matchState,
        stats,
    }, () => {
        // Game over — return to title
        showTitle();
    });
    setScreen(gameplay);
}

function boot() {
    // Start with the loading screen
    const loading = new LoadingScreen((beeper) => {
        showTitle(beeper);
    });
    setScreen(loading);

    // Start the game loop
    requestAnimationFrame(gameLoop);
}

// Wait for DOM then boot
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
} else {
    boot();
}
