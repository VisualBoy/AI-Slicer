from RealtimeSTT import AudioToTextRecorder
import assist # Il tuo modulo per le chiamate OpenAI e TTS
import tools
import time
import threading
from pygame import mixer
import shared_variables # Per latest_text e lock
import os
from dotenv import load_dotenv, find_dotenv
from rich.console import Console 
from rich.spinner import Spinner
import logging 
from rich.logging import RichHandler # ADDED IMPORT FOR RICH LOGGING

# --- Debug Iniziale per .env ---
# These print statements will remain as they are, not converted to logging,
# as they are initial startup checks.
# print("[DEBUG] Cerco il file .env...")
env_path = find_dotenv()
# print(f"[DEBUG] Percorso .env trovato: {env_path}")

loaded = load_dotenv(env_path)
# print(f"[DEBUG] .env caricato con successo? {loaded}")

stl_folder_check = os.getenv("STL_DEFAULT_FOLDER")
# print(f"[DEBUG] Valore di STL_DEFAULT_FOLDER (all'avvio): {stl_folder_check}")
# --- Fine Debug Iniziale ---

console = Console() 

def listen_thread(recorder_instance): 
    """Thread che ascolta continuamente e aggiorna latest_text."""
    while True:
        text = recorder_instance.text()
        with shared_variables.latest_text_lock:
            shared_variables.latest_text = text

if __name__ == '__main__':
    # --- Configura Rich Logging ---
    logging.basicConfig(
        level=logging.DEBUG, # CHANGED to WARNING
        format="%(message)s", 
        datefmt="[%X]",
        handlers=[RichHandler(level=logging.DEBUG, rich_tracebacks=True, show_path=False, log_time_format="[%X]")] # MODIFIED Handler
    )
    # Silence specific noisy loggers
    logging.getLogger("faster_whisper").setLevel(logging.WARNING)
    logging.getLogger("RealtimeSTT").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("ctranslate2").setLevel(logging.WARNING)
    logging.getLogger("pkg_resources").setLevel(logging.ERROR)
    logging.getLogger("google.generativeai").setLevel(logging.INFO)
    logging.getLogger("genai").setLevel(logging.INFO)
    # --- Fine Configurazione Logging ----

    mixer.init()  

    recorder = AudioToTextRecorder(
        spinner=False,
        model="large-v3-turbo", 
        language="it",
        post_speech_silence_duration=0.75,
        silero_sensitivity=0.4,
        device="cuda",
        compute_type="float16"
    )
    
    hot_words = ["arturo", "artur", "vez","coglione","testa di cazzo","miserabile","scemo di merda","porco dio"] 
    expecting_user_response = False 
    last_tts_end_time = 0.0 

    initial_greeting = "Ciao vez, sono Arturo. In cosa posso aiutarti?"
    console.print(initial_greeting) 
    if not tools.is_silent_mode(): 
        # assist.TTS(initial_greeting) # TODO: Re-enable TTS when a Gemini-compatible solution is implemented
        last_tts_end_time = time.time() 

    if not tools.is_silent_mode() and not recorder.is_recording:
        # This specific print can be converted to logging.debug if preferred,
        # but the subtask specified modifying/adding basicConfig.
        # For now, keeping it as print to match original intent unless specified otherwise.
        # print("[DEBUG] Avvio registratore all'inizio...")
        recorder.start()

    listener = threading.Thread(target=listen_thread, args=(recorder,), daemon=True)
    listener.start()

    console.print("Ti ascolto...") 

    try:
        while True:
            if tools.is_silent_mode():
                if recorder.is_recording:
                    # Similar to above, this print can be logging.debug
                    # print("[DEBUG] Modalità silenziosa: fermo il registratore.")
                    recorder.stop()
                
                user_input = console.input("[b style='dark_cyan']Tu (testo):[/b style='dark_cyan'] ") # MODIFIED for color
                if user_input.lower() == 'exit': 
                    break
                
                with console.status(Spinner("dots", text=" Arturo sta pensando...")):
                    response = assist.ask_question_memory(user_input) 
                
                console.print(f"[b style='dark_orange']Arturo:[/b style='dark_orange'] [dark_orange]{response}[/dark_orange]") # MODIFIED for color
                
                if "silent mode disabled" in response.lower() and not recorder.is_recording:
                    # print("[DEBUG] Modalità silenziosa disabilitata. Riattivo l'ascolto vocale al prossimo ciclo.")
                    continue 

            else: # Modalità Vocale
                if not recorder.is_recording:
                    # print("[DEBUG] Modalità vocale: avvio il registratore.")
                    recorder.start()
                    console.print("Ti ascolto...") 


            time.sleep(0.5)
            text_from_stt = "" # Usa una variabile temporanea per chiarezza
            with shared_variables.latest_text_lock:
                text_from_stt = shared_variables.latest_text
                shared_variables.latest_text = "" # Svuota il buffer solo dopo aver letto il testo

            # Ora elabora il testo solo se non è vuoto
            if text_from_stt:
                console.print(f"[b style='dark_cyan']Utente:[/b style='dark_cyan'] [dark_cyan]{text_from_stt}[/dark_cyan]") # Stampa l'input dell'utente una volta qui

                # Modifica la condizione per l'eco se necessario
                if (time.time() - last_tts_end_time) < 0.5: # Ridotto a 0.5s, o rimuovi del tutto per test
                    logging.debug("[DEBUG] Testo ignorato (probabile eco).")
                    continue # Passa al prossimo ciclo se è eco

                # Assegna il testo elaborato per il resto della logica nel blocco corrente
                current_text_for_processing = text_from_stt # Usa un nome diverso per chiarezza, o semplicemente continua a usare text_from_stt

                # --- Inizio Blocco Logica di Elaborazione Testo (ora correttamente annidato) ---
                hotword_found = any(hot_word in current_text_for_processing.lower() for hot_word in hot_words)
                logging.debug(f"[SUPER DEBUG] Testo='{current_text_for_processing.lower()}' | Hotwords={hot_words} | 'arturo' in Testo?={'arturo' in current_text_for_processing.lower()} | Risultato Finale={hotword_found}")

                if mixer.music.get_busy() and hotword_found:
                    logging.debug("[DEBUG] Interruzione TTS richiesta dall'utente.")
                    mixer.music.stop()

                if hotword_found or expecting_user_response:
                    logging.debug("[DEBUG] Condizione per chiamare l'AI soddisfatta. Invio...")

                    if recorder.is_recording:
                        logging.debug("[DEBUG] Metto in pausa il registratore per il TTS dell'AI...")
                        recorder.stop()

                    with console.status(Spinner("dots", text=" Arturo sta pensando...")):
                        # Usa current_text_for_processing per la chiamata all'AI
                        response = assist.ask_question_memory(current_text_for_processing + " " + time.strftime("%D:%H:%M:%S"))

                    console.print(f"[b style='dark_orange']Arturo:[/b style='dark_orange'] [dark_orange]{response}[/dark_orange]")

                    expecting_user_response = response.strip().endswith('?')

                    if not tools.is_silent_mode():
                        # print("[DEBUG] Avvio TTS per la risposta di Arturo...") # TODO: Re-enable TTS
                        # assist.TTS(response) # TODO: Re-enable TTS
                        # print("[DEBUG] TTS di Arturo completato.")
                        last_tts_end_time = time.time()

                        lunghezza_risposta = len(response)
                        pausa_stimata = min(max(0.5, lunghezza_risposta * 0.065), 10.0)
                        logging.debug(f"[DEBUG] Pausa calcolata dopo TTS: {pausa_stimata:.2f}s (basata su {lunghezza_risposta} caratteri)")
                        time.sleep(pausa_stimata)

                    if not recorder.is_recording and not tools.is_silent_mode():
                        logging.debug("[DEBUG] Riattivo il registratore...")
                        recorder.start()
                        console.print("Ti ascolto...")

                    # Non svuotare current_text_for_processing qui, è una variabile locale al blocco if
                    continue # Passa al prossimo ciclo dopo aver elaborato l'input

                else:
                    logging.debug("[DEBUG] Hotword non trovata e nessuna risposta attesa. Ignoro.")
                    pass # Input ignorato, continua il loop

            # --- Fine Blocco Logica di Elaborazione Testo ---


            # Questo controllo di sicurezza ora non dipende da 'current_text'
            if not text_from_stt and not mixer.music.get_busy() and not recorder.is_recording and not tools.is_silent_mode():
                logging.debug("[DEBUG] Controllo di sicurezza: riattivo il registratore.")
                recorder.start()
                console.print("Ti ascolto...")




    except KeyboardInterrupt:
        console.print("\nArturo interrotto dall'utente.") 
        if mixer.music.get_busy():
            mixer.music.stop()
        if recorder.is_recording:
            recorder.stop()
    finally:
        console.print("Uscita da Arturo.") 
        if recorder.is_recording: 
            recorder.stop()
