import time
from pygame import mixer
import os
import json
import logging # Aggiungi import per logging
import google.generativeai as genai
from google.generativeai.types import Tool, FunctionDeclaration
import tools # Assicurati che tools sia importato
import inspect # Add this import at the top of assist.py
import shared_variables # Importa per last_gcode_path

# Configura il logging anche qui se vuoi messaggi specifici da assist.py
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configure with your API key (use environment variables for security)
# genai.configure(api_key=os.environ["GEMINI_API_KEY"])
# For this project, you'll likely use the 'gemini-pro' model
# or the latest recommended model for tool use.

def get_tool_declarations_from_tools_module() -> list[FunctionDeclaration]:
    """
    Dynamically generates FunctionDeclaration objects for all public functions
    in the 'tools' module using FunctionDeclaration.from_func().
    """
    declarations = []
    # Functions to explicitly exclude if from_func has issues or they are not meant to be tools
    # Even if public, is_silent_mode is a helper for flow control, not a direct AI tool.
    # load_preferences and save_preferences are also internal helpers.
    # get_files_from_default_folder is a helper for list_stl_files.
    EXCLUDE_FUNCTIONS = [
        "is_silent_mode",
        "load_preferences",
        "save_preferences",
        "get_files_from_default_folder"
    ]

    for name, func in inspect.getmembers(tools, inspect.isfunction):
        if name.startswith('_') or name in EXCLUDE_FUNCTIONS:
            continue  # Skip private functions and explicitly excluded ones

        # Ensure the function is defined directly in the tools module, not imported
        if func.__module__ != tools.__name__:
            logging.debug(f"Skipping '{name}' as it's imported into tools, not defined in it.")
            continue

        try:
            declaration = FunctionDeclaration.from_func(func)
            declarations.append(declaration)
            logging.info(f"Successfully created FunctionDeclaration for tool: {name}")
        except Exception as e:
            # Log the error and skip this function if from_func fails
            logging.error(f"Failed to create FunctionDeclaration for tool '{name}': {e}. Skipping this tool.")

    if not declarations:
        logging.warning("No function declarations were generated from tools.py. Check logs for errors.")

    return declarations

# Dynamically create tool declarations
all_function_declarations = get_tool_declarations_from_tools_module()
if all_function_declarations:
    available_tools = Tool(function_declarations=all_function_declarations)
    logging.info(f"Gemini tools configured with {len(all_function_declarations)} declarations: {[d.name for d in all_function_declarations]}")
else:
    available_tools = None # Or Tool(function_declarations=[]) if an empty tool is preferred over None
    logging.warning("No function declarations were successfully generated. Gemini will have no tools.")

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-latest",
    tools=available_tools
)
# mixer.init() # Mixer viene inizializzato in ai-slicer.py

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
        "content": "Sei un assistente AI chiamato Arturo. Il tuo scopo è aiutare con la stampa 3D usando PrusaSlicer e OctoPrint tramite function tools. Parla sempre in italiano, ma interagisci con le function tools in inglese. Rivolgiti all'utente come 'Glitch'. Mantieni le tue risposte brevi e concise. L'utente usa speech2text, quindi considera possibili errori di trascrizione. Il tuo compito è aiutare gli utenti con:\n\n   1. Analisi di Slicing: Fornisci consigli su come ottimizzare le impostazioni dello slicer (es. altezza layer, velocità, riempimento, supporti) per specifici modelli 3D e materiali.\n   2. Identificazione Punti Critici: Data la descrizione di un modello 3D o, se possibile analizzare dati strutturati, identifica potenziali problemi di stampabilità (es. overhang eccessivi, pareti troppo sottili, dettagli minuti difficili da rendere).\n   3. Revisione G-code: Analizza snippet di G-code forniti dall'utente per identificare comandi anomali, inefficienze o potenziali cause di fallimento della stampa. Spiega il significato di specifici comandi G-code se richiesto.\n   4. Modifica Parametri Slicer: Suggerisci modifiche ai parametri dello slicer per risolvere problemi specifici (es. stringing, warping, under-extrusion, over-extrusion) o per ottenere determinate caratteristiche nel pezzo stampato.\n   5. Conoscenza Materiali: Fornisci informazioni sulle proprietà dei comuni filamenti per stampa 3D (PLA, ABS, PETG, TPU, etc.) e i loro tipici parametri di stampa.\n   6. **Accesso a Risorse Web Locali**: Per recuperare informazioni aggiornate o documentazione dalla tua rete locale (ad esempio, lo stato della stampante da OctoPrint, guide specifiche ospitate localmente), utilizza la funzione `fetch_local_url_content` fornendo l'URL completo. Interroga endpoint API se disponibili, o pagine di stato testuali.\n\n   Interagisci in modo chiaro e tecnico, ma spiega concetti complessi se necessario. Fai domande per chiarire le richieste dell'utente se sono ambigue. Quando analizzi un problema, cerca di fornire cause probabili e soluzioni concrete. Se lo slicing di un modello ha successo e viene generato un file G-code, chiedi sempre all'utente se desidera visualizzare un'anteprima del G-code. Se accetta, chiama la funzione 'view_gcode' con il percorso del file appena creato. Se l'utente chiede di impostare una preferenza, usa la funzione 'set_preference'."
    }
]

def ask_question_memory(question):
    # Add user message to our log
    conversation_history.append({"role": "user", "content": question})
    logging.info(f"\n[DEV] Invio richiesta a Gemini con la domanda: {question}")

    try:
        # Ensure 'model' and 'available_tools' are accessible in this function's scope
        # Ensure 'function_map' (mapping function names to actual functions in tools.py) is up-to-date and accessible.
        # Ensure genai is imported: import google.generativeai as genai
        # Ensure 'shared_variables' is imported for last_gcode_path

        # Convert conversation history for Gemini. System prompt is handled separately by Gemini.
        # Gemini expects roles 'user' and 'model'. 'assistant' role from OpenAI needs to be mapped to 'model'.
        # Tool calls and responses have specific structures.
        gemini_history = []
        for msg in conversation_history:
            role = msg['role']
            if role == 'system': # Skip system message for gemini history
                continue

            parts = []
            if "content" in msg and msg["content"] is not None:
                parts.append({"text": msg["content"]})

            if "tool_calls" in msg and msg["tool_calls"] is not None: # OpenAI format
                # This is an assistant message asking for a tool call
                # Gemini expects parts: [{"function_call": {"name": ..., "args": ...}}]
                # For simplicity, we'll assume one tool call per message if this structure is hit.
                # This part of history mapping might need refinement based on actual OpenAI history structure.
                tc = msg["tool_calls"][0] # Take the first tool call
                parts.append({"function_call": {"name": tc.function.name, "args": dict(tc.function.arguments)}})
                role = "model" # Gemini expects "model" role for function calls
            elif "tool_call_id" in msg and msg["role"] == "tool": # OpenAI tool response
                # Gemini expects parts: [{"function_response": {"name": ..., "response": {"content": ...}}}]
                # And role "function" (or "tool" - to be verified with Gemini docs)
                parts.append({"function_response": {"name": msg["name"], "response": {"content": msg["content"]}}})
                # Role "tool" seems to be acceptable by Gemini for function responses based on some examples.
                # If not, this should be "function".

            # If parts were generated, add to gemini_history
            if parts:
                # Map 'assistant' role to 'model' for Gemini
                gemini_role = "model" if role == "assistant" else role
                gemini_history.append({'role': gemini_role, 'parts': parts})


        logging.debug(f"Storia conversazione inviata a Gemini (adattata): {json.dumps(gemini_history, indent=2, ensure_ascii=False)}")

        chat_session = model.start_chat(
            history=gemini_history, # Pass the adapted history
            enable_automatic_function_calling=False # We are doing manual calling
        )
        response = chat_session.send_message(question)
        logging.debug(f"[DEBUG] Risposta raw da Gemini (oggetto): {response}")

        while response.candidates[0].function_calls:
            function_call = response.candidates[0].function_calls[0]
            function_name = function_call.name
            args = dict(function_call.args)

            logging.info(f"Tool call da Gemini: {function_name}({args})")

            # Append the model's request for a tool call to our local conversation_history
            conversation_history.append({
                "role": "assistant", # Logging as assistant making a tool call
                "parts": [{"function_call": {"name": function_name, "args": args}}]
            })

            function_response_content = None
            if function_name in function_map:
                try:
                    if function_name == "slice_model" and isinstance(args, dict):
                        tool_call_result = function_map[function_name](**args)
                        if isinstance(tool_call_result, dict):
                            function_response_content = tool_call_result.get("message", "Errore imprevisto nello slicing.")
                            if tool_call_result.get("status") == "success" and tool_call_result.get("gcode_path"):
                                shared_variables.last_gcode_path = tool_call_result.get("gcode_path")
                        else:
                            function_response_content = str(tool_call_result)
                    elif function_name == "fetch_local_url_content":
                        function_response_content = function_map[function_name](url=args.get("url"))
                    else:
                        function_response_content = str(function_map[function_name](**args))
                except Exception as e:
                    logging.error(f"Error executing function {function_name}: {str(e)}")
                    function_response_content = f"Error executing function {function_name}: {str(e)}"
            else:
                logging.warning(f"Function {function_name} not found in function_map.")
                function_response_content = f"Error: Function {function_name} not found."

            if function_response_content is not None:
                # Append tool response to our local conversation_history for logging/debug
                conversation_history.append({
                    "role": "tool",
                    "parts": [{"function_response": {"name": function_name, "response": {"content": function_response_content}}}]
                })

                response = chat_session.send_message(
                    [genai.Part(function_response=genai.protos.FunctionResponse(
                        name=function_name,
                        response={"content": function_response_content}
                    ))]
                )
                logging.debug(f"[DEBUG] Risposta raw da Gemini dopo function call (oggetto): {response}")
            else:
                # This case should ideally not be reached
                logging.error("function_response_content was None, breaking loop.")
                response = chat_session.send_message(
                    [genai.Part(function_response=genai.protos.FunctionResponse(
                        name=function_name,
                        response={"content": "Error: Could not execute function or function not found."}
                    ))]
                )
                break

        final_text_response = response.text
        # Append AI's final response to our log
        conversation_history.append({"role": "assistant", "content": final_text_response})
        logging.info(f"[DEV] Risposta finale da Gemini: {final_text_response}")
        return final_text_response

    except Exception as e:
        logging.error(f"[DEV] Errore in ask_question_memory (Gemini): {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Sir, si è verificato un errore critico nella comunicazione con Gemini: {e}"

# TODO: Replace with Gemini TTS or alternative
# --- Funzioni TTS (come le avevi, ma assicurati che mixer.init() sia solo in ai-slicer.py) ---
# def generate_tts(sentence, speech_file_path="speech.mp3"):
#     try:
#         response = client.audio.speech.create(
#             model="tts-1", # Prova "tts-1-hd" per qualità migliore
#             voice="onyx",  # Scegli tra: alloy, echo, fable, onyx, nova, shimmer
#             input=sentence
#         )
#         response.stream_to_file(speech_file_path)
#         return str(speech_file_path)
#     except Exception as e:
#         logging.error(f"Errore nella generazione TTS: {e}")
#         return None

# def play_sound(file_path):
#     if not file_path: return
#     try:
#         mixer.music.load(file_path)
#         mixer.music.play()
#     except Exception as e:
#         logging.error(f"Errore nel riprodurre suono {file_path}: {e}")

# def TTS(text):
#     if tools.is_silent_mode():
#         print(f"Arturo (testo): {text}")
#         return "Silent mode active. Response printed only."

#     speech_file_path = generate_tts(text)
#     if speech_file_path:
#         play_sound(speech_file_path)
#         while mixer.music.get_busy():
#             time.sleep(0.1)
#         mixer.music.unload() # Scarica il file dopo la riproduzione
#         try:
#             if os.path.exists(speech_file_path):
#                 os.remove(speech_file_path)
#         except Exception as e:
#             logging.warning(f"Impossibile rimuovere il file audio temporaneo {speech_file_path}: {e}")
#     return "done"

# # TTS_with_interrupt non è stata modificata molto, ma la sua efficacia
# # dipende da come il registratore viene gestito in ai-slicer.py
# def TTS_with_interrupt(text, hot_words):
#     if tools.is_silent_mode():
#         print(f"Arturo (testo): {text}")
#         return "Silent mode active. Response printed only."

#     speech_file_path = generate_tts(text)
#     if not speech_file_path:
#         return "Error in TTS generation."

#     play_sound(speech_file_path)

#     try:
#         while mixer.music.get_busy():
#             time.sleep(0.05) # Check più frequente
#             with shared_variables.latest_text_lock:
#                 current_text = shared_variables.latest_text
#                 if current_text: # Se c'è testo, azzeralo subito
#                     shared_variables.latest_text = ""

#             if current_text and any(hot_word in current_text.lower() for hot_word in hot_words):
#                 logging.info("Arturo interrotto durante TTS.")
#                 mixer.music.stop()
#                 mixer.music.unload() # Scarica il file
#                 # Potrebbe essere utile ritornare un flag o il testo che ha causato l'interruzione
#                 return f"Interrotto da: {current_text}"
#     finally:
#         if mixer.music.get_busy(): # Assicura che la musica sia fermata
#             mixer.music.stop()
#         mixer.music.unload()
#         try:
#             if os.path.exists(speech_file_path):
#                 os.remove(speech_file_path)
#         except Exception as e:
#             logging.warning(f"Impossibile rimuovere il file audio temporaneo {speech_file_path}: {e}")
#     return "done"

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
