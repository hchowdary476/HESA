import os
import re

jarvis_dir = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\JARVIS"

# Patterns to scan for
# Match any string literal containing jarvis or JARVIS (excluding obvious internal usages like imports)
results = []
for root, dirs, files in os.walk(jarvis_dir):
    # Exclude backup files/folders, test directories
    if "archive" in root or "tests" in root or "__pycache__" in root:
        continue
    for file in files:
        if not file.endswith(".py"):
            continue
        path = os.path.join(root, file)
        # Relpath for display
        rel_path = os.path.relpath(path, jarvis_dir)
        with open(path, "r", encoding="utf-8") as fh:
            for idx, line in enumerate(fh, 1):
                # Search case-insensitively for jarvis/JARVIS inside quotes
                stripped = line.strip()
                # Ignore comments
                if stripped.startswith("#"):
                    continue
                # Ignore imports
                if stripped.startswith("import ") or stripped.startswith("from "):
                    continue
                # Match anything inside quotes containing jarvis (case-insensitive)
                matches = re.findall(r'(["\'])(.*?[jJ][aA][rR][vV][iI][sS].*?)\1', line)
                if matches:
                    # Let's inspect the match and see if it's user facing
                    # Exclude: logger names, sys.path inserts, registry keys, file names, internal class registrations, imports, or variable names
                    if any(x in stripped for x in [
                        "get_logger", "getLogger", "sys.argv", "sys.path", "winreg",
                        "JARVIS_SilentBoot", "JARVIS_AutoLaunch", "jarvis_gui_startup.log",
                        "jarvis_autostart.log", "jarvis_events.log", "jarvis.py", "jarvis.ico",
                        "jarvis_face.png", "jarvis_gui.lock", "JARVIS.services", "JARVIS.core",
                        "JARVIS.gui", "JARVIS.runtime", "JARVIS_WAKE_WORD", "JARVIS_VOICE_ENABLED",
                        "JARVIS_TTS_PROVIDER", "JARVIS_OFFLINE_STT", "JARVIS_LOCAL_LLM_URL",
                        "JARVIS_AI_MODE", "JARVIS_WAKE_WORD_ENABLED", "JARVIS_WAKE_WORD_COOLDOWN_SECONDS",
                        "JARVIS_ACTIVE_TIMEOUT", "JARVIS_ACTION_SEQUENCE_DELAY", "JARVIS_APP_LAUNCH_DELAY",
                        "JARVIS_CPU_SAMPLE_INTERVAL", "JARVIS_PROCESS_MONITOR_INTERVAL", "JARVIS_SCREENSHOT_DELAY",
                        "JARVIS_SLEEP_ACTION_DELAY", "JARVIS_TYPE_DELAY", "JARVIS_ENERGY_THRESHOLD",
                        "JARVIS_PAUSE_THRESHOLD", "JARVIS_TTS_ENABLED", "JARVIS_ALLOW_DESTRUCTIVE_ACTIONS",
                        "JARVIS_PERMISSION_PROFILE", "JARVIS_PRIVACY_MODE", "JARVIS_VOSK_MODEL_PATH",
                        "JARVIS_RELEASE_SIGNING_KEY", "JARVIS_PLUGIN_SIGNING_KEY", "JARVIS_PLUGIN_SIGNING_KEYS",
                        "JARVIS_SECURE_SALT", "JARVIS_OFFLINE", "JARVIS_MANAGED", "JARVIS_FACE_MATCH_STATUS"
                    ]):
                        continue
                    
                    results.append((rel_path, idx, stripped))

with open(r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\scratch\py_scan_results.txt", "w", encoding="utf-8") as out:
    out.write(f"Found {len(results)} user-facing Python matches:\n")
    for file, line_no, content in results:
        out.write(f"{file}:{line_no} -> {content}\n")

print(f"Completed scan. Found {len(results)} matches. Results written to scratch/py_scan_results.txt.")
