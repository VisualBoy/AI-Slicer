# AI-Slicer (assistente vocale per la stampa 3D) - Gemini Edition

## Panoramica del Progetto

AI-Slicer è un assistente vocale Python progettato per semplificare e automatizzare il processo di slicing di modelli 3D. Questa versione è stata aggiornata per utilizzare **Google Gemini API**. L'obiettivo è permettere all'utente di interagire con PrusaSlicer e risorse di rete locale usando comandi vocali in linguaggio naturale (italiano).

L'assistente, chiamato "Arturo", utilizza:
* **RealtimeSTT (con faster_whisper):** Per la trascrizione da parlato a testo (Speech-to-Text), con accelerazione GPU se disponibile.
* **Google Gemini API (gemini-1.5-flash-latest):** Per la comprensione del linguaggio naturale (NLU), la gestione della conversazione e la decisione di chiamare funzioni specifiche (tools).
* **PrusaSlicer Command Line:** Per eseguire materialmente le operazioni di slicing.
* **Python:** Come linguaggio di programmazione principale, con librerie come `pygame` per l'audio (input), `python-dotenv` per la configurazione, `requests` per chiamate HTTP, `markdownify` per conversione HTML, e `subprocess` per lanciare PrusaSlicer.
* **NOTA TTS:** Attualmente, le funzionalità Text-to-Speech (risposte vocali di Arturo) sono **disabilitate** a seguito della transizione a Gemini API. L'assistente fornirà risposte testuali.

## Funzionalità Chiave Implementate

* **Attivazione Vocale:** Risponde alla hotword "Arturo".
* **Riconoscimento Vocale in Italiano:** Trasforma i comandi vocali in testo.
* **Comprensione del Linguaggio Naturale (via Gemini):** Interpreta le richieste dell'utente.
* **Interazione con PrusaSlicer CLI:**
    * **Elenco File:** Può elencare i file `.stl`, `.3mf`, `.obj` da una cartella predefinita.
    * **Slicing Modelli:** Può avviare lo slicing di un file specificato e generare il G-code.
    * **Tentativo di Correzione Z=0:** Correzione automatica per l'errore "no extrusions in the first layer".
* **Interazione con Risorse di Rete Locale (Nuova Funzionalità):**
    * Utilizza la funzione `fetch_local_url_content` per recuperare contenuti testuali da URL sulla rete locale (es. stato stampante da OctoPrint, documentazione locale).
* **Configurazione Tramite `.env`:** Gestione sicura di API key e percorsi.
* **Gestione Preferenze:** Capacità di caricare, salvare e impostare preferenze di base.
* **Integrazione OctoPrint:** Funzionalità di base per listare file, profili, avviare stampe e slicing tramite OctoPrint (utilizzando anche la nuova capacità di fetch URL per alcuni aspetti).

## Setup e Installazione

1.  **Clona il Repository**
2.  **Crea un Ambiente Virtuale Python:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Su Linux/macOS
    .venv/bin/activate    # Su Windows
    ```
3.  **Installa le Dipendenze:**
    ```bash
    pip install -r requirements.txt
    ```
    (Assicurati che `requirements.txt` ora includa `google-generativeai`, `requests`, `markdownify`, `RealtimeSTT`, `faster_whisper`, `pygame`, `python-dotenv`, `rich` e `PyTorch` con supporto CUDA se usi la GPU).
4.  **Configura PrusaSlicer:** Assicurati che PrusaSlicer sia installato.
5.  **Configura Google Cloud e Gemini API:**
    *   Abilita la Gemini API nel tuo progetto Google Cloud.
    *   Assicurati di esserti autenticato tramite `gcloud auth application-default login` o imposta la variabile d'ambiente `GOOGLE_APPLICATION_CREDENTIALS`. In alternativa, puoi configurare la API key direttamente nel codice (non raccomandato per la sicurezza) o tramite la variabile `GEMINI_API_KEY` (se il codice in `assist.py` viene adattato per usarla esplicitamente con `genai.configure()`).
6.  **Crea e Configura il File `.env`:**
    Crea un file `.env` nella directory principale con le seguenti variabili:
    ```dotenv
    # GEMINI_API_KEY="la_tua_chiave_api_gemini" # Opzionale, vedi punto sopra
    PRUSA_SLICER_PATH="C:/Percorso/Completo/A/prusa-slicer-console.exe"
    STL_DEFAULT_FOLDER="C:/Percorso/Alla/Tua/Cartella/STL"
    # OCTOPRINT_URL e OCTOPRINT_API_KEY se si usa l'integrazione OctoPrint
    ```
7.  **(Opzionale) Configura GPU per Whisper.**

## Utilizzo

Esegui lo script `ai-slicer.py`:
```bash
python ai-slicer.py
```
Attendi il saluto testuale "Ciao, sono Arturo. In cosa posso aiutarti?" e poi interagisci usando la hotword "Arturo" (per input vocale) o digitando direttamente se la modalità silenziosa è attiva o l'input vocale non è configurato. Ricorda che le risposte di Arturo saranno testuali.

**Comandi Esempio:**
* "Arturo, elenca i file."
* "Arturo, processa il file CUBO.stl."
* "Arturo, qual è lo stato della stampante su http://octoprint.local/api/job?" (esempio per la nuova funzione)

## Struttura del Progetto (File Principali)

* `ai-slicer.py`: Script principale.
* `assist.py`: Gestisce la comunicazione con l'API di **Google Gemini**, la cronologia della conversazione e la mappatura delle function calls (ora definite programmaticamente).
* `tools.py`: Contiene l'implementazione Python delle funzioni che l'AI può chiamare (incl. `fetch_local_url_content`).
* `shared_variables.py`: Gestisce variabili condivise tra thread.
* `.env`: File di configurazione.
* `preferences.json`: File per salvare le preferenze utente.
* `requirements.txt`: Elenco delle dipendenze Python.
*  `3D_objects`: Cartella di default per i modelli 3D.

## Punti Chiave Discussi e Modifiche Apportate (Recenti)

* **Migrazione da OpenAI a Google Gemini API.**
* **Aggiunta Funzionalità "Browser as a Tool":** `fetch_local_url_content` per accedere a URL locali.
* **Disabilitazione Temporanea TTS:** Le risposte vocali di Arturo sono momentaneamente sospese.
* **Aggiornamento Dipendenze e Configurazione API.**

## Roadmap

Per le idee di sviluppo futuro e la roadmap dettagliata del progetto, si veda il file [ROADMAP.md](ROADMAP.md). (Considerare di aggiungere il ripristino di TTS alla roadmap).
