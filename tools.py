from googlesearch import search
import os
import subprocess
import logging 

PRUSA_SLICER_EXECUTABLE = os.getenv("PRUSA_SLICER_PATH")

# Configura il logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Aggiungi questa riga per provare a silenziare RealtimeSTT
# logging.getLogger("RealtimeSTT").setLevel(logging.WARNING) 
# E magari anche faster_whisper, se i log venissero da lì
# logging.getLogger("faster_whisper").setLevel(logging.WARNING)

PREFERENCES_FILE = "preferences.json"

def load_preferences():
    """Loads user preferences from preferences.json."""
    if not os.path.exists(PREFERENCES_FILE):
        return {} # Ritorna dizionario vuoto se non esiste
    try:
        with open(PREFERENCES_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading preferences: {e}")
        return {}

def save_preferences(prefs):
    """Saves user preferences to preferences.json."""
    try:
        with open(PREFERENCES_FILE, 'w') as f:
            json.dump(prefs, f, indent=4)
        return True
    except Exception as e:
        logging.error(f"Error saving preferences: {e}")
        return False

def set_preference(key, value):
    """Sets a specific preference and saves it."""
    prefs = load_preferences()
    prefs[key] = value
    if save_preferences(prefs):
        return f"Ok, Glitch. Ho impostato {key} a {value}."
    else:
        return "Sir, non sono riuscito a salvare le preferenze."

def get_files_from_default_folder():
    """Helper function to get a list of files."""
    default_folder = os.getenv("STL_DEFAULT_FOLDER")
    if not default_folder or not os.path.exists(default_folder):
        return []
        
    supported_extensions = ['.stl', '.3mf', '.obj']
    found_files = []
    try:
        for f in os.listdir(default_folder):
            if os.path.isfile(os.path.join(default_folder, f)) and any(f.lower().endswith(ext) for ext in supported_extensions):
                found_files.append(f)
        return found_files
    except:
        return []

def slice_model(file_path, output_path=None):
    """
    Slices a 3D model, attempting to fix 'no extrusions' error by centering.
    """
    prusa_executable = os.getenv("PRUSA_SLICER_PATH")
    default_folder = os.getenv("STL_DEFAULT_FOLDER")
    
    # --- Inizio controlli e setup percorso (come prima) ---
    if not prusa_executable:
        logging.error("PRUSA_SLICER_PATH not found in .env file.")
        return "Errore: Il percorso di PrusaSlicer non è configurato."
    if not os.path.exists(prusa_executable):
        logging.error(f"PrusaSlicer executable not found at: {prusa_executable}")
        return f"Errore: Non trovo PrusaSlicer qui: {prusa_executable}."

    actual_file_path = ""
    try:
        file_index = int(file_path.strip()) - 1
        available_files = get_files_from_default_folder()
        if 0 <= file_index < len(available_files):
            actual_file_path = os.path.join(default_folder, available_files[file_index])
        else:
            return f"Sir, il numero {file_path} non è valido."
    except ValueError:
        if not os.path.isabs(file_path):
            if not default_folder: return "Errore: Cartella predefinita non configurata."
            actual_file_path = os.path.join(default_folder, file_path)
        else:
            actual_file_path = file_path

    if not actual_file_path or not os.path.exists(actual_file_path):
        return f"Errore: Non trovo il file {file_path}."

    if output_path:
        gcode_file = output_path
    else:
        base_name = os.path.basename(actual_file_path)
        name_without_ext = os.path.splitext(base_name)[0]
        gcode_file = os.path.join(os.path.dirname(actual_file_path), f"{name_without_ext}.gcode")
    # --- Fine controlli e setup percorso ---

    # --- Primo tentativo di Slicing ---
    command = [prusa_executable, "-g", actual_file_path, "-o", gcode_file]
    logging.info(f"Primo tentativo: {' '.join(command)}")
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        # Controlla se ha funzionato o se è l'errore Z=0
        if result.returncode == 0:
            logging.info(f"Slicing riuscito al primo tentativo. Output: {gcode_file}")
            return f"Fatto, Sir! Ho processato {os.path.basename(actual_file_path)} e salvato il G-code."
        
        elif "no extrusions in the first layer" in result.stderr:
            logging.warning("Errore Z=0 rilevato. Tento la correzione con --center.")
            
            # --- Secondo tentativo con --center ---
            # Usiamo 125,105 come centro (tipico per Prusa), puoi cambiarlo se necessario
            command_fix = [prusa_executable, "-g", actual_file_path, "-o", gcode_file, "--center", "125,105"]
            logging.info(f"Secondo tentativo: {' '.join(command_fix)}")
            
            result_fix = subprocess.run(command_fix, capture_output=True, text=True, check=False)

            if result_fix.returncode == 0:
                logging.info(f"Slicing riuscito al secondo tentativo (con --center). Output: {gcode_file}")
                return f"Fatto, Sir! Ho dovuto riposizionare l'oggetto, ma ho processato {os.path.basename(actual_file_path)} e salvato il G-code."
            else:
                logging.error(f"Anche il secondo tentativo è fallito. Stderr: {result_fix.stderr}")
                return f"Sir, ho provato a riposizionare l'oggetto, ma lo slicing è fallito di nuovo. Errore: {result_fix.stderr[:100]}..."
        
        else:
            # Altro tipo di errore
            logging.error(f"PrusaSlicer failed (Primo tentativo). Stderr: {result.stderr}")
            return f"Sir, c'è stato un problema durante lo slicing. Errore: {result.stderr[:100]}..."

    except Exception as e:
        logging.error(f"An unexpected error occurred during slicing: {e}")
        return f"Si è verificato un errore inaspettato durante lo slicing: {e}"

def list_stl_files():
    """
    Lists 3D printable files (STL, 3MF, OBJ) in the default folder.
    """
    default_folder = os.getenv("STL_DEFAULT_FOLDER")

    if not default_folder or not os.path.exists(default_folder):
        logging.error(f"Default STL folder not found or not set: {default_folder}")
        return "Sir, la cartella predefinita per gli oggetti 3D non è configurata o non esiste. Controlla il file .env."

    supported_extensions = ['.stl', '.3mf', '.obj']
    found_files = []
    try:
        for f in os.listdir(default_folder):
            if os.path.isfile(os.path.join(default_folder, f)) and any(f.lower().endswith(ext) for ext in supported_extensions):
                found_files.append(f)
    except Exception as e:
        logging.error(f"Error reading default folder: {e}")
        return f"Sir, ho riscontrato un errore nel leggere la cartella: {e}"

    if not found_files:
        return "Sir, non ho trovato file stampabili nella cartella predefinita."

    # Crea una lista numerata
    file_list_str = "Sir, ecco i file che ho trovato:\n"
    for i, f_name in enumerate(found_files, 1):
        file_list_str += f"{i}. {f_name}\n"
    
    file_list_str += "Quale file desideri processare? Puoi dire il nome o il numero."
    
    return file_list_str

# Web search functions
def perform_web_search(query, num_results=3):
    try:
        results = list(search(query, num_results=num_results, advanced=True))
        return [{'title': r.title, 'description': r.description, 'url': r.url} for r in results]
    except Exception as e:
        print(f"Error performing web search: {e}")
        return []

def web_search(query):
    results = perform_web_search(query)
    if results:
        return "\n".join([f"Title: {r['title']}\nDescription: {r['description']}" for r in results])
    return f"No results found for '{query}'"

# Light control
def control_lights(state: bool):
    return f"Lights turned {'on' if state else 'off'}"



    
    # Silent mode state
silent_mode_state = False

def toggle_silent_mode(state):
    global silent_mode_state
    silent_mode_state = state
    return f"Silent mode {'enabled' if state else 'disabled'}."

def is_silent_mode():
    return silent_mode_state