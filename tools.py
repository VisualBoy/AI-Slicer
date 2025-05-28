from googlesearch import search # Se usi ancora web_search, altrimenti puoi rimuoverlo
import os
import subprocess
import logging 
import json # Importa json per load_preferences

# Configura il logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Rimosse le righe per silenziare RealtimeSTT/faster_whisper se non servono più
# logging.getLogger("RealtimeSTT").setLevel(logging.WARNING) 
# logging.getLogger("faster_whisper").setLevel(logging.WARNING)

PREFERENCES_FILE = "preferences.json"

# --- Funzioni per le Preferenze (come definite prima) ---
def load_preferences():
    """Loads user preferences from preferences.json."""
    if not os.path.exists(PREFERENCES_FILE):
        logging.info(f"{PREFERENCES_FILE} non trovato, ritorno dizionario vuoto.")
        return {} 
    try:
        with open(PREFERENCES_FILE, 'r') as f:
            prefs = json.load(f)
            logging.info(f"Preferenze caricate: {prefs}")
            return prefs
    except Exception as e:
        logging.error(f"Errore nel caricare le preferenze: {e}")
        return {}

def save_preferences(prefs):
    """Saves user preferences to preferences.json."""
    try:
        with open(PREFERENCES_FILE, 'w') as f:
            json.dump(prefs, f, indent=4)
        logging.info(f"Preferenze salvate: {prefs}")
        return True
    except Exception as e:
        logging.error(f"Errore nel salvare le preferenze: {e}")
        return False

def set_preference(key, value):
    """Sets a specific preference and saves it."""
    prefs = load_preferences()
    # Prova a convertire il valore se è un numero (per altezza layer, infill, ecc.)
    try:
        if '.' in str(value): # Se c'è un punto, prova a convertirlo in float
            processed_value = float(value)
        else: # Altrimenti, prova a convertirlo in int
            processed_value = int(value)
    except ValueError: # Se non è un numero, lascialo come stringa
        processed_value = value
        
    prefs[key] = processed_value
    if save_preferences(prefs):
        return f"Ok, Glitch. Ho impostato '{key}' a '{processed_value}'."
    else:
        return "Sir, non sono riuscito a salvare le preferenze."
# --- Fine Funzioni Preferenze ---


# --- Funzioni Esistenti (web_search, control_lights, toggle_silent_mode) ---
# Assicurati che queste siano presenti se le usi ancora
def perform_web_search(query, num_results=3): # Esempio web_search
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

def control_lights(state: bool): # Esempio control_lights
    return f"Lights turned {'on' if state else 'off'}"

_silent_mode = False # Stato interno per la modalità silenziosa
def toggle_silent_mode(state: bool): # Esempio toggle_silent_mode
    global _silent_mode
    _silent_mode = state
    if _silent_mode:
        return "Silent mode enabled. I will only respond with text."
    else:
        return "Silent mode disabled. Voice responses resumed."

def is_silent_mode(): # Funzione helper
    global _silent_mode
    return _silent_mode
# --- Fine Funzioni Esistenti ---


def get_files_from_default_folder():
    """Helper function to get a list of files."""
    default_folder = os.getenv("STL_DEFAULT_FOLDER")
    if not default_folder or not os.path.exists(default_folder):
        logging.error(f"Cartella STL predefinita non trovata o non impostata: {default_folder}")
        return []
        
    supported_extensions = ['.stl', '.3mf', '.obj'] # Puoi aggiungere altri formati
    found_files = []
    try:
        for f_name in os.listdir(default_folder):
            if os.path.isfile(os.path.join(default_folder, f_name)) and \
               any(f_name.lower().endswith(ext) for ext in supported_extensions):
                found_files.append(f_name)
        logging.info(f"File trovati nella cartella di default: {found_files}")
        return sorted(found_files) # Ritorna i file ordinati
    except Exception as e:
        logging.error(f"Errore nel leggere la cartella di default: {e}")
        return []

def list_stl_files():
    """
    Lists 3D printable files (STL, 3MF, OBJ) in the default folder.
    """
    found_files = get_files_from_default_folder()

    if not found_files:
        return "Sir, non ho trovato file stampabili nella cartella predefinita."

    file_list_str = "Sir, ecco i file che ho trovato:\n"
    for i, f_name in enumerate(found_files, 1):
        file_list_str += f"{i}. {f_name}\n"
    
    file_list_str += "Quale file desideri processare? Puoi dire il nome o il numero."
    return file_list_str

def slice_model(file_path, output_path=None):
    """
    Slices a 3D model, attempting to fix 'no extrusions' error by centering.
    Returns a dictionary with status, message, and gcode_path on success.
    """
    prusa_executable = os.getenv("PRUSA_SLICER_PATH")
    default_folder = os.getenv("STL_DEFAULT_FOLDER")
    
    if not prusa_executable:
        logging.error("PRUSA_SLICER_PATH not found in .env file.")
        return {"status": "error", "message": "Errore: Il percorso di PrusaSlicer non è configurato."}
    if not os.path.exists(prusa_executable):
        logging.error(f"PrusaSlicer executable not found at: {prusa_executable}")
        return {"status": "error", "message": f"Errore: Non trovo PrusaSlicer qui: {prusa_executable}."}

    actual_file_path = ""
    try:
        file_index = int(file_path.strip()) - 1
        available_files = get_files_from_default_folder()
        if 0 <= file_index < len(available_files):
            actual_file_path = os.path.join(default_folder, available_files[file_index])
            logging.info(f"Utente ha selezionato il numero {file_path}, mappato a: {actual_file_path}")
        else:
            return {"status": "error", "message": f"Sir, il numero {file_path} non è valido per la lista corrente."}
    except ValueError: # Non era un numero, quindi è un nome file o un percorso
        if not os.path.isabs(file_path):
            if not default_folder:
                logging.error("Percorso file non assoluto e STL_DEFAULT_FOLDER non impostato.")
                return {"status": "error", "message": "Errore: Hai fornito solo un nome file, ma la cartella predefinita non è configurata."}
            actual_file_path = os.path.join(default_folder, file_path)
            logging.info(f"Il percorso è relativo, uso la cartella di default: {actual_file_path}")
        else:
            actual_file_path = file_path

    if not actual_file_path or not os.path.exists(actual_file_path):
        logging.error(f"File di input non trovato o non determinato: {actual_file_path}")
        return {"status": "error", "message": f"Errore: Non riesco a trovare il file {os.path.basename(file_path)} da processare."}

    # Costruzione nome G-code di output
    if output_path:
        gcode_file = output_path
    else:
        base_name = os.path.basename(actual_file_path)
        name_without_ext = os.path.splitext(base_name)[0]
        gcode_file = os.path.join(os.path.dirname(actual_file_path), f"{name_without_ext}.gcode")
    
    common_args = ["-g", actual_file_path, "-o", gcode_file]
    command_try1 = [prusa_executable] + common_args
    
    logging.info(f"Primo tentativo di slicing: {' '.join(command_try1)}")
    
    try:
        result1 = subprocess.run(command_try1, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace')

        if result1.returncode == 0:
            logging.info(f"Slicing riuscito al primo tentativo. Output: {gcode_file}")
            return {
                "status": "success",
                "message": f"Fatto, Sir! Ho processato {os.path.basename(actual_file_path)} e salvato il G-code.",
                "gcode_path": gcode_file
            }
        elif "no extrusions in the first layer" in result1.stderr:
            logging.warning(f"Errore Z=0 rilevato (stderr: {result1.stderr[:200]}). Tento la correzione con --center.")
            # Definisci X,Y per il centro del piatto (configurabile se necessario)
            bed_center_x = "125" 
            bed_center_y = "105"
            command_try2 = [prusa_executable] + common_args + ["--center", f"{bed_center_x},{bed_center_y}"]
            logging.info(f"Secondo tentativo di slicing: {' '.join(command_try2)}")
            
            result2 = subprocess.run(command_try2, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace')

            if result2.returncode == 0:
                logging.info(f"Slicing riuscito al secondo tentativo (con --center). Output: {gcode_file}")
                return {
                    "status": "success",
                    "message": f"Fatto, Sir! Ho dovuto riposizionare l'oggetto, ma ho processato {os.path.basename(actual_file_path)} e salvato il G-code.",
                    "gcode_path": gcode_file
                }
            else:
                logging.error(f"Anche il secondo tentativo è fallito. Stderr: {result2.stderr[:200]}")
                return {"status": "error", "message": f"Sir, ho provato a riposizionare l'oggetto, ma lo slicing è fallito di nuovo. Errore: {result2.stderr[:100]}..."}
        else:
            logging.error(f"PrusaSlicer ha fallito (Primo tentativo). Stderr: {result1.stderr[:200]}")
            return {"status": "error", "message": f"Sir, c'è stato un problema durante lo slicing. Errore: {result1.stderr[:100]}..."}

    except Exception as e:
        logging.error(f"Errore inaspettato durante lo slicing: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Si è verificato un errore Python inaspettato durante lo slicing: {e}"}

# --- NUOVA FUNZIONE: view_gcode ---
def view_gcode(gcode_file_path):
    """
    Opens the specified .gcode file using prusa-gcodeviewer.exe.
    """
    gcode_viewer_executable = os.getenv("PRUSA_GCODEVIEWER_PATH")

    if not gcode_viewer_executable:
        logging.error("PRUSA_GCODEVIEWER_PATH not found in .env file.")
        return "Sir, il percorso del visualizzatore G-code non è configurato. Controlla il file .env."

    if not os.path.exists(gcode_viewer_executable):
        logging.error(f"Prusa G-code Viewer executable not found at: {gcode_viewer_executable}")
        return f"Sir, non trovo prusa-gcodeviewer.exe qui: {gcode_viewer_executable}. Verifica il percorso."

    # Controlla se gcode_file_path è un percorso assoluto o solo un nome file
    # Se è un nome file, si assume che sia nella cartella di default STL (o dove è stato salvato l'ultimo G-code)
    actual_gcode_path = ""
    if not os.path.isabs(gcode_file_path):
        default_folder = os.getenv("STL_DEFAULT_FOLDER") # o una cartella G-code predefinita
        if not default_folder:
            logging.error("G-code path is not absolute and STL_DEFAULT_FOLDER (for G-code) is not set.")
            return "Sir, hai fornito solo un nome file per il G-code, ma non so dove cercarlo."
        actual_gcode_path = os.path.join(default_folder, gcode_file_path)
        logging.info(f"G-code path is relative, looking in default folder: {actual_gcode_path}")
    else:
        actual_gcode_path = gcode_file_path
        
    if not os.path.exists(actual_gcode_path):
        logging.error(f"G-code file not found: {actual_gcode_path}")
        return f"Sir, il file G-code da visualizzare non esiste: {os.path.basename(actual_gcode_path)}."

    command = [gcode_viewer_executable, actual_gcode_path]
    logging.info(f"Eseguo il comando del G-code Viewer: {' '.join(command)}")

    try:
        subprocess.Popen(command) # Avvia e non attendere
        return f"Ok, Glitch, sto aprendo {os.path.basename(actual_gcode_path)} con il visualizzatore G-code."
    except FileNotFoundError:
        logging.error(f"Comando non trovato: {gcode_viewer_executable}.")
        return "Errore critico: Non riesco ad eseguire prusa-gcodeviewer.exe."
    except Exception as e:
        logging.error(f"Errore inaspettato durante l'apertura del G-code viewer: {e}")
        return f"Si è verificato un errore inaspettato: {e}"
# --- FINE NUOVA FUNZIONE ---