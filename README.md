# Fogpacks Local Hub

Fogpacks è un hub locale per organizzare progetti Minecraft, consultare un catalogo di mod esistenti, gestire i JAR forniti dall’utente e creare texture pixel art con il Mod Maker integrato.

> **Stato del progetto:** applicazione desktop locale in sviluppo. La UI gira nel browser, ma il server Python deve essere avviato sul computer. Pubblicare il repository su GitHub non mette automaticamente online il backend.

## Identità visiva

Il logo ufficiale è incluso in `assets/fogpacks-logo.png` ed è utilizzato nella barra superiore, nella sidebar e come favicon del server locale.

## Lingue

L’interfaccia include Italiano, English e Français. La lingua si seleziona dal menu nella barra superiore e la preferenza viene ricordata nel browser. Le impostazioni, le descrizioni del catalogo e le informazioni sul profilo sono localizzate; i messaggi diagnostici dettagliati del backend possono ancora includere testo tecnico in italiano.

## Requisiti

- Windows 10/11 consigliato.
- Python **3.13** consigliato; è necessario Python 3.11 o superiore (usa `tomllib` della standard library).
- Nessuna dipendenza Python da installare: l'app usa la libreria standard.
- Connessione Internet necessaria soltanto per le funzioni che cercano o scaricano release dai cataloghi online.

## Avvio su Windows

1. Scarica il progetto o estrai lo ZIP.
2. Fai doppio clic su `Avvia_Fogpacks.bat`.
3. Il browser si apre sull'indirizzo locale mostrato nella console, normalmente `http://127.0.0.1:8765`.
4. Per chiudere l'applicazione, torna alla finestra del terminale e premi `Ctrl+C`.

Avvio manuale:

```powershell
py -3.13 fogpacks.py
```

Se il launcher `py` non è disponibile:

```powershell
python fogpacks.py
```

## Compatibilità dichiarata

Il catalogo di download automatico in questa release è limitato a Minecraft **1.21.1**. La versione mostrata nelle Impostazioni è informativa e non modificabile: Fogpacks legge il profilo reale e interrompe l’operazione quando versione o loader non coincidono. Quando un progetto non dichiara in anticipo un loader, Fogpacks tenta la ricerca della release filtrando per loader/versione e controlla i metadati del JAR prima dell’installazione.

## Funzioni

- Dashboard e console con log in tempo reale.
- Rilevamento dei percorsi Minecraft conosciuti e del loader dai metadati disponibili.
- Catalogo di 20 voci Mods e 20 voci client/utility. Il catalogo non garantisce che ogni progetto abbia una release per ogni versione o loader: Fogpacks verifica la compatibilità e segnala quando non trova un file utilizzabile.
- Importazione e analisi locale di JAR, metadati, ID, dipendenze dichiarate e SHA-256.
- Workspace locale per i progetti importati e gli asset esportati.
- Mod Maker: editor pixel art 3D con forme base per oggetti (spada, piccone, lancia, ascia, pugnale, martello, bastone e arco), parametri item (danno, knockback, cooldown, abilità ed effetti), spessore della forma regolabile su 5 livelli, mini anteprima 3D sincronizzata, editor JSON e struttura Java modificabile, esportazione PNG/JSON/ZIP.

Il Mod Maker mostra forme di item estruse in 3D; per gli item, il PNG esportato è una texture piatta con silhouette trasparente. Esporta asset, specifica JSON e una classe Java neutra modificabile, **non un JAR compilato o un item automaticamente registrato**. Danno, knockback, cooldown, abilità ed effetti sono valori di configurazione: per ottenere gli effettivi comportamenti in gioco occorre collegarli al codice gameplay e registrare l’oggetto in una mod compatibile.

## Dati locali e file ignorati da Git

Fogpacks crea questi percorsi mentre viene usato:

- `imports/`: JAR/ZIP locali aggiunti dall'utente e cache dei download.
- `workspace/`: progetti importati e asset creati.
- `backups/`: backup.
- `fogpacks_data.json`: preferenze locali e profilo ricordato.

Questi dati sono esclusi da `.gitignore` per non pubblicare file personali, cache o binari di terze parti. Nella copia locale puoi aggiungere in `imports/` i JAR che hai diritto di usare.

## Download da cataloghi esterni

Le release disponibili, i loader e le regole di distribuzione possono cambiare. CurseForge può rifiutare i download diretti (ad esempio HTTP 403) e alcuni progetti possono essere disponibili soltanto su una piattaforma o non avere una versione compatibile. In questi casi Fogpacks deve segnalare il problema, senza dichiarare completata un'installazione non riuscita. Modrinth e CurseForge sono servizi esterni indipendenti e non sono affiliati a Fogpacks.

## Sicurezza locale

- Il server si lega a `127.0.0.1` e usa una porta libera nell'intervallo configurato.
- Le richieste con Host non locale o Origin cross-site vengono rifiutate.
- I file importati sono verificati prima di essere copiati; i percorsi ZIP sono filtrati durante il ripristino.
- Prima di installare una mod, controlla sempre versione Minecraft, loader, dipendenze e regole del server a cui giochi. Il catalogo online dipende dalla disponibilità delle API e delle release pubbliche.

Non esporre il server locale su una rete pubblica e non inoltrare la sua porta dal router.

## GitHub e GitHub Pages

Questo repository è pronto per il versionamento e include un workflow CI che controlla Python, i test e la sintassi JavaScript. **GitHub Pages non può eseguire direttamente `fogpacks.py`**: può ospitare siti statici, mentre Fogpacks ha bisogno del processo Python per leggere e scrivere file sul PC. Usa GitHub per il codice e avvia l'applicazione localmente tramite il launcher.

## Test

Tutti i test usano la libreria standard di Python:

```powershell
python -m unittest discover -s tests -v
```

La sintassi JavaScript incorporata nella pagina può essere controllata con Node.js 22 o successivo; il workflow GitHub esegue anche questo controllo.

## File di terze parti

Gli archivi GitHub puliti non includono JAR/ZIP di mod di terze parti. I pacchetti binari hanno licenze e condizioni di redistribuzione proprie; aggiungi o distribuisci solo file per i quali hai i diritti necessari. La licenza qui inclusa riguarda esclusivamente il codice originale Fogpacks, non le mod esterne né i loro marchi.
