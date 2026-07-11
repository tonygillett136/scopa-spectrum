# Il gioco di carte scomparso — e come l'abbiamo riportato in vita

### Ricostruire un gioco perduto per ZX Spectrum in linguaggio macchina Z80, con un'IA come partner di programmazione

*Traduzione italiana di [ARTICLE.md](ARTICLE.md).*

---

Anni fa, un mio amico — Angelo Colucci — scrisse una versione della Scopa per il Sinclair ZX Spectrum. Ciò che ricordo di più sono le carte. Le aveva disegnate a mano, e su quella piccola macchina dai tasti di gomma del 1982 erano meravigliose: i cavalli e i re del mazzo napoletano, resi con un dettaglio quasi sfrontato su uno schermo che ti dava 256×192 pixel e, francamente, parecchio carattere.

Poi, come succede con queste cose, il gioco si è perso. Le cassette si degradano. Gli scatoloni si smarriscono nei traslochi. Ho cercato in ogni cassetta che ero riuscito a salvare dall'infanzia; gli amici della comunità italiana dello Spectrum hanno gentilmente fatto girare un appello. Niente. Era semplicemente scomparso — un piccolo pezzo privato di storia dell'informatica, senza backup e irrecuperabile.

Ho sempre desiderato riportarlo in vita. Quest'estate ci sono finalmente riuscito, con un collaboratore improbabile: un'intelligenza artificiale.

La prima versione giocabile è nata in un solo, euforico giorno. Farla *bene* — farne qualcosa che l'originale di Angelo meritasse — ha richiesto un altro mese. Ed è in quel mese, si è scoperto, che vive la vera storia.

Questa è la storia di come ha funzionato, del perché è stato più difficile di quanto sembri, e di cosa mi ha insegnato sulla strana nuova divisione del lavoro tra un umano che ricorda una macchina e una macchina che ha letto tutto ciò che è mai stato scritto su di essa.

---

## Perché è davvero difficile

Se non avete mai programmato un home computer degli anni '80, è facile pensare che per un'IA moderna sia *banale* — in fondo una macchina a 8 bit vecchia di quarant'anni è un errore di arrotondamento rispetto all'hardware di oggi, no?

È l'esatto contrario. La programmazione moderna è una storia di abbondanza: gigabyte di memoria, librerie per qualsiasi cosa, un runtime indulgente che ripulisce i tuoi errori. Lo Spectrum è una storia di **scarsità e stranezze**, e vanno rispettate tutte, una per una:

- **48 kilobyte di RAM.** Non gigabyte. Kilobyte. L'intero gioco — il codice, tutte le 40 carte ricalcate a mano, le schermate, la musica — deve stare in meno spazio di un singolo sticker emoji moderno.
- **Un processore Z80 a 3,5 MHz**, programmato in puro linguaggio macchina. Niente garbage collector, niente rete di sicurezza. Se sporchi il registro sbagliato, la macchina non lancia un'eccezione — si limita a fare tranquillamente la cosa sbagliata, per sempre.
- **Uno schermo progettato da un sadico.** La memoria video dello Spectrum non è una griglia ordinata. Le righe si susseguono in un ordine notoriamente sconcertante, per cui «il pixel sotto questo» si trova 256 byte più in là, tranne quando non è così. Il colore è memorizzato a parte, una coppia inchiostro-sfondo per ogni cella di 8×8 — l'origine del leggendario *attribute clash* che dà ai giochi Spectrum il loro aspetto inconfondibile.
- **Un altoparlante a un bit.** Non c'è un chip sonoro. È la CPU a far vibrare fisicamente una singola membrana, dentro e fuori, e *tutto* — ogni nota, ogni accordo — è un'illusione evocata commutando quell'unico bit nei microsecondi esatti.

Niente di tutto questo sta in un manuale che l'IA possa consultare al volo. È un corpus di folclore guadagnato a caro prezzo. La domanda interessante non era *«un'IA sa scrivere codice?»* — ovviamente sì. Era *«riesce a tenere tutti questi arcani in testa contemporaneamente, e a prendere le migliaia di piccole decisioni corrette che un vero Spectrum esige?»*

La risposta, si è scoperto, è sì — con un limite affascinante su cui tornerò.

---

## Prima i compiti: studiare i maestri

Non siamo partiti dal gioco. Siamo partiti dai classici.

Prima che esistesse una sola riga di Scopa, io e l'IA abbiamo fatto i compiti: leggere il canone della programmazione Spectrum — i libri che ogni bedroom coder dell'epoca custodiva gelosamente — e poi andare oltre i libri, alle fonti primarie. Abbiamo **disassemblato i grandi**: *Manic Miner*, *Jet Set Willy*, *Knight Lore*, *Alien 8*, *Skool Daze*. Non per copiare qualcosa, ma per rispondere come si deve a una domanda: come ottenevano un movimento fluido e senza sfarfallio da una macchina senza sprite hardware, senza double buffer e senza alcun aiuto?

Le risposte sono diventate un catalogo di tecniche — salva lo sfondo sotto uno sprite prima di disegnarlo; ridisegna solo i byte che sono cambiati; fai a gara col pennello elettronico del televisore giù per lo schermo, così non ti coglie mai a metà disegno; conta il tuo budget in cicli di CPU per linea di scansione. Quel catalogo è dappertutto nel gioco finito. Quando una carta scivola sul panno verde senza un tremolio, lì dentro da qualche parte c'è un trucco imparato guardando gli sprite di *Skool Daze* planare per le loro aule.

Se vuoi costruire qualcosa di degno della macchina, a quanto pare, si comincia come avremmo cominciato nel 1983: scrutando come facevano i migliori.

---

## Come ha funzionato davvero la collaborazione

Voglio essere onesto sulla forma di tutto questo, perché è la parte più interessante.

Non ho digitato «fammi un gioco di carte per lo Spectrum» per poi andarmene. E l'IA — lavoravo con Claude Code di Anthropic — non ha semplicemente sputato fuori un programma finito. È stata una collaborazione vera, e ognuno ha fatto ciò che sapeva fare meglio.

**L'IA era le mani.** Ha scritto l'assembly Z80 — circa 8.800 righe. Conosceva la disposizione dello schermo, i tempi di ogni istruzione, la matrice della tastiera, le stranezze della memory contention. Assemblava il codice, lo eseguiva in un emulatore che pilotava da sola, faceva screenshot, rileggeva la memoria della macchina per verificare il proprio lavoro, e faceva debug. Instancabilmente. Alle tre del pomeriggio e di nuovo a mezzanotte, con esattamente la stessa pazienza.

**Io ero i sensi e il gusto.** Prendevo le decisioni — partita agli 11, un avversario forte, carte fedeli al mazzo napoletano di Angelo. E, cosa cruciale, ero *io* quello con un vero Spectrum e un televisore a tubo catodico. Ero gli occhi capaci di vedere se i colori cantavano e le orecchie capaci di sentire se la musica valeva qualcosa.

Quest'ultimo punto conta più di quanto pensiate, e ha prodotto alcune delle scene più comiche dell'intero progetto.

---

## Il bug che faceva vagare una carta per lo schermo, per sempre

Ecco una scenetta che cattura cos'è davvero la programmazione a 8 bit.

Volevo che le carte fossero *animate* — quando catturi delle carte e le altre scalano per chiudere il vuoto, volevo che sfrecciassero fluide nelle loro nuove posizioni. Bella idea. L'IA l'ha costruita.

Poi ho riferito dalla macchina vera: il gioco si era **bloccato**, e «una carta si muoveva a caso sullo sfondo!»

Per chiunque abbia fatto queste cose, quella frase è una *diagnosi*. L'IA l'ha risolta in pochi secondi. Nel profondo del codice di animazione, una carta scivolava verso sinistra, verso il bordo del tavolo. Arrivata a poche colonne dalla destinazione, il codice sottraeva quattro dalla sua posizione — ma la posizione era memorizzata come byte *senza segno*. Sottrarre quattro a un numero piccolo non dava un negativo: **faceva il giro e tornava a 254**. La carta schizzava all'estrema destra e ricominciava il viaggio da capo, a ogni frame, per sempre — il loop infinito di un'unica carta che passeggiava sul panno mentre l'intero gioco restava congelato alle sue spalle.

È il tipo di bug puramente 8-bit: nessun crash, nessun messaggio d'errore, solo una macchina che fa allegramente ed esattamente quello che le hai detto di fare. La correzione stava in tre istruzioni. Abbiamo anche aggiunto un tetto di sicurezza perché un'animazione impazzita non potesse *mai più* bloccare il gioco, e un test che riproduceva lo scenario esatto. Preso, corretto, blindato — in pochi minuti.

---

## Fare spazio: una routine che porta il nome di Angelo

La memoria cominciava a scarseggiare. Il codice continuava a crescere e aveva iniziato a sbattere contro la schermata del titolo, che se ne stava in RAM proprio lì sopra. Su una macchina da 48K non puoi chiedere di più: lo spazio te lo devi *guadagnare*.

All'inizio del progetto avevamo scritto una piccola routine di compressione dello schermo — un classico run-length encoder — e, com'era giusto, portava il nome di Angelo. L'abbiamo puntata sulla schermata del titolo, comprimendola da quasi 7 KB a circa 4,6, e poi abbiamo tirato fuori un trucchetto sfacciato: abbiamo parcheggiato il titolo *compresso* dentro la memoria che durante la partita usiamo come area di lavoro per il disegno. All'avvio si decomprime sullo schermo; nell'istante in cui la partita comincia, quella stessa memoria viene riutilizzata come back-buffer e l'immagine compressa viene semplicemente sovrascritta. La schermata del titolo costa *zero* byte di memoria permanente.

Ha liberato circa 7 KB — e c'era qualcosa di sommessamente commovente in tutto questo. **La routine che porta il nome di Angelo ha fatto spazio al gioco di Angelo.**

L'encoder ha poi ceduto il posto a ZX0 — una compressione moderna e più efficiente, che ora usiamo per ogni schermata e per l'intero mazzo. Ma il trucco che aveva inaugurato è rimasto, e con lui il gesto.

---

## La musica: da «gatto in difficoltà» a Funiculì, Funiculà

La parte che più vorrei riusciste a immaginare è la musica.

Volevo una vera melodia sulla schermata del titolo — qualcosa di gloriosamente italiano, suonato non a bip piatti ma con la ricchezza che i migliori giochi Spectrum riuscivano a ottenere, dove note in rapidissima successione si fondono in qualcosa che somiglia a un accordo. Abbiamo scelto *Funiculì, Funiculà*.

Il primo tentativo era, testuali mie parole all'IA, **«un incrocio tra un gatto in difficoltà e il suono di un telefono a toni che compone un numero»**.

L'IA non si è messa sulla difensiva. Ha fatto la diagnosi all'istante: aveva provato a suonare due note insieme facendo lo *XOR* di due onde quadre — e lo XOR di due toni produce le loro frequenze somma e differenza, che è *letteralmente* il modo in cui un telefono genera i toni di composizione. Avevo commissionato per sbaglio a un programmino Z80 di comporre un numero di telefono.

Così ha cambiato tecnica — passando alla **divisione di tempo**: invece di impastare le due voci in un pasticcio, cede l'altoparlante alla melodia per una frazione di microsecondo, poi al basso, poi di nuovo alla melodia, migliaia di volte al secondo. Due toni *puri*, alternati così in fretta che l'orecchio li sente insieme. Ha ricalibrato l'intera tabella delle note per la nuova temporizzazione, rallentato l'andamento e aggiunto un piccolo basso oom-pah da tarantella.

Ho premuto play. Da un computer di quarant'anni è uscita una *Funiculì, Funiculà* pulita, allegra, inconfondibilmente italiana. «Fantastico», ho scritto. «Teniamola così.»

---

## L'avversario che conta le carte

Un gioco di carte vive o muore con il suo avversario, e io ne volevo uno che valesse la pena battere. Il gioco finito ha quattro livelli, e il più alto — *Esperto* — fa una cosa di cui vado sinceramente fiero.

Conta le carte. Ricorda ogni carta giocata, per tutta la partita — e nel momento in cui il mazzo finisce, quella contabilità diventa una vista a raggi X. Le carte che non ha visto *devono* essere quelle nella vostra mano; non c'è nessun altro posto dove possano stare. Così, per le ultime prese, smette di tirare a indovinare e *cerca*: gioca ogni possibile seguito fino alla fine della mano — un vero minimax con potatura alfa-beta, l'algoritmo che sta dentro i motori scacchistici, in esecuzione su uno Z80 a 3,5 MHz. Gioca il finale in modo perfetto. Nei test testa a testa batte il livello inferiore in quasi tre partite su quattro.

E gioca **pulito** — e ci siamo presi la briga di dimostrarlo, perché le sensazioni non sono prove. L'IA non sbircia mai la vostra mano né il mazzo; la «conoscenza» di Esperto nel finale è una deduzione che qualunque contatore di carte umano potrebbe legittimamente fare. Quando mi è venuto il sospetto che il giocatore vincesse più spesso del computer, non ci siamo stretti nelle spalle — abbiamo lanciato una **simulazione da quarantamila partite**. (Era varianza. Dovevo delle scuse alla macchina.) Quando mi sono accorto di non aver mai visto, nemmeno una volta, la distribuzione iniziale mettere sul tavolo due carte dello stesso valore, abbiamo testato esaustivamente **tutti gli 8.192 semi possibili del mescolamento**. (Succede il 41% delle volte; semplicemente non ci avevo fatto caso.) E verso la fine l'IA ha costruito un cane da guardia che faceva giocare la logica di gioco effettivamente pubblicata contro se stessa, partita dopo partita, segnalando ogni mossa che un'analisi più profonda sapesse battere — per poi rigiocare ogni decisione segnalata attraverso il vero codice Z80, nell'emulatore, per dimostrare che i risultati non erano un artefatto del banco di prova.

Ecco che aspetto ha la qualità quando uno dei collaboratori non si annoia mai.

---

## Ciò che un'IA non può fare — ed è proprio questo il punto

Attraverso tutto questo correva un limite bellissimo: **l'IA non può vedere un tubo catodico né sentire un altoparlante.**

Può costruire il programma. Può eseguirlo in un emulatore e leggere lo schermo dalla memoria, pixel per pixel. A un certo punto ha perfino catturato l'audio grezzo prodotto dall'emulatore e ci ha fatto sopra un'analisi in frequenza per *dimostrare* che la scala musicale era intonata — un pezzo di auto-verifica sinceramente ingegnoso. Ma non può *fare esperienza* del risultato. Non può dirti se il ciano rende bene su un tubo di vetro in una stanza in penombra, o se un motivetto è delizioso o irritante.

Io sì. E così l'intero progetto ha trovato un ritmo naturale: l'IA costruiva e verificava da sola tutto il possibile, poi mi consegnava qualcosa da *testimoniare* sull'hardware vero — e io tornavo con «il gatto è sparito, ma è troppo veloce», oppure «la carta giocata si perde un po' quando il tavolo è affollato». Lei scavava, trovava la causa e correggeva.

Più di cinquanta round numerati di rifinitura hanno girato su quel ciclo, e il televisore continuava a cogliere ciò che l'emulatore non avrebbe mai potuto. Animazioni matematicamente corrette mostravano sul vetro un «effetto veneziana» — il ridisegno che gareggiava col pennello elettronico del televisore, e perdeva — finché ogni transizione del gioco non è stata ricostruita per essere sincronizzata col raggio e senza strappi. Un vezzo della schermata di caricamento che in emulatore era delizioso mandava fuori sincrono i registratori veri, che continuano a scorrere il nastro indipendentemente dal fatto che lo Spectrum sia pronto. E poi c'è stato il mio bug preferito dell'intero progetto.

---

## Il fantasma largo un pixel

Verso la fine dello sviluppo, il mio Spectrum vero mi ha mostrato qualcosa di impossibile.

Ogni volta che la carta più a destra del tavolo lampeggiava, una scheggia — larga un pixel, alta quanto una carta — lampeggiava in perfetto sincrono al **bordo sinistro estremo dello schermo**, il lato opposto a qualsiasi cosa stesse succedendo. L'IA ha controllato l'emulatore: niente. Ha riletto la memoria video byte per byte: la colonna di sinistra era intatta, dimostrabilmente pulita. Il programma era perfetto. Il vetro non era d'accordo.

La causa si è rivelata un comportamento reale del silicio. Il chip video dello Spectrum trattiene l'attributo di colore usato al bordo destro di una linea di scansione e, nelle condizioni giuste, quel colore trattenuto sanguina nel bordo sinistro delle linee successive. Disegna una carta lampeggiante nell'ultima colonna, e il suo colore *evade facendo il giro del bordo dello schermo*. Nessuno degli emulatori che abbiamo usato lo modella. La correzione è stata quasi poetica: la posizione della carta più a destra ora si ferma una cella prima, così l'ultima colonna di ogni riga è permanentemente panno verde — e il fantasma non ha più nulla da contrabbandare dietro l'angolo.

Amo questo bug perché è l'intero progetto in miniatura. L'IA poteva scrivere il codice, eseguirlo e verificare che la memoria fosse impeccabile — e solo un umano, in una stanza, con un hardware di quarant'anni collegato a un televisore, poteva vedere che non lo era.

---

## Farlo *giusto*, non solo funzionante

Un'ultima cosa su cui ho insistito, verso la fine: che il punteggio fosse **esattamente corretto**. Il punteggio della Scopa è sottile — punti per le carte, per i denari, per il *settebello*, per la *primiera* (quel meraviglioso sottogioco arcano di valori), e un punto per ogni *scopa*, la presa che ripulisce il tavolo.

Ho chiesto all'IA di verificare tutto — e le ho detto espressamente di *non* dare per buono il nostro vecchio codice di riferimento, ma di **ricercare le regole in modo indipendente**. L'ha fatto, consultando fonti autorevoli sui giochi di carte, e ha confermato che quasi tutto era corretto.

Ma ha trovato un bug vero, ed è delizioso. C'è una regola per cui una scopa fatta con *l'ultimissima carta della mano* non conta. Il nostro codice squalificava la presa *una carta troppo presto* — negando una scopa perfettamente legale fatta con la penultima carta, quando l'avversario ha ancora una carta da giocare. L'IA ha rintracciato la causa in un sottile errore di uno in un vecchio porting, l'ha corretta, e ha scritto due test per blindare il comportamento: uno per l'ultima carta (niente scopa), uno per la penultima (la scopa vale). Entrambi passano.

È il pezzo che trasforma una demo ingegnosa in qualcosa a cui affideresti davvero il conteggio dei punti.

---

## Quarant'anni dopo

Quello che esiste ora è un gioco completo e rifinito: carte fedeli ricalcate a mano, un avversario a quattro livelli che culmina in un risolutore di finali che conta le carte, animazioni senza sfarfallii né strappi dall'inizio alla fine, musica a due voci, una modalità dimostrativa, e tutte le regole — comprese quelle regionali napoletane — conteggiate correttamente. Si carica da una cassetta vera, esattamente come avrebbe fatto nel 1983, e sulla schermata del titolo si legge: *«Based on an original ZX Spectrum game by Angelo Colucci»*.

La prima versione ha richiesto un giorno, e continuo a tornarci col pensiero. Ma il numero più vero è il mese che è seguito — la cinquantina di round di rifinitura, la maggior parte dei quali finiva con me che andavo fino al televisore a guardare. Non perché l'IA sia magica: ha fatto errori, alcuni anche buffi, e ha avuto bisogno di un umano nel circuito a ogni passo. Ma l'attrito di un dominio arcano, fuori moda, morto da quattro decenni — il tipo di progetto che un tempo avrebbe significato settimane passate a strizzare gli occhi su dump esadecimali — si era quasi completamente dissolto. La conoscenza era immediatamente disponibile. L'iterazione era istantanea. Le uniche parti lente rimaste erano le due insostituibili: decidere cosa significasse *giusto*, e guardare il vetro per capire se c'eravamo arrivati.

Tendiamo a parlare di IA in termini di cose grandi e ovvie. Ciò che mi ha colpito, facendo questo, è quanto bene se la cavi negli angoli piccoli e *strani* — le stranezze dello Z80, un altoparlante a un bit, uno schermo progettato da un sadico. I posti dove la conoscenza è reale ma rara, e la pazienza richiesta è più che umana.

Le carte di Angelo sono tornate sullo schermo. E il trucco di memoria inaugurato da una routine che porta il suo nome sta ancora, silenziosamente, facendo loro spazio.

---

*Il gioco gira su un vero ZX Spectrum 48K non modificato, scritto interamente in linguaggio macchina Z80. Potete giocarci nel browser, o scaricare la cassetta per un emulatore o per la macchina vera, su **[scopa-spectrum.gillett-projects.com](https://scopa-spectrum.gillett-projects.com/it/)** (in italiano e in inglese). Il sorgente completo — e il diario di sviluppo, bug compresi — è su [github.com/tonygillett136/scopa-spectrum](https://github.com/tonygillett136/scopa-spectrum).*
