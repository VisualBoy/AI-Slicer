from RealtimeSTT import AudioToTextRecorder
import assist # Il tuo modulo per le chiamate OpenAI e TTS
import tools  # Il tuo modulo per le funzioni (is_silent_mode, ecc.)
import time
import threading
from pygame import mixer
import shared_variables # Per latest_text e lock
import os
from dotenv import load_dotenv, find_dotenv

# --- Debug Iniziale per .env ---
print("[DEBUG] Cerco il file .env...")
env_path = find_dotenv()
print(f"[DEBUG] Percorso .env trovato: {env_path}")

loaded = load_dotenv(env_path)
print(f"[DEBUG] .env caricato con successo? {loaded}")

stl_folder_check = os.getenv("STL_DEFAULT_FOLDER")
print(f"[DEBUG] Valore di STL_DEFAULT_FOLDER (all'avvio): {stl_folder_check}")
# --- Fine Debug Iniziale ---

def listen_thread(recorder_instance): # Rinominato 'recorder' a 'recorder_instance' per evitare shadowing
    """Thread che ascolta continuamente e aggiorna latest_text."""
    while True:
        text = recorder_instance.text()
        with shared_variables.latest_text_lock:
            shared_variables.latest_text = text

if __name__ == '__main__':
    mixer.init()  # Inizializza mixer per la riproduzione audio

    recorder = AudioToTextRecorder(
        spinner=False,
        model="large-v3-turbo", # o "large-v3-turbo" se esiste e funziona meglio per te
        language="it",
        post_speech_silence_duration=0.75,
        silero_sensitivity=0.4,
        device="cuda",
        compute_type="float16"
    )
    
    hot_words = ["arturo"] # La tua hotword
    expecting_user_response = False # Flag per sapere se l'AI ha appena fatto una domanda
    last_tts_end_time = 0.0 # Timestamp per la gestione dell'eco

    # Saluto vocale all'avvio
    initial_greeting = "Ciao, sono Arturo. In cosa posso aiutarla?"
    print(initial_greeting)
    if not tools.is_silent_mode(): # Controlla se non siamo in silent mode prima di parlare
        assist.TTS(initial_greeting)
        last_tts_end_time = time.time() # Imposta il timestamp dopo il saluto iniziale

    # Avvia il registratore se non siamo in silent mode
    if not tools.is_silent_mode() and not recorder.is_recording:
        print("[DEBUG] Avvio registratore all'inizio...")
        recorder.start()

    # Avvia il thread di ascolto
    listener = threading.Thread(target=listen_thread, args=(recorder,), daemon=True)
    listener.start()

    print("Ti ascolto...") # Modificato da "Say something..."

    try:
        while True:
            if tools.is_silent_mode():
                if recorder.is_recording:
                    print("[DEBUG] Modalità silenziosa: fermo il registratore.")
                    recorder.stop()
                
                user_input = input("Tu (testo): ")
                if user_input.lower() == 'exit': # Permetti di uscire
                    break
                
                # Per la modalità testo, non aggiungiamo timestamp, gestiamo direttamente
                response = assist.ask_question_memory(user_input) 
                print("Arturo:", response) # Nome dell'AI aggiornato
                
                # Se la risposta disabilita il silent mode, l'utente dovrà riavviare la registrazione audio
                # o noi dobbiamo gestirlo qui. Per ora, lasciamo che il prossimo ciclo gestisca la ripartenza.
                if "silent mode disabled" in response.lower() and not recorder.is_recording:
                    print("[DEBUG] Modalità silenziosa disabilitata. Riattivo l'ascolto vocale al prossimo ciclo.")
                continue # Salta il resto del loop per la modalità vocale

            else: # Modalità Vocale
                if not recorder.is_recording:
                    print("[DEBUG] Modalità vocale: avvio il registratore.")
                    recorder.start()
                    print("Ti ascolto...")


            time.sleep(0.1) # Breve pausa per non sovraccaricare la CPU
            current_text = ""
            with shared_variables.latest_text_lock:
                current_text = shared_variables.latest_text
                shared_variables.latest_text = "" # Resetta subito per non riprocessare

            if current_text:
                print("Utente:", current_text)

                # --- CONTROLLO ECO ---
                # Ignora il testo se è arrivato troppo presto dopo un TTS
                if (time.time() - last_tts_end_time) < 2.0: # 2 secondi di "zona di silenzio"
                    print("[DEBUG] Testo ignorato (probabile eco).")
                    current_text = "" # Azzera per non processarlo oltre
                # --- FINE CONTROLLO ECO ---

                if current_text: # Prosegui solo se il testo non è stato cancellato dal controllo eco
                    hotword_found = any(hot_word in current_text.lower() for hot_word in hot_words)
                    print(f"[SUPER DEBUG] Testo='{current_text.lower()}' | Hotwords={hot_words} | 'arturo' in Testo?={'arturo' in current_text.lower()} | Risultato Finale={hotword_found}")

                    # Interrompi il TTS se l'utente parla (e dice la hotword)
                    if mixer.music.get_busy() and hotword_found:
                        print("[DEBUG] Interruzione TTS richiesta dall'utente.")
                        mixer.music.stop()
                        # Potrebbe essere utile resettare 'expecting_user_response' qui se l'interruzione cambia il contesto
                        # expecting_user_response = False 
                        # current_text = "" # Pulisce il testo che ha causato l'interruzione per non processarlo come comando nuovo
                        # continue # Potrebbe essere utile saltare il resto dell'elaborazione di questo frammento

                    # Elaborazione Comando Principale
                    if hotword_found or expecting_user_response:
                        print("[DEBUG] Condizione per chiamare l'AI soddisfatta. Invio...")
                        
                        if recorder.is_recording:
                            print("[DEBUG] Metto in pausa il registratore per il TTS dell'AI...")
                            recorder.stop()
                        
                        response = assist.ask_question_memory(current_text + " " + time.strftime("%D:%H:%M:%S"))
                        print("Arturo:", response) # Nome dell'AI aggiornato

                        expecting_user_response = response.strip().endswith('?')

                        if not tools.is_silent_mode():
                            print("[DEBUG] Avvio TTS per la risposta di Arturo...")
                            assist.TTS(response) 
                            print("[DEBUG] TTS di Arturo completato.")
                            last_tts_end_time = time.time() # Aggiorna il timestamp
                            
                            # --- NUOVO: PAUSA DINAMICA ---
                            # Stima la durata: circa 0.065 secondi per carattere (da aggiustare)
                            # Minimo 0.5 secondi, massimo (es.) 10 secondi per evitare attese troppo lunghe
                            lunghezza_risposta = len(response)
                            pausa_stimata = min(max(0.5, lunghezza_risposta * 0.065), 10.0) 
                            print(f"[DEBUG] Pausa calcolata dopo TTS: {pausa_stimata:.2f}s (basata su {lunghezza_risposta} caratteri)")
                            time.sleep(pausa_stimata)
                            # --- FINE PAUSA DINAMICA ---
                        
                        if not recorder.is_recording and not tools.is_silent_mode():
                            print("[DEBUG] Riattivo il registratore...")
                            recorder.start()
                            print("Ti ascolto...")
                        
                        current_text = "" # Resetta per evitare riprocessamenti al ciclo successivo
                        continue 
                    else:
                        print("[DEBUG] Hotword non trovata e nessuna risposta attesa. Ignoro.")
            
            # Se non c'è testo e il mixer è fermo, ma il registratore era stato fermato per il TTS, riavvialo
            # Questo previene che il registratore resti spento se l'AI non risponde o non c'è TTS.
            if not current_text and not mixer.music.get_busy() and not recorder.is_recording and not tools.is_silent_mode():
                print("[DEBUG] Controllo di sicurezza: riattivo il registratore.")
                recorder.start()
                print("Ti ascolto...")


    except KeyboardInterrupt:
        print("\nArturo interrotto dall'utente.")
        if mixer.music.get_busy():
            mixer.music.stop()
        if recorder.is_recording:
            recorder.stop()
    finally:
        print("Uscita da Arturo.")
        if recorder.is_recording: # Assicurati che sia fermo anche all'uscita
            recorder.stop()