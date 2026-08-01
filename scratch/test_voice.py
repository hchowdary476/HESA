import sys
import os
import time

os.makedirs("logs", exist_ok=True)
def log(msg):
    with open("logs/test_voice_import.log", "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

log("Starting imports test...")
try:
    log("Importing sys...")
    import sys
    log("Importing os...")
    import os
    
    # Add project root to sys.path
    sys.path.insert(0, os.path.abspath("."))
    
    log("Importing JARVIS.services.voice_service...")
    from JARVIS.services.voice_service import _start
    log("Successfully imported JARVIS.services.voice_service!")
    
    log("Running _start()...")
    _start()
    log("Exited normally.")
except BaseException as e:
    import traceback
    log(f"CRASH:\n{traceback.format_exc()}")
