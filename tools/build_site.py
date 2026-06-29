#!/usr/bin/env python3
"""Generate the bilingual site (EN at /, IT at /it/) from ONE template + one strings table,
so the two languages never drift. Run from scopa/:  python tools/build_site.py

Reads  site_src/template.html  (structure, with {{key}} placeholders)
Writes site/index.html (English)  and  site/it/index.html (Italian)

The game itself is already Italian-flavoured (VINCITORE, CARTE/DENARI/SETTEBELLO/PRIMIERA, NEAPOLITAN,
PALLE DEL CANE are in the ROM) -- only the page chrome is translated here. The Italian is idiomatic, not
literal: glosses that exist only for English readers ("broom", "Re (king)") are dropped, since they're
obvious to an Italian. Review welcome (Tony / Angelo).
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "site_src", "template.html")
SITE = os.path.join(ROOT, "site")
BASE = "https://scopa-spectrum.gillett-projects.com"
GH  = "https://github.com/tonygillett136/scopa-spectrum"
ART = GH + "/blob/main/ARTICLE.md"
RUL = GH + "/blob/main/RULES.md"

# Per-language page config (computed, not translated)
def switch(active):
    en = '<a href="/"%s>EN</a>' % (' class="active" aria-current="page"' if active == "en" else "")
    it = '<a href="/it/"%s>IT</a>' % (' class="active" aria-current="page"' if active == "it" else "")
    return en + '<span aria-hidden="true">·</span>' + it

CFG = {
    "en": dict(lang="en", og_locale="en_GB", canonical=BASE + "/",     switch=switch("en")),
    "it": dict(lang="it", og_locale="it_IT", canonical=BASE + "/it/", switch=switch("it")),
}

EN = {
 "title": "SCOPA — an Italian card game for the 48K ZX Spectrum",
 "meta_desc": "Scopa, the Italian card game, hand-written in Z80 machine code for an unmodified 48K Sinclair ZX Spectrum. Play it in your browser, or download the tape. A recreation of Angelo Colucci's lost game.",
 "og_title": "SCOPA for the 48K ZX Spectrum",
 "og_desc": "The Italian card game Scopa, in Z80 machine code for a real 48K ZX Spectrum. Play it in your browser, or download the tape for real hardware.",
 "kicker": "An Italian card game for the&nbsp;48K&nbsp;ZX&nbsp;Spectrum",
 "lede": "<em>Scopa</em>, the classic Italian card game — hand-written in pure Z80 machine code for an unmodified 48K Sinclair ZX&nbsp;Spectrum. The full <em>Napoletane</em> deck, a genuinely strong opponent that plays fair (it never sees your hand), and a match to&nbsp;eleven.",
 "dedication": "A recreation of a friend’s lost game —<br><span>based on an original ZX&nbsp;Spectrum game by&nbsp;Angelo&nbsp;Colucci.</span>",
 "cta_play": "Play in your browser",
 "cta_dl": "Download the tape",
 "hero_alt": "Scopa loading screen: a Neapolitan knight on horseback holding a gold coin, with the SCOPA wordmark over the Italian tricolore",
 "hero_cap": "The tape loading screen — drawn pixel by pixel on the Spectrum.",
 "play_title": "Play it now",
 "play_intro": "<em>Scopa</em> — \"broom\" — is the classic Italian fishing game: play a card to capture table cards that add up to its value, and clear the whole table for a <em>scopa</em>. Most cards, most coins, the seven of coins (the <em>settebello</em>), the <em>primiera</em> and every scopa all score — first to&nbsp;eleven wins. And it runs right here in your browser, no download or plug-ins: give it a moment to boot, then press <kbd>SPACE</kbd> and play. Prefer real hardware? The tape's just below.",
 "gif1_alt": "Animated gameplay: Neapolitan cards played and captured on the cyan felt",
 "gif1_cap": "A hand in play — it even plays itself in attract mode",
 "gif2_alt": "The VINCITORE victory screen with an animated golden sunburst shimmer",
 "gif2_cap": "VINCITORE! — win the match and the golden rays shimmer",
 "controls_title": "Controls",
 "k_move": "Move the cursor over your hand",
 "k_play": "Play the selected card / confirm",
 "k_diff": "Easy / Medium / Hard / Esperto",
 "k_asso": "Toggle the optional <em>Asso piglia tutto</em> rule",
 "k_sound": "Sound on / off",
 "k_howto": "How to play",
 "tip": "The card you play stays in your hand while you choose what to capture, so it never hides the table. Leave it idle and the Spectrum plays itself — press <kbd>SPACE</kbd> to take over.",
 "shots_title": "In play",
 "s1_alt": "Title screen: the Ace of Swords with the SCOPA wordmark and tricolore",
 "s1_cap": "Title screen",
 "s2_alt": "A hand in progress: the cyan felt, the opponent's face-down cards, the table, and your hand",
 "s2_cap": "A hand in progress",
 "s3_alt": "End-of-deal scoring screen showing Carte, Denari, Settebello, Primiera and more",
 "s3_cap": "Round scoring",
 "s4_alt": "The in-game how-to-play screen",
 "s4_cap": "How to play",
 "s5_alt": "The VINCITORE victory screen: the King of Coins on a golden sunburst when you win the match",
 "s5_cap": "Vincitore!",
 "deck_title": "A faithful Neapolitan deck",
 "deck_intro": "Every one of the forty cards is rendered in <em>defined monochrome</em> — crisp black linework with ordered-dither shading — traced faithfully from a real <em>Napoletane</em> deck. The four suits (coins, cups, swords, clubs), the settebello, and the court figures with their hand-placed suit emblems, all on a single 48&nbsp;KB machine.",
 "deckhero_alt": "Five cards close up: the seven of coins, ace of cups, king of coins, knight of cups and king of clubs",
 "deckfull_alt": "The complete forty-card Neapolitan deck rendered for the ZX Spectrum",
 "deckfull_cap": "The complete forty-card deck.",
 "feat_title": "What’s inside",
 "f1_t": "Pure Z80",
 "f1_b": "100% hand-written machine code on an unmodified 48K Spectrum — no extra hardware, no 128K.",
 "f2_t": "A strong opponent",
 "f2_b": "Four levels — Easy, Medium, Hard and <em>Esperto</em>. Each weighs every legal play with a tuned value function; Esperto counts cards and, once the deck runs out, searches the endgame exactly. It plays fair: it never sees your hand.",
 "f3_t": "Full scoring",
 "f3_b": "Carte, Denari, the Settebello, Primiera, every Scopa, plus the regional Napola and <em>palle del cane</em> bonuses. First to eleven wins.",
 "f4_t": "Authentic art",
 "f4_b": "Every rank and suit stays legible at the Spectrum’s 48&times;64 pixels — down to the little crowns that tell a <em>Re</em> (king) from a <em>Fante</em> (knave).",
 "f5_t": "Optional rule",
 "f5_b": "<em>Asso piglia tutto</em> — the ace sweeps the whole table — included as a toggle, off by default, in the <em>Scopa d’Assi</em> reading.",
 "f6_t": "Loads from tape",
 "f6_b": "A silent multi-part loader boots straight to the title screen on real hardware — TZX and TAP both provided.",
 "f7_t": "It plays itself",
 "f7_b": "Leave it idle on the title and an attract mode takes over — the AI plays itself at <em>Esperto</em>, hand after hand. Press <em>Space</em> to step in.",
 "dl_title": "Download &amp; play on real hardware",
 "dl_intro": "Grab a tape image for your real Spectrum or your favourite emulator (Fuse, ZEsarUX, Spectaculator…). Both load identically; the TZX also carries title, author and year metadata.",
 "dl_tzx_meta": "Recommended · with archive metadata · ~36 KB",
 "dl_tap_meta": "Plain tape image · ~36 KB",
 "dl_sna_meta": "48K snapshot · instant load, no tape · ~48 KB",
 "dl_note": "On a real 48K Spectrum: <code>LOAD \"\"</code> and play the tape. It boots itself to the title screen.",
 "story_title": "The story",
 "story_p1": "Years ago a friend, <strong>Angelo Colucci</strong>, wrote a game of Scopa for the ZX&nbsp;Spectrum. Its hand-drawn cards were superb — and, like so much home-grown 8-bit software, it slipped away with the tapes and the years.",
 "story_p2": "This is a recreation, built to honour it — and to put it back in Angelo’s hands: the Italian card game in full, written from scratch in Z80 machine code for a real 48K machine. The rules and scoring were checked against the standard Neapolitan game, the card art traced faithfully from a physical deck, and the AI tuned over tens of thousands of self-played games. The whole thing was developed and tested on real hardware, on a CRT.",
 "story_links": '<a href="%s">Read how it was built&nbsp;→</a> &nbsp;·&nbsp; <a href="%s">Source on GitHub</a>' % (ART, GH),
 "story_sign": "— Tony Gillett, 2026",
 "foot_credits": "Game © Tony Gillett 2026 · based on an original by Angelo Colucci.<br>100% Z80 assembly for the 48K ZX Spectrum.<br>Card art is derived from a physical Napoletane deck and rendered in monochrome for the Spectrum.",
 "foot_links": '<a href="%s">Source on GitHub</a> · <a href="%s">How it was built</a> · <a href="%s">Rules &amp; scoring</a>' % (GH, ART, RUL),
}

IT = {
 "title": "SCOPA — il gioco di carte italiano per lo ZX Spectrum 48K",
 "meta_desc": "Scopa, il gioco di carte italiano, scritto a mano in codice macchina Z80 per uno ZX Spectrum 48K Sinclair non modificato. Giocaci nel browser o scarica il nastro. La ricreazione del gioco perduto di Angelo Colucci.",
 "og_title": "SCOPA per lo ZX Spectrum 48K",
 "og_desc": "Il gioco di carte italiano Scopa, in codice macchina Z80 per un vero ZX Spectrum 48K. Giocaci nel browser o scarica il nastro per l'hardware reale.",
 "kicker": "Un gioco di carte italiano per lo&nbsp;ZX&nbsp;Spectrum&nbsp;48K",
 "lede": "La <em>Scopa</em>, il classico gioco di carte italiano — scritta a mano in puro codice macchina Z80 per uno ZX&nbsp;Spectrum 48K Sinclair non modificato. Mazzo napoletano completo, un avversario davvero forte e leale (non vede mai le tue carte), e partita all'&nbsp;undici.",
 "dedication": "La ricreazione del gioco perduto di un amico —<br><span>basata su un gioco originale per ZX&nbsp;Spectrum di&nbsp;Angelo&nbsp;Colucci.</span>",
 "cta_play": "Gioca nel browser",
 "cta_dl": "Scarica il nastro",
 "hero_alt": "Schermata di caricamento di Scopa: un cavaliere napoletano a cavallo che regge una moneta d'oro, con la scritta SCOPA sul tricolore italiano",
 "hero_cap": "La schermata di caricamento del nastro — disegnata pixel per pixel sullo Spectrum.",
 "play_title": "Gioca subito",
 "play_intro": "La <em>Scopa</em> è il classico gioco di presa italiano: giochi una carta per catturare le carte sul tavolo che ne sommano il valore, e svuotare tutto il tavolo vale una <em>scopa</em>. Si fanno punti con le carte, i denari, il <em>settebello</em>, la <em>primiera</em> e ogni scopa — vince chi arriva per primo a undici. E gira proprio qui nel browser, senza download né plug-in: lascia che si avvii, poi premi <kbd>SPACE</kbd> e gioca. Preferisci l'hardware vero? Il nastro è qui sotto.",
 "gif1_alt": "Gioco animato: carte napoletane giocate e catturate sul panno azzurro",
 "gif1_cap": "Una mano in gioco — gioca anche da solo in modalità dimostrativa",
 "gif2_alt": "La schermata di vittoria VINCITORE con un effetto dorato raggiante animato",
 "gif2_cap": "VINCITORE! — vinci la partita e i raggi dorati luccicano",
 "controls_title": "Comandi",
 "k_move": "Sposta il cursore sulle tue carte",
 "k_play": "Gioca la carta selezionata / conferma",
 "k_diff": "Facile / Medio / Difficile / Esperto",
 "k_asso": "Attiva/disattiva la regola opzionale <em>Asso piglia tutto</em>",
 "k_sound": "Audio acceso / spento",
 "k_howto": "Come si gioca",
 "tip": "La carta che giochi resta in mano mentre scegli cosa catturare, così non nasconde mai il tavolo. Lascialo fermo e lo Spectrum gioca da solo — premi <kbd>SPACE</kbd> per prendere il controllo.",
 "shots_title": "In partita",
 "s1_alt": "Schermata del titolo: l'Asso di spade con la scritta SCOPA e il tricolore",
 "s1_cap": "Schermata del titolo",
 "s2_alt": "Una mano in corso: il panno azzurro, le carte coperte dell'avversario, il tavolo e le tue carte",
 "s2_cap": "Una mano in corso",
 "s3_alt": "Schermata dei punti di fine smazzata: Carte, Denari, Settebello, Primiera e altro",
 "s3_cap": "Conteggio dei punti",
 "s4_alt": "La schermata «come si gioca» dentro al gioco",
 "s4_cap": "Come si gioca",
 "s5_alt": "La schermata di vittoria VINCITORE: il Re di denari sui raggi dorati quando vinci la partita",
 "s5_cap": "Vincitore!",
 "deck_title": "Un fedele mazzo napoletano",
 "deck_intro": "Ognuna delle quaranta carte è resa in <em>monocromia definita</em> — linee nere nitide con ombreggiatura a retino ordinato — ricalcata fedelmente da un vero mazzo <em>napoletano</em>. I quattro semi (denari, coppe, spade, bastoni), il settebello e le figure con i semi disegnati a mano, tutto su una sola macchina da 48&nbsp;KB.",
 "deckhero_alt": "Cinque carte in primo piano: il sette di denari, l'asso di coppe, il re di denari, il cavallo di coppe e il re di bastoni",
 "deckfull_alt": "Il mazzo napoletano completo di quaranta carte realizzato per lo ZX Spectrum",
 "deckfull_cap": "Il mazzo completo di quaranta carte.",
 "feat_title": "Cosa c’è dentro",
 "f1_t": "Puro Z80",
 "f1_b": "Codice macchina scritto a mano al 100% su uno Spectrum 48K non modificato — niente hardware aggiuntivo, niente 128K.",
 "f2_t": "Un avversario forte",
 "f2_b": "Quattro livelli — Facile, Medio, Difficile ed <em>Esperto</em>. Ognuno valuta ogni mossa lecita con una funzione di valore calibrata; l'Esperto conta le carte e, finito il mazzo, risolve il finale in modo esatto. Gioca lealmente: non vede mai le tue carte.",
 "f3_t": "Punteggio completo",
 "f3_b": "Carte, Denari, Settebello, Primiera, ogni Scopa, più i bonus regionali della Napola e delle <em>palle del cane</em>. Vince chi arriva per primo a undici.",
 "f4_t": "Grafica autentica",
 "f4_b": "Ogni valore e ogni seme restano leggibili nei 48&times;64 pixel dello Spectrum — fin nelle piccole corone che distinguono un <em>Re</em> da un <em>Fante</em>.",
 "f5_t": "Regola opzionale",
 "f5_b": "<em>Asso piglia tutto</em> — l'asso prende l'intero tavolo — incluso come opzione, disattivata di default, nella variante <em>Scopa d’Assi</em>.",
 "f6_t": "Si carica da nastro",
 "f6_b": "Un caricatore silenzioso in più parti avvia direttamente la schermata del titolo sull'hardware reale — forniti sia TZX che TAP.",
 "f7_t": "Gioca da solo",
 "f7_b": "Lascialo fermo sul titolo e parte la modalità dimostrativa — l'IA gioca contro sé stessa da <em>Esperto</em>, mano dopo mano. Premi <em>Spazio</em> per entrare in gioco.",
 "dl_title": "Scarica e gioca su hardware reale",
 "dl_intro": "Prendi un'immagine del nastro per il tuo Spectrum reale o per il tuo emulatore preferito (Fuse, ZEsarUX, Spectaculator…). Si caricano in modo identico; il TZX include anche i metadati di titolo, autore e anno.",
 "dl_tzx_meta": "Consigliato · con metadati d'archivio · ~36 KB",
 "dl_tap_meta": "Immagine semplice del nastro · ~36 KB",
 "dl_sna_meta": "Snapshot 48K · caricamento istantaneo, senza nastro · ~48 KB",
 "dl_note": "Su un vero Spectrum 48K: <code>LOAD \"\"</code> e avvia il nastro. Si avvia da solo fino alla schermata del titolo.",
 "story_title": "La storia",
 "story_p1": "Anni fa un amico, <strong>Angelo Colucci</strong>, scrisse un gioco di Scopa per lo ZX&nbsp;Spectrum. Le sue carte disegnate a mano erano splendide — e, come tanto software casalingo a 8 bit, è andato perduto con i nastri e con gli anni.",
 "story_p2": "Questa è una ricreazione, fatta per rendergli omaggio — e per rimetterlo nelle mani di Angelo: il gioco di carte italiano per intero, riscritto da zero in codice macchina Z80 per una vera macchina 48K. Le regole e il punteggio sono stati verificati sul gioco napoletano standard, la grafica delle carte ricalcata fedelmente da un mazzo fisico, e l'IA messa a punto con decine di migliaia di partite giocate da sola. Il tutto è stato sviluppato e collaudato su hardware reale, su un CRT.",
 "story_links": '<a href="%s">Come è stato realizzato&nbsp;→</a> &nbsp;·&nbsp; <a href="%s">Codice su GitHub</a>' % (ART, GH),
 "story_sign": "— Tony Gillett, 2026",
 "foot_credits": "Gioco © Tony Gillett 2026 · basato su un originale di Angelo Colucci.<br>100% assembly Z80 per lo ZX Spectrum 48K.<br>La grafica delle carte deriva da un mazzo napoletano fisico, resa in monocromia per lo Spectrum.",
 "foot_links": '<a href="%s">Codice su GitHub</a> · <a href="%s">Come è stato realizzato</a> · <a href="%s">Regole e punteggio</a>' % (GH, ART, RUL),
}

STR = {"en": EN, "it": IT}
OUT = {"en": os.path.join(SITE, "index.html"), "it": os.path.join(SITE, "it", "index.html")}

def main():
    tmpl = open(TEMPLATE, encoding="utf-8").read()
    # sanity: EN and IT define the same keys
    if set(EN) != set(IT):
        sys.exit("EN/IT key mismatch: " + str(set(EN) ^ set(IT)))
    for lang in ("en", "it"):
        out = tmpl
        for k, v in {**STR[lang], **CFG[lang]}.items():
            out = out.replace("{{" + k + "}}", v)
        if "{{" in out:
            import re
            sys.exit(f"{lang}: unsubstituted placeholders: {set(re.findall(r'{{(\w+)}}', out))}")
        os.makedirs(os.path.dirname(OUT[lang]), exist_ok=True)
        open(OUT[lang], "w", encoding="utf-8").write(out)
        print(f"  wrote {os.path.relpath(OUT[lang], ROOT)}  ({len(out)} bytes)")

if __name__ == "__main__":
    main()
