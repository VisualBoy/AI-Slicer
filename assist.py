from openai import OpenAI
import time
from pygame import mixer
import os
import json
import logging # Aggiungi import per logging
import tools # Assicurati che tools sia importato
import shared_variables # Importa per last_gcode_path

# Configura il logging anche qui se vuoi messaggi specifici da assist.py
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# mixer.init() # Mixer viene inizializzato in ai-slicer.py

# Carica le funzioni e trasformale per l'API
try:
    with open('functions.json', 'r') as f:
        functions_list = json.load(f)['functions']
    openai_tools = [{"type": "function", "function": func} for func in functions_list]
    logging.info("Definizioni funzioni caricate e trasformate per OpenAI.")
except Exception as e:
    logging.error(f"Errore nel caricare functions.json: {e}")
    openai_tools = [] # Lista vuota per evitare crash se il file non esiste o è corrotto

function_map = {}
try:
    for func_name in dir(tools):
        if not func_name.startswith('_'):
            func = getattr(tools, func_name)
            if callable(func):
                function_map[func_name] = func
    logging.info(f"Function map creata: {list(function_map.keys())}")
except Exception as e:
    logging.error(f"Errore nel creare function_map: {e}")


conversation_history = [
    {
        "role": "system",
        "content": "Sei un assistente AI chiamato Arturo. Il tuo scopo è aiutare con la stampa 3D usando PrusaSlicer. Parla sempre in italiano. Rivolgiti all'utente come 'Glitch'. Mantieni le tue risposte brevi e concise. L'utente usa speech2text, quindi considera possibili errori di trascrizione. Se lo slicing di un modello ha successo e viene generato un file G-code, chiedi sempre all'utente se desidera visualizzare un'anteprima del G-code. Se accetta, chiama la funzione 'view_gcode' con il percorso del file appena creato. Se l'utente chiede di impostare una preferenza, usa la funzione 'set_preference'."
    }
]

def ask_question_memory(question):
    # Aggiungi il messaggio dell'utente (questo è già corretto)
    conversation_history.append({"role": "user", "content": question})
    logging.info(f"\n[DEV] Invio richiesta a OpenAI con la domanda: {question}")
    
    # Debug della cronologia PRIMA della chiamata API
    try:
        # Per il debug, serializziamo solo i campi noti e sicuri
        serializable_history = []
        for msg in conversation_history:
            item = {"role": msg.get("role"), "content": msg.get("content")}
            if msg.get("tool_calls"): # Aggiungi se presente
                item["tool_calls"] = [{"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in msg.get("tool_calls")]
            if msg.get("tool_call_id"): # Aggiungi se presente (per ruolo 'tool')
                item["tool_call_id"] = msg.get("tool_call_id")
                item["name"] = msg.get("name")
            serializable_history.append(item)
        logging.debug(f"Cronologia conversazione inviata (forma serializzabile): {json.dumps(serializable_history, indent=2, ensure_ascii=False)}")
    except Exception as e_json:
        logging.error(f"Errore nella serializzazione JSON della cronologia per debug: {e_json}")


    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation_history, # Invia la cronologia originale
            tools=openai_tools,
            tool_choice="auto",
            temperature=0.5,
            max_tokens=4096
        )

        message_from_ai = response.choices[0].message # Questo è un ChatCompletionMessage
        logging.debug(f"[DEBUG] Risposta raw da OpenAI (oggetto): {message_from_ai}")

        # Prepara il messaggio da aggiungere alla cronologia
        message_to_add_to_history = {"role": "assistant", "content": message_from_ai.content}

        tool_calls = message_from_ai.tool_calls

        if tool_calls:
            logging.info(f"[DEBUG] OpenAI ha deciso di chiamare {len(tool_calls)} funzione/i.")
            # Aggiungi i tool_calls al messaggio che verrà storicizzato
            message_to_add_to_history["tool_calls"] = message_from_ai.tool_calls # L'API history accetta l'oggetto tool_calls
            conversation_history.append(message_to_add_to_history) # Aggiungi la risposta dell'AI che richiede il tool

            ai_response_content_after_tool = "Ok, Glitch." 

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args_str = tool_call.function.arguments
                logging.info(f"[DEBUG] Chiamo: {function_name} con args: {function_args_str}")
                
                tool_result_content = ""
                # ... (logica per chiamare la funzione e ottenere tool_result_content) ...
                try:
                    function_args = json.loads(function_args_str)
                    if function_name in function_map:
                        tool_call_result = function_map[function_name](**function_args)
                        # ... (gestione di tool_call_result come prima) ...
                        if function_name == "slice_model" and isinstance(tool_call_result, dict):
                            tool_result_content = tool_call_result.get("message", "Errore imprevisto nello slicing.")
                            if tool_call_result.get("status") == "success" and tool_call_result.get("gcode_path"):
                                shared_variables.last_gcode_path = tool_call_result.get("gcode_path")
                        # ... (altri 'elif' per altre funzioni se necessario) ...
                        else:
                            tool_result_content = str(tool_call_result)
                    else:
                        tool_result_content = f"Funzione {function_name} non trovata"
                except Exception as func_err:
                    # ... (gestione errore funzione) ...
                    tool_result_content = f"Errore nell'eseguire {function_name}: {func_err}"


                conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": tool_result_content
                })

            logging.info("[DEV] Ottengo risposta finale dopo la chiamata funzione...")
            final_response_after_tool = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=conversation_history, # Invia la cronologia aggiornata
                temperature=0.5,
                max_tokens=1024
            )
            ai_response_content_after_tool = final_response_after_tool.choices[0].message.content
            
            if not ai_response_content_after_tool:
                ai_response_content_after_tool = "Ok, Glitch, fatto."
            
            # Aggiungi la risposta finale dell'assistente alla cronologia
            conversation_history.append({"role": "assistant", "content": ai_response_content_after_tool})
            return ai_response_content_after_tool

        else:
            # Nessuna chiamata a funzione
            logging.info("[DEBUG] OpenAI non ha richiesto una function call.")
            ai_response_content = message_from_ai.content
            if not ai_response_content: 
                 ai_response_content = "Certamente, Sir. C'è altro?"
            
            # Aggiungi la risposta dell'AI alla cronologia (come dizionario)
            conversation_history.append(message_to_add_to_history) # Usa message_to_add_to_history che è già un dizionario
            return ai_response_content

    except Exception as e:
        logging.error(f"[DEV] Errore in ask_question_memory: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Sir, si è verificato un errore critico nella comunicazione con l'AI: {e}"


# --- Funzioni TTS (come le avevi, ma assicurati che mixer.init() sia solo in ai-slicer.py) ---
def generate_tts(sentence, speech_file_path="speech.mp3"):
    try:
        response = client.audio.speech.create(
            model="tts-1", # Prova "tts-1-hd" per qualità migliore
            voice="onyx",  # Scegli tra: alloy, echo, fable, onyx, nova, shimmer
            input=sentence
        )
        response.stream_to_file(speech_file_path)
        return str(speech_file_path)
    except Exception as e:
        logging.error(f"Errore nella generazione TTS: {e}")
        return None

def play_sound(file_path):
    if not file_path: return
    try:
        mixer.music.load(file_path)
        mixer.music.play()
    except Exception as e:
        logging.error(f"Errore nel riprodurre suono {file_path}: {e}")

def TTS(text):
    if tools.is_silent_mode():
        print(f"Arturo (testo): {text}") 
        return "Silent mode active. Response printed only."
    
    speech_file_path = generate_tts(text)
    if speech_file_path:
        play_sound(speech_file_path)
        while mixer.music.get_busy():
            time.sleep(0.1)
        mixer.music.unload() # Scarica il file dopo la riproduzione
        try:
            if os.path.exists(speech_file_path):
                os.remove(speech_file_path)
        except Exception as e:
            logging.warning(f"Impossibile rimuovere il file audio temporaneo {speech_file_path}: {e}")
    return "done"

# TTS_with_interrupt non è stata modificata molto, ma la sua efficacia
# dipende da come il registratore viene gestito in ai-slicer.py
def TTS_with_interrupt(text, hot_words):
    if tools.is_silent_mode():
        print(f"Arturo (testo): {text}")
        return "Silent mode active. Response printed only."

    speech_file_path = generate_tts(text)
    if not speech_file_path:
        return "Error in TTS generation."
        
    play_sound(speech_file_path)

    try:
        while mixer.music.get_busy():
            time.sleep(0.05) # Check più frequente
            with shared_variables.latest_text_lock:
                current_text = shared_variables.latest_text
                if current_text: # Se c'è testo, azzeralo subito
                    shared_variables.latest_text = ""
            
            if current_text and any(hot_word in current_text.lower() for hot_word in hot_words):
                logging.info("Arturo interrotto durante TTS.")
                mixer.music.stop()
                mixer.music.unload() # Scarica il file
                # Potrebbe essere utile ritornare un flag o il testo che ha causato l'interruzione
                return f"Interrotto da: {current_text}"
    finally:
        if mixer.music.get_busy(): # Assicura che la musica sia fermata
            mixer.music.stop()
        mixer.music.unload()
        try:
            if os.path.exists(speech_file_path):
                os.remove(speech_file_path)
        except Exception as e:
            logging.warning(f"Impossibile rimuovere il file audio temporaneo {speech_file_path}: {e}")
    return "done"

if __name__ == "__main__": # Per testare assist.py separatamente
    mixer.init() # Necessario per testare TTS
    # tools._silent_mode = False # Per testare TTS
    
    # Test TTS
    # print("Testo TTS: 'Ciao, questo è un test.'")
    # TTS("Ciao, questo è un test.")

    # Test ask_question_memory (richiede functions.json e tools.py configurati)
    # print("\nTest di ask_question_memory:")
    # response = ask_question_memory("elenca i file")
    # print("Risposta AI:", response)
    # if not tools.is_silent_mode(): TTS(response)

    # response = ask_question_memory("processa il file numero 1")
    # print("Risposta AI:", response)
    # if not tools.is_silent_mode(): TTS(response)
    pass # Lascia vuoto o aggiungi test specifici per assist.py