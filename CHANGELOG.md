# Changelog AI-Slicer

Tutte le modifiche rilevanti a questo progetto saranno documentate in questo file.

## [Non Rilasciato] - 2025-05-28

### Aggiunto
* **Assistente Vocale "Arturo":**
    * Implementazione di un assistente vocale Python per interagire con PrusaSlicer.
    * Attivazione tramite hotword ("Arturo").
    * Configurazione per la lingua italiana (STT, System Prompt OpenAI, TTS).
    * Saluto vocale all'avvio dell'applicazione.
* **Integrazione PrusaSlicer CLI:**
    * Funzione `slice_model` per avviare lo slicing di file .stl (e altri formati supportati).
        * Accetta nomi file (da cartella predefinita), percorsi completi o numeri da una lista.
        * Genera G-code nella stessa cartella del modello o in un percorso specificato.
    * Funzione `list_stl_files` per elencare i modelli 3D (`.stl`, `.3mf`, `.obj`) in una cartella predefinita.
    * Tentativo di correzione automatica per l'errore PrusaSlicer "no extrusions in the first layer" utilizzando l'opzione `--center X,Y`.
* **Tecnologie Core:**
    * Utilizzo di `RealtimeSTT` con `faster_whisper` (modello `large-v3`) per trascrizione STT locale, con supporto GPU (`device="cuda"`, `compute_type="float16"`).
    * Utilizzo dell'API OpenAI (`gpt-4o-mini`) per NLU e gestione della conversazione.
    * Utilizzo dell'API OpenAI (`tts-1` con diverse voci) per Text-to-Speech.
    * Gestione delle API key e percorsi tramite file `.env` e `python-dotenv`.
* **Miglioramenti UX e Robustezza:**
    * Implementata logica di pausa/ripresa del registratore e gestione di un timestamp (`last_tts_end_time`) per minimizzare l'auto-ascolto/eco dell'assistente.
    * Aggiunta pausa dinamica (prevista, ma implementazione base con `time.sleep(0.5)` dopo il TTS).
    * Debug dettagliato e logica di gestione `expecting_user_response` per migliorare il flusso conversazionale.
    * Struttura del progetto con moduli separati (`assist.py`, `tools.py`, `shared_variables.py`).
    * Script `run.bat` per facilitare l'avvio con attivazione dell'ambiente virtuale.
* **Gestione Preferenze (Iniziale):**
    * Creazione di `preferences.json` (struttura base).
    * Funzioni `load_preferences`, `save_preferences`, `set_preference` in `tools.py`.
    * Function call `set_preference` per permettere all'AI di modificare le preferenze (es. `default_layer_height`).
* **Integrazione Libreria Rich per Interfaccia CLI Migliorata:**
    * Utilizzo di `rich.Console` per output testuali stilizzati (colori per utente/assistente).
    * Implementazione di `rich.Table` per la visualizzazione tabellare dei file 3D (`list_stl_files`).
    * Aggiunta di `rich.Spinner` per indicare gli stati di attesa durante l'elaborazione da parte dell'AI.
    * Configurazione di `rich.logging.RichHandler` per log e traceback più leggibili e formattati.
    * Rimossi i precedenti messaggi di `print("[DEBUG]...")` per una console più pulita, affidandosi alla nuova configurazione di logging.
* **Integrazione OctoPrint API:**
    * Aggiunte funzioni per listare i file su OctoPrint, elencare i profili di slicing disponibili, avviare la stampa di file G-code esistenti e avviare lo slicing di modelli 3D direttamente su OctoPrint.

### Modificato
* **System Prompt OpenAI:** Aggiornato per riflettere il nome "Arturo" e le istruzioni in italiano.
* **Flusso Chiamate Funzioni OpenAI:** Adattato alla sintassi più recente (`tools` e `tool_calls`).
* **Logica di Debug:** Aggiunti numerosi `print` di debug per tracciare il flusso e identificare problemi.
* **Robustezza Codice:** Corretti vari bug (es. `NameError` in `assist.py`, formattazione `functions.json`, gestione caricamento `.env`).
* **Voce TTS:** Discussa e implementata la possibilità di cambiare la voce TTS di OpenAI.
