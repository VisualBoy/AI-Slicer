import threading
latest_text = ""
latest_text_lock = threading.Lock()
last_gcode_path = None 