from JARVIS.config.manager import ConfigManager
import os

cm = ConfigManager()
cm.load()
diag = cm._diagnostics
print(f"Config path: {diag['config_path']}")
print(f"Config exists: {diag['config_exists']}")
if diag['config_exists']:
    with open(diag['config_path'], "r", encoding="utf-8") as f:
        print(f.read())
else:
    print("Settings file does not exist.")
