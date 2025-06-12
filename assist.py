import time
import os
import json
import logging
import tools
import shared_variables
import typing

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info("assist.py loaded and basic logging configured.")

# Carica le funzioni e trasformale per l'API (assumendo che la struttura sia riutilizzabile per Gemini)
try:
    with open('functions.json', 'r') as f:
        functions_list = json.load(f)['functions']
    gemini_tools_definitions = [{"type": "function", "function": func} for func in functions_list]
    logging.info("Definizioni funzioni caricate e trasformate per Gemini (struttura preliminare).")
except Exception as e:
    logging.error(f"Errore nel caricare functions.json: {e}")
    gemini_tools_definitions = []

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


def initialize_conversation() -> list[dict[str, str]]:
    """
    Initializes the conversation history with a system prompt.
    Returns the initial conversation history.
    """
    history = [
        {
            "role": "system",
            "content": "Sei un assistente AI chiamato Arturo. Il tuo scopo è aiutare con la stampa 3D usando PrusaSlicer. Parla sempre in italiano. Rivolgiti all'utente come 'Glitch'. Mantieni le tue risposte brevi e concise. L'utente usa speech2text, quindi considera possibili errori di trascrizione. Se lo slicing di un modello ha successo e viene generato un file G-code, chiedi sempre all'utente se desidera visualizzare un'anteprima del G-code. Se accetta, chiama la funzione 'view_gcode' con il percorso del file appena creato. Se l'utente chiede di impostare una preferenza, usa la funzione 'set_preference'."
        }
    ]
    return history

def add_user_message_to_history(text: str, history: list) -> list:
    """
    Adds a user message to the conversation history.
    Args:
        text: The user's message.
        history: The current conversation history.
    Returns:
        The updated conversation history.
    """
    history.append({"role": "user", "content": text})
    return history

def handle_gemini_response(
    gemini_response_text: typing.Optional[str],
    gemini_tool_calls: typing.Optional[list],
    history: list,
    function_map: dict
) -> tuple[list, typing.Optional[list[dict]]]:
    tool_responses_for_gemini = []
    if gemini_response_text:
        assistant_message_for_history = {"role": "assistant", "content": gemini_response_text}
        history.append(assistant_message_for_history)
        logging.debug(f"Assistant text response added to history: {gemini_response_text}")

    if gemini_tool_calls:
        logging.info(f"Gemini requested {len(gemini_tool_calls)} tool call(s).")
        for tool_call in gemini_tool_calls:
            function_name = ""
            function_args = {}
            tool_call_id = ""
            if hasattr(tool_call, 'function_call') and hasattr(tool_call.function_call, 'name') and hasattr(tool_call.function_call, 'args'):
                 fc_data = tool_call.function_call
                 function_name = fc_data.name
                 function_args = fc_data.args
                 tool_call_id = getattr(tool_call, 'id', function_name)
                 logging.debug(f"Extracted from FunctionCall Part: name={function_name}, args={function_args}, id_for_response={tool_call_id}")
            elif hasattr(tool_call, 'name') and hasattr(tool_call, 'args'):
                function_name = tool_call.name
                function_args = tool_call.args
                tool_call_id = getattr(tool_call, 'id', function_name)
                logging.debug(f"Extracted from direct attributes: name={function_name}, args={function_args}, id_for_response={tool_call_id}")
            else:
                logging.error(f"Tool call structure from Gemini not as expected: {tool_call}")
                continue
            logging.info(f"Processing tool call: {function_name} with args: {function_args}")
            tool_result_content_for_history = ""
            tool_result_for_gemini = {}
            try:
                if function_name in function_map:
                    tool_call_result = function_map[function_name](**function_args)
                    if function_name == "slice_model" and isinstance(tool_call_result, dict):
                        tool_result_content_for_history = tool_call_result.get("message", "Errore imprevisto nello slicing.")
                        if tool_call_result.get("status") == "success" and tool_call_result.get("gcode_path"):
                            shared_variables.last_gcode_path = tool_call_result.get("gcode_path")
                        tool_result_for_gemini = {"status": tool_call_result.get("status", "error"), "message": tool_result_content_for_history, "gcode_path": tool_call_result.get("gcode_path")}
                    else:
                        tool_result_content_for_history = str(tool_call_result)
                        tool_result_for_gemini = {"result": tool_result_content_for_history}
                else:
                    tool_result_content_for_history = f"Funzione {function_name} non trovata."
                    tool_result_for_gemini = {"error": tool_result_content_for_history}
                logging.info(f"Tool {function_name} executed. Result for history: {tool_result_content_for_history}")
            except Exception as func_err:
                logging.error(f"Error executing tool {function_name}: {func_err}")
                tool_result_content_for_history = f"Errore nell'eseguire {function_name}: {str(func_err)}"
                tool_result_for_gemini = {"error": tool_result_content_for_history}
            history.append({
                "role": "tool",
                "name": function_name,
                "content": tool_result_content_for_history
            })
            gemini_tool_response_obj = {
                "id": tool_call_id,
                "name": function_name,
                "response": tool_result_for_gemini
            }
            tool_responses_for_gemini.append(gemini_tool_response_obj)
        return history, tool_responses_for_gemini
    logging.debug("Nessun tool call richiesto da Gemini.")
    return history, None

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    print("Test di assist.py (logica Gemini - mockata):")
    current_history = initialize_conversation()
    print(f"Storia Iniziale: {json.dumps(current_history, indent=2, ensure_ascii=False)}")
    current_history = add_user_message_to_history("Ciao Arturo, puoi fare lo slicing del file test.stl?", current_history)
    print(f"\nStoria dopo msg utente: {json.dumps(current_history, indent=2, ensure_ascii=False)}")
    mock_fc_object = type('MockFunctionCall', (), {
        'id': 'tool_call_id_12345',
        'function_call': type('MockFunctionCallData', (), {
            'name': 'slice_model',
            'args': {"file_path": "test.stl"}
        })()
    })()
    mock_gemini_tool_calls_list = [mock_fc_object]
    mock_gemini_text_response = "Certo, Glitch! Procedo con lo slicing di test.stl."
    print(f"\nSimulazione risposta Gemini con tool call: text='{mock_gemini_text_response}', tool_calls={mock_gemini_tool_calls_list}")
    class MockSharedVariables:
        def __init__(self):
            self.last_gcode_path = None
    original_shared_variables = shared_variables
    shared_variables = MockSharedVariables()
    updated_history, tool_responses = handle_gemini_response(
        mock_gemini_text_response,
        mock_gemini_tool_calls_list,
        current_history,
        function_map
    )
    shared_variables = original_shared_variables
    print(f"\nStoria dopo risposta Gemini e gestione tool: {json.dumps(updated_history, indent=2, ensure_ascii=False)}")
    print(f"\nTool responses da inviare a Gemini: {json.dumps(tool_responses, indent=2, ensure_ascii=False)}")
    if tool_responses:
        final_gemini_text_response = "Ho completato lo slicing di test.stl. Il file G-code è pronto. Vuoi vederne l'anteprima?"
        updated_history_after_tool_response, final_tool_responses = handle_gemini_response(
            final_gemini_text_response,
            None,
            updated_history,
            function_map
        )
        print(f"\nStoria dopo risposta finale di Gemini: {json.dumps(updated_history_after_tool_response, indent=2, ensure_ascii=False)}")
        assert final_tool_responses is None
    current_history = add_user_message_to_history("Grazie Arturo!", updated_history_after_tool_response)
    final_reply_text = "Prego, Glitch! Alla prossima."
    updated_history_no_tools, no_tool_responses = handle_gemini_response(
        final_reply_text,
        None,
        current_history,
        function_map
    )
    print(f"\nStoria dopo risposta semplice di Gemini: {json.dumps(updated_history_no_tools, indent=2, ensure_ascii=False)}")
    assert no_tool_responses is None
    print("\nTest di assist.py completati.")
