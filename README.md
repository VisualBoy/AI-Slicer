# AI-Slicer (con Assistente Vocale "Arturo")

## Panoramica del Progetto

AI-Slicer è un assistente vocale Python progettato per semplificare e automatizzare il processo di slicing di modelli 3D utilizzando PrusaSlicer tramite la sua interfaccia a riga di comando. L'obiettivo è permettere all'utente di interagire con PrusaSlicer usando comandi vocali in linguaggio naturale (italiano), gestendo operazioni come il caricamento di modelli, l'elenco di file e l'avvio dello slicing.

L'assistente, chiamato "Arturo", utilizza:
* **RealtimeSTT (con faster_whisper):** Per la trascrizione da parlato a testo (Speech-to-Text), con accelerazione GPU se disponibile.
* **OpenAI API (gpt-4o-mini):** Per la comprensione del linguaggio naturale (NLU), la gestione della conversazione e la decisione di chiamare funzioni specifiche.
* **OpenAI API (tts-1):** Per la generazione da testo a parlato (Text-to-Speech), dando una voce ad Arturo.
* **PrusaSlicer Command Line:** Per eseguire materialmente le operazioni di slicing.
* **Python:** Come linguaggio di programmazione principale, con librerie come `pygame` per l'audio, `python-dotenv` per la configurazione, e `subprocess` per lanciare PrusaSlicer.

## Funzionalità Chiave Implementate

* **Attivazione Vocale:** Risponde alla hotword "Arturo".
* **Riconoscimento Vocale in Italiano:** Trasforma i comandi vocali in testo.
* **Comprensione del Linguaggio Naturale:** Interpreta le richieste dell'utente relative allo slicing.
* **Interazione con PrusaSlicer CLI:**
    * **Elenco File:** Può elencare i file `.stl`, `.3mf`, `.obj` da una cartella predefinita.
    * **Slicing Modelli:** Può avviare lo slicing di un file specificato (per nome dalla cartella predefinita, per numero dalla lista, o per percorso completo) e generare il G-code.
    * **Tentativo di Correzione Z=0:** Se PrusaSlicer riporta un errore "no extrusions in the first layer", Arturo tenta automaticamente un secondo slicing usando l'opzione `--center X,Y` per provare ad allineare il modello al piano Z=0.
* **Risposte Vocali:** Arturo comunica i risultati e gli errori vocalmente.
* **Configurazione Tramite `.env`:** Gestione sicura di API key e percorsi (PrusaSlicer, cartella STL).
* **Gestione dell'Eco Vocale:** Implementate logiche per ridurre l'auto-ascolto dell'assistente.
* **Saluto Vocale all'Avvio:** Arturo saluta l'utente all'avvio dell'applicazione.
* **Gestione Preferenze (Iniziale):** Capacità di caricare, salvare e impostare preferenze di base (come l'altezza predefinita del layer) tramite l'AI, utilizzando il file `preferences.json`.

## Setup e Installazione (Generale)

1.  **Clona il Repository** (se applicabile)
2.  **Crea un Ambiente Virtuale Python:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Su Linux/macOS
    .venv\Scripts\activate    # Su Windows
    ```
3.  **Installa le Dipendenze:**
    ```bash
    pip install -r requirements.txt
    ```
    (Assicurati che `requirements.txt` includa `openai`, `RealtimeSTT`, `faster_whisper`, `pygame`, `python-dotenv`, e PyTorch con supporto CUDA se usi la GPU).
4.  **Configura PrusaSlicer:** Assicurati che PrusaSlicer sia installato e che il percorso al suo eseguibile `prusa-slicer-console.exe` (o equivalente) sia corretto.
5.  **Crea e Configura il File `.env`:**
    Crea un file `.env` nella directory principale con le seguenti variabili:
    ```dotenv
    OPENAI_API_KEY="la_tua_chiave_api_openai"
    PRUSA_SLICER_PATH="C:/Percorso/Completo/A/prusa-slicer-console.exe"
    STL_DEFAULT_FOLDER="C:/Percorso/Alla/Tua/Cartella/STL"
    ```
6.  **(Opzionale) Configura GPU per Whisper:** Per prestazioni ottimali con `faster_whisper`, installa PyTorch con supporto CUDA e assicurati che i driver NVIDIA siano aggiornati. Lo script `ai-slicer.py` è configurato per usare `device="cuda"` e `compute_type="float16"`.

## Utilizzo

Esegui lo script `ai-slicer.py` (o usa il file `run.bat` se configurato):
```bash
python ai-slicer.py
```
Attendi il saluto "Ciao, sono Arturo. In cosa posso aiutarla?" e poi interagisci usando la hotword "Arturo".

**Comandi Esempio:**
* "Arturo, elenca i file."
* "Arturo, processa il file BRISO.stl."
* "Arturo, processa il file numero uno."

## Struttura del Progetto (File Principali)

* `ai-slicer.py`: Script principale, gestisce il loop di input vocale, la logica di interazione e il thread di ascolto.
* `assist.py`: Gestisce la comunicazione con l'API di OpenAI (chat e TTS), la cronologia della conversazione e la mappatura delle function calls.
* `tools.py`: Contiene l'implementazione Python delle funzioni che l'AI può chiamare (es. `slice_model`, `list_stl_files`, `set_preference`).
* `functions.json`: Definisce la struttura delle funzioni disponibili per l'AI (formato OpenAI).
* `shared_variables.py`: Gestisce variabili condivise tra thread (es. ultimo testo trascritto).
* `.env`: File di configurazione per API key e percorsi (non versionato).
* `preferences.json`: (Futuro) File per salvare le preferenze utente.
* `requirements.txt`: Elenco delle dipendenze Python.

## Punti Chiave Discussi e Modifiche Apportate

* **Configurazione Ambiente Python:** Setup con ambiente virtuale.
* **Integrazione OpenAI:** Utilizzo di `gpt-4o-mini` per NLU e `tts-1` per TTS.
* **Integrazione `faster_whisper` (via `RealtimeSTT`):** Per trascrizione STT locale, con supporto GPU.
* **Function Calling OpenAI:** Implementazione per `list_stl_files` e `slice_model`.
* **Interazione PrusaSlicer CLI:** Costruzione dinamica dei comandi.
* **Gestione Percorsi File:** Implementazione di una cartella STL predefinita e gestione di nomi file vs percorsi completi.
* **Correzione Errori PrusaSlicer:** Tentativo automatico di correzione per "no extrusions in first layer" usando `--center`.
* **Lingua Italiana:** Configurazione di STT, TTS e system prompt per l'italiano.
* **Gestione Eco Vocale:** Implementazione di logica di pausa/ripresa del registratore e timestamp per minimizzare l'auto-ascolto.
* **Hotword:** Modificata e debuggata per un riconoscimento più affidabile ("Arturo").
* **TTS per Saluto Iniziale:** Arturo ora saluta vocalmente all'avvio.
* **Refactoring e Debug:** Numerosi cicli di debug per risolvere problemi di logica, API, formattazione JSON, caricamento `.env`, ecc.

## Roadmap

Per le idee di sviluppo futuro e la roadmap dettagliata del progetto, si veda il file [ROADMAP.md](ROADMAP.md).
