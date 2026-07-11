# The Card Game That Disappeared — and How We Brought It Back

### Rebuilding a lost ZX Spectrum game in Z80 machine code, with an AI as my coding partner

*Disponibile anche in italiano: [ARTICLE.it.md](ARTICLE.it.md).*

---

Years ago, a friend of mine — Angelo Colucci — wrote a version of the Italian card game *Scopa* for the Sinclair ZX Spectrum. What I remember most are the cards. He'd drawn them by hand, and on that little rubber-keyed machine from 1982 they looked wonderful: the knights and kings of the Neapolitan deck, rendered in defiant detail on a screen that gave you 256×192 pixels and, frankly, attitude.

Then, as these things do, the game slipped away. Tapes degrade. Boxes get lost in house moves. I searched every cassette I'd managed to save from childhood; friends in the Italian Spectrum community kindly circulated an appeal. Nothing. It was simply gone — a small, private piece of computing history, unbacked-up and unrecoverable.

I'd always wanted to bring it back. This summer I finally did, with an unlikely collaborator: an AI.

The first playable version came together in a single, giddy day. Making it *right* — making it something Angelo's original deserved — took another month. And that month, it turns out, is where the real story lives.

This is the story of how that worked, why it was harder than it sounds, and what it taught me about the strange new division of labour between a human who remembers a machine and a machine that has read everything ever written about it.

---

## Why this is genuinely difficult

If you've never written for a 1980s home computer, it's easy to assume that a modern AI would find it *trivial* — surely a four-decade-old 8-bit machine is a rounding error next to today's hardware?

It's the opposite. Modern programming is a story of abundance: gigabytes of memory, libraries for everything, a forgiving runtime that cleans up your mistakes. The Spectrum is a story of **scarcity and quirks**, and you have to respect every one of them:

- **48 kilobytes of RAM.** Not gigabytes. Kilobytes. The whole game — code, all 40 hand-traced cards, screens, music — has to live in less space than a single modern emoji sticker.
- **A Z80 processor running at 3.5 MHz**, programmed in raw machine code. No garbage collector, no safety net. If you clobber the wrong register, the machine doesn't throw an exception — it just quietly does the wrong thing forever.
- **A screen laid out by a sadist.** The Spectrum's display memory isn't a tidy grid. The lines are *interleaved* in a famously baffling order, so "the pixel below this one" is 256 bytes away, except when it's not. Colour is stored separately, one ink-and-paper pair per 8×8 cell — the source of the legendary "attribute clash" that gives Spectrum games their look.
- **A one-bit speaker.** There's no sound chip. The CPU physically flicks a single membrane in and out, and *everything* — every note, every chord — is an illusion conjured by toggling that one bit at exactly the right microseconds.

None of this is in a textbook the AI can look up mid-task. It's a body of hard-won folklore. The interesting question wasn't *"can an AI write code?"* — it obviously can. It was *"can it hold all of this arcana in its head at once, and make the thousands of tiny correct decisions a real Spectrum demands?"*

The answer, it turns out, is yes — with one fascinating limitation I'll come back to.

---

## Homework first: studying the masters

We didn't start with the game. We started with the classics.

Before a line of Scopa existed, the AI and I did the homework: reading through the Spectrum programming canon — the books every bedroom coder of the era hoarded — and then going past the books to the primary sources. We **disassembled the greats**: *Manic Miner*, *Jet Set Willy*, *Knight Lore*, *Alien 8*, *Skool Daze*. Not to copy anything, but to answer one question properly: how did they get smooth, flicker-free movement out of a machine with no hardware sprites, no double buffer, and no help?

The answers became a catalogue of techniques — save the background under a sprite before you draw it; redraw only the bytes that changed; race the television's electron beam down the screen so it never catches you mid-draw; count your budget in CPU cycles per scanline. That catalogue is all over the finished game. When a card slides across the felt without a flicker, somewhere in there is a trick learned from watching the sprites of *Skool Daze* glide through their classrooms.

If you want to build something worthy of the machine, it turns out, you start the way we would have started in 1983: by peering at how the best people did it.

---

## How the collaboration actually worked

I want to be honest about the shape of this, because it's the most interesting part.

I didn't type "make me a Spectrum card game" and walk away. And the AI — I was working with Anthropic's Claude Code — didn't just spit out a finished program. It was a real collaboration, and we each did what we were good at.

**The AI was the hands.** It wrote the Z80 assembly — some 8,800 lines of it. It knew the screen layout, the timing of every instruction, the keyboard matrix, the contention quirks. It assembled the code, ran it in an emulator it drove itself, took screenshots, read back the machine's memory to check its own work, and debugged. Tirelessly. At three in the afternoon and again at midnight, with exactly the same patience.

**I was the senses and the taste.** I made the decisions — match to 11, a strong AI opponent, cards faithful to Angelo's Neapolitan deck. And crucially, *I* was the one with a real Spectrum and a CRT television. I was the eyes that could see whether the colours sang and the ears that could hear whether the music was any good.

That last point matters more than you'd think, and it produced some of the best comedy of the whole project.

---

## The bug that swept a card across the screen, forever

Here's a vignette that captures what 8-bit programming is really like.

I wanted the cards to *animate* — when you capture cards and the rest shuffle along to close the gap, I wanted them to **zip** smoothly into their new positions. Lovely idea. The AI built it.

Then I reported back from the real machine: the game had **hung**, and "a card was randomly moving around in the background!"

To anyone who's done this, that sentence is a *diagnosis*. The AI worked it out in seconds. Deep in the animation code, a card was sliding left toward the edge of the table. When it got within a few columns of its target, the code subtracted four from its position — but the position was stored as an *unsigned* byte. Subtracting four from a small number didn't give a negative; it **wrapped around to 254**. The card lurched off to the far right and started its journey all over again, every frame, forever — an infinite loop of a single card pacing across the felt while the whole game froze behind it.

It's the sort of bug that's pure 8-bit: no crash, no error message, just a machine cheerfully doing precisely what you told it. The fix was three instructions. We also added a safety cap so a runaway animation could *never* hang the game again, and a test that reproduced the exact scenario. Caught, fixed, fortified — in minutes.

---

## Making room: a routine named after Angelo

Memory got tight. The code kept growing and started bumping into the title screen sitting in RAM right above it. On a 48K machine you can't just ask for more; you have to *earn* the space.

Earlier in the project we'd written a little screen-compression routine — a classic run-length encoder — and, fittingly, it carried Angelo's name. We pointed it at the title screen, squeezing it from nearly 7 KB down to about 4.6, and then pulled a slightly cheeky trick: we parked the *compressed* title inside the memory we use as a drawing scratchpad during play. At boot it unpacks onto the screen; the instant the game starts, that same memory is reused as the back-buffer and the compressed image is simply overwritten. The title screen costs *zero* permanent storage.

It freed about 7 KB — and there was something quietly moving about it. **Angelo's namesake routine made room for Angelo's game.**

The encoder itself has since given way to ZX0 — a tighter, modern squeeze we now use for every screen and the whole card deck. But the trick it pioneered stayed, and so did the gesture.

---

## The music: from "distressed cat" to Funiculì, Funiculà

The bit I'd most love you to picture is the music.

I wanted a proper tune on the title screen — something gloriously Italian, played not as flat bleeps but with the richness the best Spectrum games managed, where rapid-fire notes fuse into something like a chord. We settled on *Funiculì, Funiculà*.

The first attempt was, in my exact words to the AI, **"a cross between a distressed cat and the sound of a multi-tone phone dialling."**

The AI didn't get defensive. It diagnosed it instantly: it had tried to play two notes at once by *XOR-ing* two square waves together — and XOR-ing two tones produces their sum and difference frequencies, which is *literally* how a telephone makes dial tones. I'd accidentally commissioned a tiny Z80 program to dial a phone.

So it changed technique — to **time-division**: instead of mixing the two voices into a muddle, it gives the speaker to the melody for a sliver of a microsecond, then to the bass, then back, thousands of times a second. Two *pure* tones, interleaved so fast your ear hears them together. It re-tuned the whole note table for the new timing, slowed the tempo, and added a little tarantella oom-pah bass.

I pressed play. A clean, cheerful, unmistakably Italian *Funiculì, Funiculà* came out of a forty-year-old computer. "That's awesome," I wrote. "Let's stick with that."

---

## The opponent that counts cards

A card game lives or dies by its opponent, and I wanted one worth beating. The finished game has four levels, and the top one — *Esperto* — does something I'm genuinely proud of.

It counts cards. It remembers every card that's been played, all game long — and the moment the deck runs out, that bookkeeping becomes X-ray vision. The cards it hasn't seen *must* be the ones in your hand; there's nowhere else for them to be. So for the final tricks it stops guessing and *searches*, playing out every possible line to the end of the deal — a proper alpha-beta minimax, the algorithm inside chess engines, running on a 3.5 MHz Z80. It plays the endgame perfectly. In head-to-head testing it beats the next level down in nearly three-quarters of matches.

And it plays **fair** — we went to some lengths to prove that, because feelings are not evidence. The AI never peeks at your hand or the deck; Esperto's endgame "knowledge" is a deduction any human card-counter could legitimately make. When I became suspicious that the player seemed to win more often than the computer, we didn't shrug — we ran a **forty-thousand-match simulation**. (It was variance. I owed the machine an apology.) When I realised I'd never once seen the opening deal put two cards of the same value on the table, we exhaustively tested **all 8,192 possible shuffle seeds**. (It happens 41% of the time; I just hadn't been paying attention.) And near the end, the AI built a watchdog that made the shipped game logic play itself for match after match, flagging any move a deeper analysis could beat — then replayed every flagged decision through the real Z80 code, in the emulator, to prove the findings weren't an artefact of the test harness.

That's what quality looks like when one of the collaborators never gets bored.

---

## The thing an AI cannot do — and why that's the point

Throughout all of this ran a beautiful limitation: **the AI cannot see a CRT or hear a speaker.**

It can build the program. It can run it in an emulator and read the screen out of memory pixel by pixel. It even, at one point, captured the raw audio the emulator produced and did a frequency analysis on it to *prove* the musical scale was in tune — a genuinely clever bit of self-verification. But it cannot *experience* the result. It can't tell you whether the cyan looks right on a glass tube in a dim room, or whether a jingle is charming or grating.

I can. And so the whole project found a natural rhythm: the AI would build and verify everything it possibly could on its own, then hand me something to *witness* on the real hardware — and I'd come back with "the cat's gone, but it's too fast," or "the laid card gets a bit lost when the table's crowded." It would dig in, find the cause, and fix it.

More than fifty numbered refinement rounds ran on that loop, and the television kept catching what the emulator never could. Animations that were mathematically correct showed "horizontal blinds" on the glass — the redraw racing the TV's electron beam and losing — until every transition in the game was rebuilt to be beam-synced and tear-free. A loading-screen flourish that looked lovely in the emulator derailed real tape players, which stream on regardless of whether the Spectrum is ready. And then there was my favourite bug of the entire project.

---

## The one-pixel ghost

Late in development, my real Spectrum showed me something impossible.

Whenever the rightmost card on the table flashed, a sliver — one pixel wide, a full card tall — flashed in perfect sync at the **far left edge of the screen**, the opposite side from anything that was happening. The AI checked the emulator: nothing. It read the screen memory back byte by byte: the left column was untouched, provably clean. The program was perfect. The glass disagreed.

The cause turned out to be real silicon behaviour. The Spectrum's video chip latches the colour attribute it used at the right-hand edge of a scanline, and under the right conditions that latched colour bleeds into the left-hand edge of the lines that follow. Draw a flashing card in the last column and its colour *escapes around the edge of the screen*. No emulator we used models it. The fix was almost poetic: the rightmost card position now stops one cell short, so the final column of every line is permanently green felt — and the ghost has nothing to smuggle round the back.

I love this bug because it's the whole project in miniature. The AI could write the code, run it, and verify the memory was flawless — and only a human, in a room, with forty-year-old hardware plugged into a television, could see that it wasn't.

---

## Getting it *right*, not just working

One more thing I insisted on, near the end: that the scoring be **exactly correct**. Scopa's scoring is subtle — points for most cards, most coins, the *settebello* (seven of coins), the *primiera* (a wonderfully arcane sub-game of prime values), and a point for every *scopa*, the sweep that clears the table.

I asked the AI to verify it all — and pointedly told it *not* to assume our own earlier reference code was right, but to **research the rules independently.** It did, going to authoritative card-game sources, and confirmed almost everything was correct.

But it found one real bug, and it's a lovely one. There's a rule that a sweep made with the *very last card of the deal* doesn't count as a scopa. Our code was disqualifying the sweep *one card too early* — denying a perfectly legal scopa made on the second-to-last card, when your opponent still has a card to play. The AI traced it to a subtle off-by-one in how an old port had been written, fixed it, and wrote two tests to lock the behaviour down: one for the last card (no scopa), one for the second-to-last (scopa counts). Both pass.

That's the bit that turns a clever demo into something you'd actually trust to keep score.

---

## Forty years late

What exists now is a complete, polished game: faithful hand-traced cards, a four-level opponent that ends in a card-counting endgame solver, flicker-free and tear-free animation throughout, two-part music, an attract mode, and all the rules — including the regional Neapolitan ones — scored correctly. It boots from a real tape, exactly as it would have in 1983, and on the title screen it reads: *"Based on an original ZX Spectrum game by Angelo Colucci."*

The first version took a day, and I keep coming back to that. But the truer number is the month that followed — the fifty-odd rounds of refinement, most of them ending with me walking over to the television to look. Not because the AI is magic: it made mistakes, some of them funny, and it needed a human in the loop at every turn. But the friction of an arcane, unfashionable, four-decades-dead domain — the kind of project that would once have meant weeks of squinting at hex dumps — had almost completely melted away. The knowledge was instantly available. The iteration was instant. The only slow parts left were the two irreplaceable ones: deciding what *right* meant, and looking at the glass to see whether we'd got there.

We tend to talk about AI in terms of the big, obvious things. What struck me, doing this, is how well it turns its hand to the small, *strange* corners — the Z80's quirks, a one-bit speaker, a screen designed by a sadist. The places where the knowledge is real but rare, and the patience required is more than human.

Angelo's cards are back on the screen. And the memory trick pioneered by a routine with his name on it is still, quietly, making room for them.

---

*The game runs on a real, unmodified 48K ZX Spectrum, written entirely in Z80 machine code. Play it in your browser, or download the tape for an emulator or the real thing, at **[scopa-spectrum.gillett-projects.com](https://scopa-spectrum.gillett-projects.com)** (in English and Italian). The full source — and the development log, bugs and all — is at [github.com/tonygillett136/scopa-spectrum](https://github.com/tonygillett136/scopa-spectrum).*
