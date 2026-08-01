# NOTE: This script is a historical migration utility and is currently INACTIVE.
# It is kept for historical reference. Do not run it.

import os
import shutil
import glob

def replace_in_files(dir_path, replacements):
    for root, _, files in os.walk(dir_path):
        for file in files:
            if not file.endswith('.py'):
                continue
            file_path = os.path.join(root, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content
            for old, new in replacements.items():
                new_content = new_content.replace(old, new)
                
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

def main():
    replacements = {
        "JARVIS.gui": "JARVIS.gui",
        "JARVIS.core.voice": "JARVIS.core.voice",
        "JARVIS.core.memory": "JARVIS.core.memory",
        "JARVIS.core.security": "JARVIS.core.security",
        "JARVIS.core.ai_router": "JARVIS.core.ai_router",
        "JARVIS.core.automation": "JARVIS.core.automation",
        "JARVIS.core.system": "JARVIS.core.system",
        "JARVIS.core.system.utils": "JARVIS.core.system.utils",
        "JARVIS": "JARVIS" # Catch all remaining
    }
    
    replace_in_files(".", replacements)
    
    # Also rename jarvis_gui.py to main_window.py or similar if needed
    if os.path.exists("JARVIS/gui/arayuz.py"):
        os.rename("JARVIS/gui/arayuz.py", "JARVIS/gui/main_window.py")
        
    print("Refactoring complete.")
    
    replace_in_files(".", replacements)
    print("Refactoring complete.")

if __name__ == "__main__":
    main()
