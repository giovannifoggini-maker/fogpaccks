## 1.2.3 — 2026-10-20

- Ripristinato il logo originale del cubo viola/blu ricavandolo dall’immagine di riferimento; favicon, icona Apple, logo PNG e SVG condividono ora lo stesso simbolo nelle versioni cloud e locale.
- Ridotti i bordi e gli aloni aggiunti via CSS attorno al marchio per non duplicare la cornice e il bagliore del file originale.

## Cloud Edition visual refresh — 2026-10-20

- Refined the Cloud Edition with a restrained dark-navy palette, subtle violet accents, thinner borders, and less glow.
- Replaced the temporary hero cube illustration with the same cube mark used by the favicon.
- Unified cube logo and favicon assets across Cloud Edition, the local edition, and its downloadable ZIP. No paid API keys or extra runtime dependencies added.

# Changelog

## 1.2.2 — 2026-10-20

- Completate le traduzioni inglese e francese delle impostazioni, delle descrizioni del catalogo e delle etichette dei campi.
- Tradotte le etichette testuali dei valori statici senza sovrascrivere i valori runtime (versione Python, percorso istanza e loader rilevato).
- Resa localizzata anche la descrizione dinamica del profilo Minecraft rilevato.
- Aggiunto un test di copertura per le stringhe della pagina Impostazioni, del catalogo e dei messaggi dinamici più comuni.

## 1.2.0 — 2026-10-20

- Aggiunto il selettore lingua Italiano / English / Français nella barra superiore.
- Tradotti i testi principali della navigazione, dashboard, Mod Maker, cataloghi e impostazioni; la scelta viene mantenuta nel browser.
- Tradotti anche i messaggi più comuni del Mod Maker che cambiano durante disegno, esportazione e salvataggio.
- Ripristinato l’avviso SPERIMENTALE come riquadro autonomo e ben visibile accanto alle abilità speciali degli oggetti.
- Aggiunti test automatici per selettore lingua e avviso sperimentale.


## 1.1.3 — 2026-10-20

- Aumentata la larghezza minima dell'asta di lancia e bastone a 3 pixel sulla griglia 16×16.
- Il cursore dello spessore mantiene ora aste leggibili anche al livello minimo, senza farle collassare a una singola colonna.
- Aggiornati i test di regressione per larghezza delle sagome.

## 1.1.2 — 2026-10-18

- Sostituiti i marchi SVG provvisori con il logo ufficiale Fogpacks ad alta risoluzione.
- Aggiunta la favicon del logo e un endpoint locale con intestazioni di sicurezza.
- Ottimizzato il PNG a 512×512, rimuovendo i pixel di sfondo quasi trasparenti senza compromettere i bordi sfumati.


## 1.1.1 — 2026-10-18

- Aggiunto il logo Fogpacks anche nella barra superiore, con layout ridotto per schermi stretti.
- Ridisegnate le forme base: ascia con lama asimmetrica, martello con testa piatta, lancia con punta stretta e bastone con globo cristallino.
- Resi continui i tratti diagonali dei manici e migliorata la leggibilità delle silhouette nella griglia 16×16.
- Aggiunti controlli di regressione per il logo superiore e per le forme distinte.

## 1.1.0 — 2026-10-18

- Resi coerenti lingua, stato dell'app e messaggi principali dell'interfaccia.
- Eliminati i target di versione del catalogo che non sono coperti dalla release corrente: il catalogo automatico mostra chiaramente Minecraft 1.21.1.
- Distinta la compatibilità nota dall'autoverifica necessaria della release; i loader esplicitamente incompatibili vengono ancora esclusi.
- Aggiunta conferma prima dei batch di installazione, che possono modificare più file del profilo.
- Migliorata la validazione del PNG generato dal canvas: limiti di dimensione, controlli CRC, intestazioni, blocchi e dimensione decompressa.
- Reso atomico il salvataggio del Mod Maker: in caso di errore conserva il progetto precedente e, quando si sovrascrive, non lascia file vecchi tra asset di tipo differente.
- Aggiunti test per integrità PNG, sostituzione completa dei progetti, markup e compatibilità dinamica del loader.
- Migliorati i fallback di stato del frontend e la gestione dei messaggi per evitare notifiche duplicate.
