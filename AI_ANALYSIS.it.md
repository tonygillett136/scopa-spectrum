# IA di Scopa — audit di profondità e conclusione (2026-06-18)

*Traduzione italiana di [AI_ANALYSIS.md](AI_ANALYSIS.md).*

Nato da una giocata che Tony ha visto nella demo (attract mode): *due re in mano, tavolo vuoto,
uno dei due il Re di denari — l'IA ha giocato un re, che è stato subito spazzato da un asso. Non
avrebbe dovuto tenersi il re di denari e buttare l'altro?* Quella singola giocata ha sollevato una
domanda più ampia: **l'intero approccio dell'IA è solido, o fa regolarmente scelte sbagliate?**

Questa è l'indagine completa e la sua conclusione. Script diagnostici: `tools/ai_audit.py`,
`tools/ai_prime.py` (entrambi girano su `tools/ai_tune.py`, una replica fedele lato host del
valutatore Z80 — stessa codifica delle carte, stesse regole di presa, stessi pesi e punteggi:
i risultati si trasferiscono).

> **Nota:** il `W0` incorporato in `ai_tune.py` è la baseline *pre*-taratura. Gli script di audit
> lo sovrascrivono con `SHIPPED`, i pesi realmente compilati in `scopa.asm` (card_count ×3,
> seven 12, drop_7 −5, drop_6 −5, leave_sweep_risk −9, leave_easy_capture −5, ecc.).

## 1. La giocata specifica era corretta

Riprodotta nella replica host con i pesi di serie:

```
Mano = [Re di denari, Re di coppe], tavolo vuoto, asso piglia tutto attivo
  Re di denari  punteggio SCARTO = -16
  Re di coppe   punteggio SCARTO = -12   <- vince il punteggio più alto
  --> l'IA SCARTA il re non di denari, TIENE il Re di denari
```

È esattamente il termine `DROP_DENARI = −4` a fare la differenza. La ricerca strategica
indipendente concorda (Wikipedia, pagat.com, il paper di Di Palma & Lanzi 2018 sullo Scopone):
**i due re valgono uguale per la primiera (valore 10), quindi l'unico discrimine è che il Re di
denari è un *denaro* — mai regalare un denaro al tavolo.** L'IA ha superato esattamente il test
che aveva fatto nascere il dubbio.

La spiegazione più probabile di ciò che si è visto sul CRT: a 48×64 i re si somigliano molto
(proprio il problema di leggibilità già segnalato), così il re *non* di denari buttato è stato
letto come il re di denari. (Esiste un solo caso davvero discutibile — con `[re di denari, 7]` in
mano butta il re di denari per tenersi il sette — ma anche lì tenere il sette è corretto: un 7
vale 21 di primiera ed è un sette.)

## 2. L'architettura

Due motori:

1. **Medio gioco (mazzo non esaurito): un valutatore greedy pesato a 1 mossa (1-ply).** Per ogni
   carta in mano valuta la presa migliore (o lo scarto) con costanti tarate a mano — settebello
   +35, scopa +50, i sette +12, i denari +5, più penalità di sicurezza se lascia il tavolo
   spazzabile — e sceglie il massimo. La demo gioca *questo* finché il mazzo non si esaurisce.
2. **Finale (mazzo esaurito): minimax esatto con potatura alfa-beta** (il livello Esperto).
   Esaurito il mazzo, le carte mai viste *sono* la mano dell'avversario: la posizione diventa a
   informazione perfetta e la ricerca esatta diventa possibile; pilota il vero motore delle
   regole via make/unmake.

Coincide con la raccomandazione accademica per questa famiglia di giochi: **euristica nel medio
gioco a informazione nascosta, ricerca esatta nel finale a informazione perfetta.** Esperto
comincia a cercare nel *primo* istante in cui l'esattezza è possibile (mazzo esaurito); prima
servirebbe una ricerca determinizzata / su information set sopra le carte nascoste — pesante, non
esatta, irrealistica in tempo reale su un 48K.

## 3. È costruita bene? Misure di forza

| Misura (simulazione host, pesi di serie, asso attivo) | Risultato |
|---|---|
| vittorie a specchio (di serie contro di serie) | 0.498 — simmetrica, nessun vantaggio di lato |
| contro un giocatore **casuale** (mosse legali) | **0.837** — competente |
| punto **carte** deciso (non un pareggio 20–20) | 92.8% |
| punto **denari** deciso (non 5–5) | 78.7% (21.3% di pareggi) |
| **primiera** decisa | 95.5% |
| scope per smazzata (entrambi i lati) | 1.484; il 74.8% delle smazzate ha ≥1 scopa |

Valuta le cose giuste nell'ordine giusto, applica la regola della presa singola obbligata, non
rifiuta mai una presa legale, orienta le combinazioni di presa verso i denari, e penalizza già il
lasciare un tavolo con somma ≤10 (la regola anti-scopa).

## 4. Ogni miglioramento a buon mercato è stato provato — nessuno aiuta

La domanda centrale: si può rinforzare a poco prezzo l'euristica del medio gioco? Misurato testa
a testa contro l'IA di serie (percentuale di vittorie; >0.50 = migliore):

| Esperimento | Risultato | Verdetto |
|---|---|---|
| Ri-taratura di tutti i pesi (coordinate-ascent, **a partire** dal set di serie) | 0.507 | rumore — già un ottimo locale |
| Lookahead "paranoico" ingenuo a 2 mosse (sconto 0.3/0.5/0.7) | 0.46–0.48 | **peggio** |
| Tenuta dei denari più forte (drop_denari −4→−10 / −14) | 0.483–0.491 | peggio |
| Prendere più carte (card_count ×3→×4) | 0.497 | rumore |
| Valutare di più i sette | 0.509 | entro il rumore |
| **Consapevolezza del guadagno di primiera** (bonus di presa consapevole del mazzetto) | 0.476–0.498 | peggio / pareggio |
| **Completamento puro del seme** (bonus per prendere in un seme scoperto) | 0.485–0.493 | peggio |
| Scarto del **doppione** (buttare una carta di cui si possiede la gemella) | 0.49–0.505 | rumore |

Tutto atterra al pareggio o sotto.

## 5. Perché — la vera lezione

Il diagnostico sulla consapevolezza di primiera è la pistola fumante. L'IA "primiera-aware" ha
vinto il punto di primiera il **47.8% contro 47.7%** — *nessun cambiamento* — mentre i suoi
denari sono **peggiorati** (38.1% contro 40.7%). Orientare le prese verso la primiera non ha
fatto vincere più primiere; ha solo sacrificato i punti che l'euristica stava già vincendo.

La ragione è strutturale: **i punti comparativi (primiera, denari, carte) emergono sull'intera
smazzata, non da una singola giocata.** La primiera finale dipende dall'intera composizione del
mazzetto lungo ~18 giocate — non da una singola presa avida. Un valutatore a 1 mossa non può
pilotare una quantità emergente e comparativa con l'avidità locale; quando ci prova, distorce
soltanto le scelte localmente corrette (prendi il denaro, prendi il settebello, evita la scopa)
che già azzecca. Tre esperimenti indipendenti — ri-taratura, lookahead e consapevolezza di
primiera — falliscono tutti per lo stesso motivo.

## 6. Conclusione

**L'euristica del medio gioco è al tetto della propria architettura, e questo convalida il
progetto invece di indebolirlo.** L'unica cosa che dimostrabilmente batte un'euristica ben tarata
è la ricerca, e la ricerca è già schierata nell'unico punto in cui è insieme esatta ed economica
(il finale a mazzo esaurito di Esperto).

**Decisione: accettare il verdetto e lasciare l'IA com'è.** Gioca correttamente lo scenario che
aveva fatto nascere il dubbio, è competente (84% contro il caso), è dimostrabilmente vicina al
suo tetto a 1 mossa (ogni miglioramento ovvio è peggiore o non migliore), e ha un finale esatto
genuinamente forte — in una build rifinita, pubblicata e stretta al byte (~50 byte liberi). La
giocata che aveva fatto nascere il dubbio era una buona giocata.

La leva teorica rimasta è la ricerca campionata/determinizzata nel medio gioco (stile ISMCTS):
pesante, non esatta, irrealistica per uno Spectrum 48K in tempo reale — e la simulazione
suggerisce comunque ritorni modesti. Non vale la pena disturbare una build verificata.

---

## 7. Addendum — consapevolezza della napola (2026-06-28): l'unica combinazione concreta, pubblicata per l'OTTICA

Un'osservazione successiva al CRT (Tony): nella demo l'IA ha preso un 7 invece del denaro che
avrebbe *completato* una napola da 3 punti. A differenza di tutti gli esperimenti del §4 — tutte
quantità *emergenti* (primiera, completamento del seme) che un valutatore a 1 mossa
strutturalmente non può pilotare — la napola è **concreta e attribuibile**: la possiedi se e solo
se il tuo mazzetto contiene A+2+3 di denari, incontestabile, esattamente come il settebello che
il valutatore già premia (+35). Era quindi l'unica leva non ancora provata che *poteva*
funzionare. Lacuna confermata: `EvalCapture` valutava sette/settebello/denari ma non chiamava mai
`Napola` (solo `ScoreRound` lo faceva). Modellata in `tools/ai_napola.py` (il pattern pile-aware
di ai_prime.py, replica host fedele): un termine di guadagno-napola = (run(mazzetto+prese) −
run(mazzetto)) × ~35.

| Esperimento | Risultato | Verdetto |
|---|---|---|
| Bonus di presa napola-aware (qualsiasi peso 8–90) | 0.502 (24k partite) | **entro il rumore — non più forte** |

Neutrale, non negativo (a differenza della consapevolezza di primiera): la napola è rara (~14%
delle smazzate), l'IA completa già la maggior parte di quelle completabili (i denari sono
premiati), il conflitto "7 contro denaro-della-napola" è raro, e prendere il denaro significa
rinunciare al 7 (anch'esso prezioso) → in pareggio. Ma soprattutto è **sicuro** — denari
39.4/39.2, primiera 47.9/47.9, carte 46.7/46.2, nessuna cannibalizzazione (il difetto che ha
affondato la consapevolezza di primiera). Consapevolezza delle palle del cane: anch'essa neutrale.

**Decisione (per questo solo termine): PUBBLICATO — per l'ottica, non per la forza.** È l'unica
modifica che corregge una giocata *visibilmente* sbagliata (cosa che conta nella demo, guardata
da tutti, e per la fiducia del giocatore), è dimostrabilmente sicura, ed è economica. **Non**
contraddice il §6 — l'euristica resta al suo tetto di *forza*; la napola è pubblicata come
rifinitura, a occhi aperti. Z80: `NapolaBonus` in `EvalCapture` (+ `BuildNapMask` / `NapRun` /
`OrCoinBit`); verificata dallo unit test `TM65` (prende il denaro della napola nell'esatta
posizione di Tony) e da una demo senza crash. Non esiste altra combinazione concreta trascurata —
il settebello è già premiato; carte/denari/primiera sono emergenti; la **negazione** di
napola/palle richiede il mazzetto nascosto dell'avversario, che solo il minimax di Esperto a
mazzo esaurito vede.

---

## 8. Addendum — il watchdog in self-play (2026-06-29): un audit sistematico, confermato su Z80

Tony ha chiesto uno strumento che faccia giocare la logica reale contro sé stessa per molte
partite e segnali le giocate "strane". `tools/ai_watch.py` è un port host fedele del valutatore
di medio gioco Esperto DI SERIE (aiSelectPlay / EvalCapture / EvalSafety / EvalDrop / CardBonus /
NapolaBonus / ThreatLive — pesi letti direttamente da scopa.asm; conteggio carte `Seen` = tavolo
+ propria mano + ogni carta giocata) che gioca Esperto-contro-Esperto e registra ogni decisione
di medio gioco con tutte le alternative. Il finale (mazzo esaurito) è il minimax esatto —
dimostrabilmente ottimale — quindi le stranezze possono vivere solo nell'euristica di medio
gioco; vengono verificate solo le decisioni a mazzo non esaurito.

Rilevatore ad alto segnale = la **dominanza**: una mossa viene segnalata solo se un'altra mossa
legale è ≥ su *ogni* fondamentale (carte, denari, settebello, guadagno di primiera, scopa, punti
napola), non peggiore sui due assi negativi (regala una scopa all'avversario; lascia il
settebello) e strettamente migliore da qualche parte — una mossa dominata non è giustificabile
da alcun principio scopistico. (Due iterazioni per farlo bene: il vettore deve incassare la carta
*giocata* nella presa e usare il vero guadagno di primiera, altrimenti segnala per errore chi
gioca il settebello per una presa, o chi prende due assi al posto di un denaro.)

**Confermato sul vero Z80.** `tools/ai_zx_check.py` rigioca ogni tavolo segnalato dentro la ROM
pubblicata tramite una sonda a iniezione (`TESTMODE 70`: poke di Table/mano/OPile/Seen, esegue il
vero aiSelectPlay, rilegge BestSlot + la maschera di presa). **14 tavoli su 14 → lo Z80 prende la
decisione identica**: la replica è fedele e i risultati sono la logica realmente pubblicata.
(Trovato + corretto per strada un bug reale dello strumento: `zx_shot.write_mem` usava ZRCP
`write-memory` con una stringa hex concatenata, che rovina le scritture multi-byte — dev'essere
`write-memory-raw`.)

**Risultati (5000 partite Esperto-contro-Esperto, asso disattivato):** ~1.5 giocate di medio
gioco dominate a partita. Su quale fondamentale vince la mossa migliore:

| Categoria | Quota | Lettura |
|---|---|---|
| primiera (incl. +denari/+carte) | ~75% | la nota cecità alla primiera emergente (§4/§6) |
| punti napola | ~16% | un bonus piatto di rango ogni tanto pesa più di un guadagno di napola |
| regala una scopa all'avversario (contro mossa pari e sicura) | ~4% | accettato un piccolo rischio-scopa al posto di un'alternativa equivalente e sicura |
| puri scambi carte / denari | ~5% | marginale |

**Nessuno strafalcione** — zero settebelli scartati, zero punti garantiti rinunciati; i 18
`LEFT_SETTEBELLO` e i rari `PASSED_SCOPA` sono la correzione napola che giustamente completa una
napola da 3–5 punti al posto di una carta da 1 punto.

**Verdetto:** il watchdog ha *riscoperto* per via indipendente i §4/§6 — l'unica subottimalità
sistematica è la marginale cecità primiera/tempo insita in un valutatore a 1 mossa, e il §4 ha
già dimostrato che la consapevolezza di primiera FA DANNO (la primiera è comparativa/emergente
sull'intera smazzata). Nessun bug nuovo; l'IA è solida; lasciata com'è. Riusabile: `python
tools/ai_watch.py [partite]`, poi `python tools/ai_zx_check.py` per confermare su Z80 una
segnalazione.

---

## 9. Addendum — come gioca davvero: le tattiche emergenti e l'archivio dei casi (2026-07-15)

Il valutatore è una dozzina di termini pesati (§2), ma al tavolo quei termini compongono una vera
e propria *dottrina* che nessuno ha programmato esplicitamente. Guardando la demo state guardando
quella dottrina — e parecchie delle sue abitudini a prima vista sembrano sbagliate pur essendo
giuste. Questa sezione mette la dottrina per iscritto, poi elenca ogni momento "quella mossa è
strana" mai sollevato contro l'IA, con i verdetti.

### La dottrina

**Disciplina dei denari: incassa con i denari, scarta gli altri semi.** Un denaro conta per il
punto denari solo dal *mazzetto*, e l'unica strada dalla mano al mazzetto è prendere con quella
carta. Fra due carte di pari valore il valutatore quindi **prende sempre prima con il denaro**
(il +5 della carta giocata finisce nel totale incassato) e **scarta prima quella non di denari**
(`DROP_DENARI −4`). Tenersi un denaro oltre un'occasione di presa rischia di doverlo scartare più
avanti — regalando all'avversario una carta da punto. Quindi: il 2 di denari prende mentre il 2
di spade aspetta; il 2 di spade viene buttato mentre il 2 di denari aspetta. I due ordinamenti
sono lo stesso principio.

**La dottrina dell'asso (asso piglia tutto attivo — la configurazione della demo).** Con la
variante attiva l'asso è la carta più forte della mano, e il valutatore lo tratta così:
- *Tavolo non vuoto:* la spazzata d'asso è quasi sempre la giocata dal punteggio più alto —
  incassa l'intero tavolo e lascia all'avversario un tavolo vuoto, la consegna più sicura
  possibile. (Le spazzate d'asso **non** ricevono il credito scopa +50 — nella lettura Scopa
  d'Assi non danno il punto — quindi la scelta è puro materiale.) Avere un secondo asso la rende
  migliore, non peggiore: l'avversario è ora costretto a scartare sul tavolo vuoto, e il secondo
  asso raccoglie lo scarto. Non esiste un "tenerlo per dopo" — tutte e tre le carte della mano si
  giocano prima della nuova distribuzione; in discussione c'è solo l'ordine, e il materiale dice:
  prima l'asso.
- *Un asso solitario sul tavolo:* un asso lo prende (riarma la tua minaccia di spazzata,
  disinnesca la loro).
- *Tavolo vuoto, scarto forzato:* a volte **scarta deliberatamente un asso** — un asso sul tavolo
  è un'armatura anti-spazzata, perché a quel punto l'asso avversario può solo prendere quell'asso
  invece di spazzare tutto ciò che si accumula. Lo fa solo quando gli scarti alternativi sono a
  loro volta rischiosi (bassi, accoppiabili); con una figura in mano scarta la figura e si tiene
  entrambi gli assi.
- Anche qui vale la disciplina dei denari: l'asso di *denari* spazza per primo; l'asso non di
  denari è quello che viene scartato come armatura.

**La gerarchia degli scarti.** Settebello −40 (quasi mai), ogni 7 −5 e ogni 6 −5 (i ranghi della
primiera), ogni denaro −4, figure (8/9/10) +3 — le figure sono le carte più economiche da
perdere: il rango peggiore per la primiera e, se non sono denari, nessun valore da punto.

**Anti-scopa con vero conteggio delle carte.** Ogni consegna del tavolo ha un prezzo: un tavolo
con somma ≤10 o con un rango accoppiabile costa punti — ma il controllo `ThreatLive` di Esperto
fa sì che non tema mai una minaccia che può *dimostrare* morta (tutte e quattro le carte di quel
rango già viste). Con l'asso piglia tutto la consegna paga anche l'esposizione alla spazzata
d'asso — a meno che un asso non giaccia sul tavolo (armatura, v. sopra) o tutti gli assi non
siano già contati.

**Le combinazioni concrete sono premiate, quelle emergenti no.** Il settebello (+35) e il
completamento della napola (§7) sono attribuibili a una singola presa, quindi il valutatore li
insegue. Carte, denari e primiera come *totali comparativi* emergono lungo ~18 giocate e
dimostrabilmente non si possono pilotare con un valutatore a 1 mossa (§4–§6) — quindi non ci
prova.

**Il passaggio al finale.** Nell'istante in cui il mazzo si esaurisce, tutto quanto sopra va in
pensione e la posizione passa al minimax esatto (§2). Due conseguenze per lo spettatore: l'ultima
mano è giocata in modo *dimostrabilmente ottimale*, e può **sembrare** arbitraria — quando più
linee arrivano allo stesso punteggio finale, il pareggio si rompe per ordine di enumerazione, non
per estetica. Il minimax ottimizza il risultato, non l'apparenza: scarterà tranquillamente un
denaro che può dimostrare l'avversario non ha modo di prendere.

### L'archivio dei casi

Ogni giocata sospetta mai sollevata (tutte guardando la demo o il CRT), indagata con la replica
host e, dove serviva, sul vero Z80:

| # | Il sospetto | Verdetto | Dove |
|---|---|---|---|
| 1 | Buttato il re di denari con due re in mano (2026-06-18) | **IA nel giusto** — tiene il re di denari (−12 contro −16); il re buttato era quello *non* di denari, letto male a 48×64 | §1 |
| 2 | Preso un 7 invece di completare una napola da 3 punti (2026-06-28) | **Lacuna vera** — l'unica confermata; termine napola pubblicato (per l'ottica — neutro in forza) | §7 |
| 3 | Preso un 4 di preferenza al 3 di denari (2026-06-29) | **IA nel giusto** — a parità prende sempre il denaro; preferisce il 4 solo quando quel bottino è strettamente più ricco | DEVLOG |
| 4 | "Il tavolo d'apertura non ha mai una coppia di pari valore — mescolata truccata?" (2026-06-29) | **Onesta** — il 41.2% dei tavoli d'apertura *ha* una coppia, esaustivamente su tutti gli 8.192 semi RNG = esattamente il tasso teorico di un mazzo onesto; le coppie sono sempre di semi diversi e a velocità di demo non si leggono come coppie | `tools/deal_check.py` |
| 5 | "Il lato giocatore vince più spesso della CPU" | **Varianza** — simulazione da 40.000 partite nell'esatta configurazione della demo: 0.502 | DEVLOG |
| 6 | Giocato un asso con due assi + una carta in mano (2026-07-15, asso attivo) | **IA nel giusto** — spazza qualsiasi tavolo non vuoto (23 contro −29 per l'alternativa); su tavolo vuoto lo scarto d'asso è un'armatura anti-spazzata deliberata | questo § |
| 7 | Scartato il 2 di denari tenendo in mano un 2 liscio (2026-07-15) | **Spiegato** — la politica di medio gioco preferisce *dimostrabilmente* lo scarto liscio (−4, replica e Z80 concordano), quindi era il minimax a mazzo esaurito: scartare un denaro è pari-ottimale quando la mano avversaria (interamente dedotta) dimostrabilmente non può punirlo. Se mai visto a mazzo *non* esaurito sarebbe una scoperta vera — iniettare il tavolo via `TESTMODE 70` | questo § |

Punteggio finora: sette sospetti, una lacuna vera (rara, cosmetica, corretta), sei volte in cui
la macchina aveva ragione in un modo che a 48×64, o a velocità di demo, si leggeva come un
errore. Quel rapporto non è fortuna — è esattamente l'aspetto che un valutatore tarato in
self-play, più un vero conteggio delle carte, *deve* avere visto da fuori.

### Interrogare una posizione

Per chiedere al cervello di serie cosa farebbe su un tavolo qualsiasi, si pilota direttamente la
replica verificata (id delle carte: 0–9 denari, 10–19 coppe, 20–29 spade, 30–39 bastoni; valore =
id%10 + 1):

```python
import sys; sys.path.insert(0, "tools")
from ai_watch import ai_select, nm, VAL
hand, table, pile = [1, 21, 15], [31, 38, 13], []
unseen = [0]*11
for v in range(1, 11):
    unseen[v] = 4 - sum(1 for c in hand + table + pile if VAL[c] == v)
r = ai_select(hand, table, pile, unseen, esperto=True, ace_rule=True)
for sc, slot, cs, sweep in sorted(r['options'], key=lambda o: -o[0]):
    print(sc, nm(hand[slot]), "sweep" if sweep else [nm(table[i]) for i in cs] if cs else "drop")
```

La riga col punteggio più alto è ciò che giocherà lo Spectrum (pareggi: vince la prima trovata,
come il `ConsiderBest` dello Z80). Per confermare una decisione di medio gioco sul vero Z80,
iniettare lo stesso tavolo con la sonda `TESTMODE 70` tramite `tools/ai_zx_check.py`.
