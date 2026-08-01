import time
import sys
import os

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root_dir)

def time_import(module_path):
    start = time.perf_counter()
    try:
        __import__(module_path)
        elapsed = time.perf_counter() - start
        print(f"Import `{module_path}`: {elapsed:.4f}s")
        return elapsed
    except Exception as e:
        print(f"Import `{module_path}`: FAILED ({e})")
        return -1

print("Tracing groq_router dependencies...")
time_import("groq")
time_import("dotenv")
time_import("JARVIS.core.automation.action_dispatcher")
time_import("JARVIS.core.security.jarvis_admin")
time_import("JARVIS.core.memory")
