from openai import OpenAI
import time
from pygame import mixer
import os
import json
import threading
import tools
import shared_variables

# Initialize OpenAI with the API Key from your env variables
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
mixer.init()

# Carica le funzioni
with open('functions.json', 'r') as f:
    functions_list = json.load(f)['functions']

# Aggiungi questa riga per trasformare la lista per l'API
openai_tools = [{"type": "function", "function": func} for func in functions_list]

function_map = {}
for func_name in dir(tools):
    if not func_name.startswith('_'):
        func = getattr(tools, func_name)
        if callable(func):
            function_map[func_name] = func

# Conversation history
conversation_history = [
    {
        "role": "system",
        "content": "Sei un assistente AI chiamato Arturo. Il tuo scopo è aiutare con la stampa 3D usando PrusaSlicer. Parla sempre in italiano. Rivolgiti all'utente come 'Glitch'. Mantieni le tue risposte brevi e concise, se possibile. L'utente utilizza un sistema di speech2text per interagire, tienine conto se noti eventuali errori nelle risposte."
    }
]

def ask_question_memory(question):
    """
    Processes a user's question, updates conversation history,
    handles tool calls, and fetches a response from OpenAI.
    """
    conversation_history.append({"role": "user", "content": question})
    print("\n[DEV] Sending request to OpenAI...")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation_history,
            tools=openai_tools,  # Usa 'tools' invece di 'functions'
            tool_choice="auto", # Usa 'tool_choice' invece di 'function_call'
            temperature=0.5,
            max_tokens=4096
        )

        message = response.choices[0].message
        print(f"[DEBUG] Risposta raw da OpenAI: {message}") # <-- Corretto! Usa 'message'

        tool_calls = message.tool_calls # <-- Usa 'message.tool_calls'

        if tool_calls:
            print(f"[DEBUG] OpenAI ha deciso di chiamare {len(tool_calls)} funzione/i.")
            conversation_history.append(message) # Aggiungi la risposta con la richiesta del tool

            # Esegui tutte le chiamate richieste
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args_str = tool_call.function.arguments
                print(f"[DEBUG] Chiamo: {function_name} con args: {function_args_str}")

                try:
                    function_args = json.loads(function_args_str)
                    if function_name in function_map:
                        result = function_map[function_name](**function_args)
                        print(f"[DEV] Function result: {result}")
                    else:
                        result = f"Function {function_name} not found"
                except Exception as func_err:
                    print(f"[DEV] Error calling function {function_name}: {func_err}")
                    result = f"Error executing {function_name}: {func_err}"

                # Aggiungi il risultato della funzione alla cronologia
                conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": str(result)
                })

            # Richiama OpenAI per ottenere una risposta in linguaggio naturale basata sul risultato
            print("[DEV] Getting final response after function call...")
            final_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=conversation_history,
                temperature=0.5,
                max_tokens=4096
            )
            ai_response = final_response.choices[0].message.content
            conversation_history.append({"role": "assistant", "content": ai_response}) # Aggiungi risposta finale
            return ai_response

        else:
            # Nessuna chiamata a funzione, è una risposta normale
            print("[DEBUG] OpenAI non ha richiesto una function call.")
            ai_response = message.content
            if not ai_response: # Gestisce risposte vuote
                 ai_response = "Certamente, Sir. C'è altro?"
            conversation_history.append(message) # Aggiungi la risposta dell'AI
            return ai_response

    except Exception as e:
        print(f"[DEV] Error occurred: {str(e)}")
        import traceback
        traceback.print_exc() # Stampa più dettagli sull'errore
        return f"Sir, si è verificato un errore critico: {e}"
		
# From here on and below it's all TTS settings
def generate_tts(sentence, speech_file_path):
    """
    Generates Text-to-Speech audio and saves it to a file.
    """
    response = client.audio.speech.create(
        model="tts-1-hd",      # Prova anche "tts-1-hd"
        voice="onyx",       # <--- Esempio: voce cambiata in "onyx"
        input=sentence,
        language="it"     # Opzionale, se vuoi forzare l'italiano per il TTS
    )
    response.stream_to_file(speech_file_path)
    return str(speech_file_path)

def play_sound(file_path):
    """
    Plays the given audio file using the mixer module.
    """
    mixer.music.load(file_path)
    mixer.music.play()

def TTS(text):
    """
    Plays the Text-to-Speech response unless Silent Mode is active.
    """
    if tools.is_silent_mode():
        print(f"Arturo: {text}")  # Print response instead of speaking
        return "Silent mode active. Response printed only."
    speech_file_path = generate_tts(text, "speech.mp3")
    play_sound(speech_file_path)
    while mixer.music.get_busy():
        time.sleep(0.1)
    mixer.music.unload()
    if os.path.exists(speech_file_path):
        os.remove(speech_file_path)
    return "done"

def TTS_with_interrupt(text, hot_words):
    """
    Plays the response with interrupt handling during playback.
    """
    speech_file_path = generate_tts(text, "speech.mp3")
    play_sound(speech_file_path)

    try:
        while mixer.music.get_busy():
            # Non-blocking check for interrupt signal
            with shared_variables.latest_text_lock:
                current_text = shared_variables.latest_text
                # Clear latest_text to avoid processing the same text multiple times
                shared_variables.latest_text = ""

            if current_text and any(hot_word in current_text.lower() for hot_word in hot_words):
                print("Slicy interrupted.")
                mixer.music.stop()
                break  # Exit the loop to proceed to cleanup
            time.sleep(0.1) 
    finally:
        # Ensure resources are cleaned up whether interrupted or not
        mixer.music.unload()
        if os.path.exists(speech_file_path):
            os.remove(speech_file_path)
    return "done"

if __name__ == "__main__":
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            break
        response = ask_question_memory(user_input)
        print("Assistant:", response)
        TTS(response)