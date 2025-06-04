# functions_declaration.py

# NOTE: The Gemini API is a bit stricter with its schema definitions than general JSON Schema.
# While 'default' is a standard JSON Schema keyword, it seems the google.generativeai library's internal schema validation doesn't expect it for parameter properties.

# NOTE: The Gemini API expects a more rigidly defined schema structure that doesn't explicitly use additionalProperties in the same way some JSON schema validators do.
# By simply declaring 'prefs' as "type": "object" and providing a good description, you allow for a flexible dictionary-like input without causing the schema validation error. The library is generally permissive for object types if their internal properties aren't strictly defined.

# --- Preference Management Functions ---

load_preferences_declaration = {
    "name": "load_preferences",
    "description": "Loads user preferences from the preferences.json file. Returns an empty dictionary if not found or on error.",
    "parameters": {
        "type": "object",
        "properties": {}, # No parameters for this function
    },
    # "required": [] # No required parameters
}

save_preferences_declaration = {
    "name": "save_preferences",
    "description": "Saves user preferences to the preferences.json file. The input should be a dictionary of preferences.",
    "parameters": {
        "type": "object",
        "properties": {
            "prefs": {
                "type": "object", # Defines 'prefs' as an object
                "description": "A dictionary containing the user preferences to save (e.g., {'printer_profile': 'MyPrusa', 'default_material': 'PLA'}). The specific keys and values within this dictionary are flexible.",
                # By not defining specific "properties" for the "prefs" object,
                # it implies that it can accept arbitrary key-value pairs,
                # effectively behaving like additionalProperties: True without using the keyword.
            }
        },
        "required": ["prefs"],
    },
}

toggle_silent_mode_declaration = {
    "name": "toggle_silent_mode",
    "description": "Enables or disables silent mode. When silent mode is enabled, the assistant will only respond with text. When disabled, voice responses are resumed.",
    "parameters": {
        "type": "object",
        "properties": {
            "state": {
                "type": "boolean",
                "description": "Set to true to enable silent mode, or false to disable it.",
            }
        },
        "required": ["state"],
    },
}

# --- OctoPrint Integration Functions ---

octoprint_list_files_declaration = {
    "name": "octoprint_list_files",
    "description": "Lists files present on OctoPrint. Can specify location (e.g., 'local', 'sdcard') and if the search should be recursive. If location is not specified by the user, 'local' is assumed. If recursive is not specified, it defaults to true.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The location to list files from on OctoPrint (e.g., 'local', 'sdcard'). Assumes 'local' if not specified.",
            },
            "recursive": {
                "type": "boolean",
                "description": "Whether to list files recursively. Defaults to true if not specified.",
            },
        },
        "required": [], # Still optional for the LLM to specify
    },
}

octoprint_list_slicing_profiles_declaration = {
    "name": "octoprint_list_slicing_profiles",
    "description": "Lists slicing profiles available for a given slicer name in OctoPrint (e.g., 'cura', 'prusa').",
    "parameters": {
        "type": "object",
        "properties": {
            "slicer_name": {
                "type": "string",
                "description": "The name of the slicer for which to list profiles (e.g., 'cura', 'prusa').",
            }
        },
        "required": ["slicer_name"],
    },
}

octoprint_start_print_declaration = {
    "name": "octoprint_start_print",
    "description": "Starts printing an existing G-code file located on OctoPrint.",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path_on_octoprint": {
                "type": "string",
                "description": "The full path to the G-code file on OctoPrint that should be printed (e.g., 'folder_name/my_model.gcode' or 'my_model.gcode' if in root).",
            }
        },
        "required": ["file_path_on_octoprint"],
    },
}

octoprint_slice_model_declaration = {
    "name": "octoprint_slice_model",
    "description": "Slices a 3D model (STL, 3MF, etc.) located on OctoPrint using a specified slicer, slicing profile, and printer profile. Can optionally print the model after slicing. Printer profile defaults to '_default' and print_after_slice defaults to false if not specified.",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path_on_octoprint": {
                "type": "string",
                "description": "The path to the 3D model file (e.g., STL, 3MF) on OctoPrint to be sliced (e.g., 'models/my_object.stl').",
            },
            "slicer_name": {
                "type": "string",
                "description": "The name of the slicer to use (e.g., 'cura', 'prusa').",
            },
            "slicing_profile_key": {
                "type": "string",
                "description": "The key/identifier of the slicing profile to use for the specified slicer.",
            },
            "printer_profile_key": {
                "type": "string",
                "description": "The key/identifier of the printer profile to use. Assumes '_default' if not specified.",
            },
            "output_gcode_name": {
                "type": "string",
                "description": "Optional desired name for the output G-code file. If not provided, a name will be generated (e.g., 'original_filename.gcode').",
            },
            "print_after_slice": {
                "type": "boolean",
                "description": "Whether to automatically start printing the model after slicing is complete. Assumes false if not specified.",
            },
        },
        "required": ["file_path_on_octoprint", "slicer_name", "slicing_profile_key"],
    },
}

# --- Local File System and Slicing Functions ---

list_stl_files_declaration = {
    "name": "list_stl_files",
    "description": "Lists 3D printable files (STL, 3MF, OBJ) found in the system's default 3D model folder. The output is printed to the console as a table.",
    "parameters": {
        "type": "object",
        "properties": {}, # No parameters for this function
    },
    # "required": []
}

slice_model_declaration = {
    "name": "slice_model",
    "description": "Slices a 3D model (STL, 3MF, OBJ) using the locally installed PrusaSlicer. The input can be a file name (if in the default folder), an index number from 'list_stl_files', or an absolute path. Returns the path to the generated G-code file.",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Identifier for the 3D model file. Can be a file name (e.g., 'my_model.stl'), an index number (e.g., '1', '2') from a previous 'list_stl_files' call, or a full absolute path to the model file.",
            },
            "output_path": {
                "type": "string",
                "description": "Optional. The desired full path for the output G-code file. If not provided, the G-code is saved next to the input model with the same base name and .gcode extension.",
            },
        },
        "required": ["file_path"],
    },
}

view_gcode_declaration = {
    "name": "view_gcode",
    "description": "Opens the specified .gcode file using the locally installed Prusa G-code Viewer.",
    "parameters": {
        "type": "object",
        "properties": {
            "gcode_file_path": {
                "type": "string",
                "description": "The path to the .gcode file to be viewed. Can be a file name (if in the default folder where models are stored) or a full absolute path.",
            }
        },
        "required": ["gcode_file_path"],
    },
}

# --- Browser/URL Fetching Tool ---
fetch_local_url_content_declaration = {
    "name": "fetch_local_url_content",
    "description": "Fetches the textual content from a given URL, typically on the local network. Useful for getting status from 3D printers (e.g., OctoPrint API endpoint) or other local web-accessible devices/services. Returns content as markdown.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The full local URL to fetch (e.g., 'http://octoprint.local/api/job', 'http://192.168.1.100/status').",
            }
        },
        "required": ["url"],
    },
}


# --- Tool Configuration for Gemini ---
# You would collect all your declarations into a list like this:
all_function_declarations = [
    load_preferences_declaration,
    save_preferences_declaration,
    toggle_silent_mode_declaration,
    octoprint_list_files_declaration,
    octoprint_list_slicing_profiles_declaration,
    octoprint_start_print_declaration,
    octoprint_slice_model_declaration,
    list_stl_files_declaration,
    slice_model_declaration,
    view_gcode_declaration,
    fetch_local_url_content_declaration
]
