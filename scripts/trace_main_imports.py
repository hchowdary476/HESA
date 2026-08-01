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

print("Tracing sub-imports...")
time_import("JARVIS.core.system.utils.jarvis_logging")
time_import("JARVIS.core.voice.ses_motoru")
time_import("JARVIS.core.voice.speech_backend")
time_import("JARVIS.core.automation.komutlar")
time_import("JARVIS.core.system.observability")
time_import("JARVIS.runtime.orchestrator")
time_import("JARVIS.runtime.readiness")
time_import("JARVIS.runtime.timer")
time_import("JARVIS.runtime.ui_bridge")
time_import("JARVIS.runtime.voice_personality")
time_import("JARVIS.runtime.wake_listener")
time_import("JARVIS.runtime.wake_word")
time_import("JARVIS.runtime.jarvis_runtime")
