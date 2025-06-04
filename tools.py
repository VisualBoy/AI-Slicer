import os
import subprocess
import logging
import json
import requests
import markdownify # Or from bs4 import BeautifulSoup

from rich.table import Table
from rich.text import Text
from rich import print as rprint
from rich.logging import RichHandler

# Configura il logging con RichHandler
logging.basicConfig(
    level=logging.WARNING, # CHANGED to WARNING
    format="%(message)s", # RichHandler handles its own formatting
    datefmt="[%X]",
    handlers=[RichHandler(level=logging.WARNING, rich_tracebacks=True, show_path=False, log_time_format="[%X]")] # MODIFIED Handler
)

# Rimosse le righe per silenziare RealtimeSTT/faster_whisper se non servono più
# logging.getLogger("RealtimeSTT").setLevel(logging.WARNING) 
# logging.getLogger("faster_whisper").setLevel(logging.WARNING)
PREFERENCES_FILE = "preferences.json"

# --- Funzioni per le Preferenze (come definite prima) ---
def load_preferences():
    """Loads user preferences from preferences.json."""
    if not os.path.exists(PREFERENCES_FILE):
        logging.info(f"{PREFERENCES_FILE} non trovato, ritorno dizionario vuoto.") # This will be INFO level
        return {} 
    try:
        with open(PREFERENCES_FILE, 'r') as f:
            prefs = json.load(f)
            logging.info(f"Preferenze caricate: {prefs}") # This will be INFO level
            return prefs
    except Exception as e:
        logging.error(f"Errore nel caricare le preferenze: {e}")
        return {}

def save_preferences(prefs):
    """Saves user preferences to preferences.json."""
    try:
        with open(PREFERENCES_FILE, 'w') as f:
            json.dump(prefs, f, indent=4)
        logging.info(f"Preferenze salvate: {prefs}") # This will be INFO level
        return True
    except Exception as e:
        logging.error(f"Errore nel salvare le preferenze: {e}")
        return False


_silent_mode = False # Stato interno per la modalità silenziosa
def toggle_silent_mode(state: bool):
    """
    Enables or disables silent mode.

    When silent mode is enabled, the assistant will only respond with text.
    When disabled, voice responses are resumed.

    Args:
        state (bool): True to enable silent mode, False to disable it.
    """
    global _silent_mode
    _silent_mode = state
    if _silent_mode:
        return "Silent mode enabled. I will only respond with text."
    else:
        return "Silent mode disabled. Voice responses resumed."

def is_silent_mode(): # Funzione helper
    global _silent_mode
    return _silent_mode

# Helper function to get OctoPrint base URL and headers
def _get_octoprint_config():
    octoprint_url = os.getenv("OCTOPRINT_URL")
    octoprint_api_key = os.getenv("OCTOPRINT_API_KEY")
    if not octoprint_url or not octoprint_api_key:
        logging.error("OctoPrint URL or API Key not found in .env file.")
        return None, None
    headers = {"X-Api-Key": octoprint_api_key}
    return octoprint_url, headers

# --- OctoPrint Integration Functions ---
def octoprint_list_files(location: str = "local", recursive: bool = True):
    """
    Lists files present on OctoPrint.
    """
    octoprint_url, headers = _get_octoprint_config()
    if not octoprint_url:
        return {"status": "error", "message": "OctoPrint configuration missing."}

    endpoint = f"{octoprint_url}/api/files"
    if location and location != "all": # OctoPrint API uses /api/files for all, or /api/files/{location}
        endpoint = f"{octoprint_url}/api/files/{location}"

    params = {"recursive": "true" if recursive else "false"}

    try:
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # OctoPrint returns a dictionary with 'files' key
        if 'files' in data:
            logging.info(f"OctoPrint files listed successfully from {location}.")
            return {"status": "success", "files": data['files']}
        else:
            logging.warning(f"OctoPrint response for files did not contain 'files' key: {data}")
            return {"status": "error", "message": "Unexpected OctoPrint response format for files."}
    except requests.exceptions.RequestException as e:
        logging.error(f"Error listing OctoPrint files: {e}")
        return {"status": "error", "message": f"Error connecting to OctoPrint or API issue: {e}"}
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON from OctoPrint file list response: {response.text}")
        return {"status": "error", "message": "Invalid JSON response from OctoPrint."}

def octoprint_list_slicing_profiles(slicer_name: str):
    """
    Lists slicing profiles available for a given slicer in OctoPrint.
    """
    octoprint_url, headers = _get_octoprint_config()
    if not octoprint_url:
        return {"status": "error", "message": "OctoPrint configuration missing."}

    endpoint = f"{octoprint_url}/api/slicing/profiles/{slicer_name}"

    try:
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # OctoPrint returns a dictionary with 'profiles' key
        if 'profiles' in data:
            logging.info(f"OctoPrint slicing profiles for {slicer_name} listed successfully.")
            return {"status": "success", "profiles": data['profiles']}
        else:
            logging.warning(f"OctoPrint response for slicing profiles did not contain 'profiles' key: {data}")
            return {"status": "error", "message": "Unexpected OctoPrint response format for slicing profiles."}
    except requests.exceptions.RequestException as e:
        logging.error(f"Error listing OctoPrint slicing profiles: {e}")
        return {"status": "error", "message": f"Error connecting to OctoPrint or API issue: {e}"}
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON from OctoPrint slicing profiles response: {response.text}")
        return {"status": "error", "message": "Invalid JSON response from OctoPrint."}

def octoprint_start_print(file_path_on_octoprint: str):
    """
    Starts printing an existing G-code file on OctoPrint.
    """
    octoprint_url, headers = _get_octoprint_config()
    if not octoprint_url:
        return {"status": "error", "message": "OctoPrint configuration missing."}

    print_endpoint = f"{octoprint_url}/api/job"
    print_payload = {
        "command": "select",
        "file": file_path_on_octoprint,
        "print": True
    }
    logging.info(f"Attempting to print: {print_payload}")
    try:
        response = requests.post(print_endpoint, headers=headers, json=print_payload)
        response.raise_for_status()
        logging.info(f"Print command sent successfully for {file_path_on_octoprint}.")
        return {"status": "success", "message": f"Print initiated for {file_path_on_octoprint}."}
    except requests.exceptions.RequestException as e:
        logging.error(f"Error during OctoPrint print: {e}")
        return {"status": "error", "message": f"Error connecting to OctoPrint or API issue during print: {e}"}
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON from OctoPrint print response: {response.text}")
        return {"status": "error", "message": "Invalid JSON response from OctoPrint during print."}

def octoprint_slice_model(file_path_on_octoprint: str, slicer_name: str, slicing_profile_key: str, printer_profile_key: str = "_default", output_gcode_name: str = None, print_after_slice: bool = False):
    """
    Slices an STL/3MF model on OctoPrint using a specified slicer and profile.
    """
    octoprint_url, headers = _get_octoprint_config()
    if not octoprint_url:
        return {"status": "error", "message": "OctoPrint configuration missing."}

    if not slicer_name or not slicing_profile_key:
        return {"status": "error", "message": "Slicer name and slicing profile key are required for slicing."}
    
    # Assume file_path_on_octoprint is the path to the model file (e.g., STL)
    # Extract filename and path for the slicing payload
    path_parts = file_path_on_octoprint.split('/')
    filename = path_parts[-1]
    path = '/'.join(path_parts[:-1]) if len(path_parts) > 1 else ""

    slicing_endpoint = f"{octoprint_url}/api/slicing/{slicer_name}/{slicing_profile_key}"
    slicing_payload = {
        "command": "slice",
        "path": path,
        "filename": filename,
        "printerProfile": printer_profile_key,
        "print": print_after_slice
    }
    if output_gcode_name:
        slicing_payload["gcode"] = output_gcode_name
    else:
        slicing_payload["gcode"] = f"{os.path.splitext(filename)[0]}.gcode" # OctoPrint will generate one if not provided

    logging.info(f"Attempting to slice model: {slicing_payload}")
    try:
        response = requests.post(slicing_endpoint, headers=headers, json=slicing_payload)
        response.raise_for_status()
        logging.info(f"Slicing command sent successfully for {file_path_on_octoprint}.")
        return {"status": "success", "message": f"Slicing initiated for {file_path_on_octoprint} using {slicer_name} with profile {slicing_profile_key}. Print after slice: {print_after_slice}."}
    except requests.exceptions.RequestException as e:
        logging.error(f"Error during OctoPrint slicing: {e}")
        return {"status": "error", "message": f"Error connecting to OctoPrint or API issue during slicing: {e}"}
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON from OctoPrint slicing response: {response.text}")
        return {"status": "error", "message": "Invalid JSON response from OctoPrint during slicing."}

# --- End OctoPrint Integration Functions ---

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
            if os.path.isfile(os.path.join(default_folder, f_name)) and                any(f_name.lower().endswith(ext) for ext in supported_extensions):
                found_files.append(f_name)
        logging.info(f"File trovati nella cartella di default: {found_files}") # This will be INFO level
        return sorted(found_files) # Ritorna i file ordinati
    except Exception as e:
        logging.error(f"Errore nel leggere la cartella di default: {e}")
        return []

def list_stl_files():
    """
    Lists 3D printable files (STL, 3MF, OBJ) in the default folder using a rich Table.
    """
    found_files = get_files_from_default_folder()

    if not found_files:
        return "Sir, non ho trovato file stampabili nella cartella predefinita."

    table = Table(title="Modelli 3D Disponibili", style="cyan", title_style="bold magenta", show_lines=True)

    table.add_column("#", style="dim cyan", justify="right", width=3)
    table.add_column("Nome File", style="green", overflow="fold")

    for i, f_name in enumerate(found_files, 1):
        table.add_row(str(i), Text(f_name, style="green"))
    
    rprint(table) 
    
    return "Ok, Glitch. Ho mostrato i file disponibili in una tabella."

def slice_model(file_path: str, output_path: str = None):
    """
    Slices a 3D model using PrusaSlicer and saves the G-code.

    This function can take a file name (if in the default STL folder),
    an index number (from 'list_stl_files'), or an absolute path to an STL/3MF/OBJ model.
    It attempts to automatically fix 'no extrusions in the first layer' errors by centering the model.
    Returns a dictionary with status, message, and gcode_path on success.

    Args:
        file_path (str): The identifier for the 3D model file to slice.
                         Can be a name, an index from `list_stl_files`, or a full path.
        output_path (str, optional): The desired path for the output G-code file.
                                     If not provided, G-code is saved next to the input model
                                     with the same base name. Defaults to None.
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
            logging.info(f"Utente ha selezionato il numero {file_path}, mappato a: {actual_file_path}") # This will be INFO level
        else:
            return {"status": "error", "message": f"Sir, il numero {file_path} non è valido per la lista corrente."}
    except ValueError: # Non era un numero, quindi è un nome file o un percorso
        if not os.path.isabs(file_path):
            if not default_folder:
                logging.error("Percorso file non assoluto e STL_DEFAULT_FOLDER non impostato.")
                return {"status": "error", "message": "Errore: Hai fornito solo un nome file, ma la cartella predefinita non è configurata."}
            actual_file_path = os.path.join(default_folder, file_path)
            logging.info(f"Il percorso è relativo, uso la cartella di default: {actual_file_path}") # This will be INFO level
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
    
    logging.info(f"Primo tentativo di slicing: {' '.join(command_try1)}") # This will be INFO level
    
    try:
        result1 = subprocess.run(command_try1, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace')

        if result1.returncode == 0:
            logging.info(f"Slicing riuscito al primo tentativo. Output: {gcode_file}") # This will be INFO level
            return {
                "status": "success",
                "message": f"Fatto, Sir! Ho processato {os.path.basename(actual_file_path)} e salvato il G-code.",
                "gcode_path": gcode_file
            }
        elif "no extrusions in the first layer" in result1.stderr:
            logging.warning(f"Errore Z=0 rilevato (stderr: {result1.stderr[:200]}). Tento la correzione con --center.")
            bed_center_x = "125" 
            bed_center_y = "105"
            command_try2 = [prusa_executable] + common_args + ["--center", f"{bed_center_x},{bed_center_y}"]
            logging.info(f"Secondo tentativo di slicing: {' '.join(command_try2)}") # This will be INFO level
            
            result2 = subprocess.run(command_try2, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace')

            if result2.returncode == 0:
                logging.info(f"Slicing riuscito al secondo tentativo (con --center). Output: {gcode_file}") # This will be INFO level
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
        traceback.print_exc() # This will now be a rich traceback if logging is configured by ai_slicer_rich.py
        return {"status": "error", "message": f"Si è verificato un errore Python inaspettato durante lo slicing: {e}"}

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

    actual_gcode_path = ""
    if not os.path.isabs(gcode_file_path):
        default_folder = os.getenv("STL_DEFAULT_FOLDER") 
        if not default_folder:
            logging.error("G-code path is not absolute and STL_DEFAULT_FOLDER (for G-code) is not set.")
            return "Sir, hai fornito solo un nome file per il G-code, ma non so dove cercarlo."
        actual_gcode_path = os.path.join(default_folder, gcode_file_path)
        logging.info(f"G-code path is relative, looking in default folder: {actual_gcode_path}") # This will be INFO level
    else:
        actual_gcode_path = gcode_file_path
        
    if not os.path.exists(actual_gcode_path):
        logging.error(f"G-code file not found: {actual_gcode_path}")
        return f"Sir, il file G-code da visualizzare non esiste: {os.path.basename(actual_gcode_path)}."

    command = [gcode_viewer_executable, actual_gcode_path]
    logging.info(f"Eseguo il comando del G-code Viewer: {' '.join(command)}") # This will be INFO level

    try:
        subprocess.Popen(command) 
        return f"Ok, Glitch, sto aprendo {os.path.basename(actual_gcode_path)} con il visualizzatore G-code."
    except FileNotFoundError:
        logging.error(f"Comando non trovato: {gcode_viewer_executable}.")
        return "Errore critico: Non riesco ad eseguire prusa-gcodeviewer.exe."
    except Exception as e:
        logging.error(f"Errore inaspettato durante l'apertura del G-code viewer: {e}")
        return f"Si è verificato un errore inaspettato: {e}"

def fetch_local_url_content(url: str) -> str:
    """
    Fetches content from a local URL and returns it as markdown or plain text.
    Args:
        url: The local URL to fetch (e.g., http://octoprint.local/api/job).
    """
    try:
        response = requests.get(url, timeout=5) # Add timeout
        response.raise_for_status() # Raise an exception for HTTP errors
        # Convert HTML to Markdown for cleaner input to the LLM
        content_md = markdownify.markdownify(response.text)
        # Or use BeautifulSoup to extract specific text:
        # soup = BeautifulSoup(response.text, 'html.parser')
        # content_text = soup.get_text()
        # Limit content length if necessary
        return content_md[:5000] # Return first 5000 chars to avoid overly long inputs
    except requests.exceptions.RequestException as e:
        return f"Error fetching URL {url}: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred while fetching {url}: {str(e)}"
