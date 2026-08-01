filepath = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\JARVIS\gui\qml_bridge.py"

with open(filepath, "r", encoding="utf-8") as file:
    content = file.read()

import re
methods = [
    "setSystemVolume",
    "getSystemVolume",
    "setSystemBrightness",
    "getSystemBrightness",
    "takeSystemScreenshot",
    "getClipboardText",
    "setClipboardText",
    "launchApp",
    "getSystemProcesses",
    "killProcess",
    "setStartupEnabled",
    "isStartupEnabled",
    "showNotification"
]

print("Scanning for Windows methods in qml_bridge.py:")
for m in methods:
    if m in content:
        # Find def line and first few lines of implementation
        lines = content.splitlines()
        found = False
        for idx, line in enumerate(lines):
            if f"def {m}" in line:
                print(f"\nMethod: {m} (line {idx+1})")
                for offset in range(0, 15):
                    if idx + offset < len(lines):
                        print(lines[idx + offset])
                found = True
                break
        if not found:
            print(f"\nMethod: {m} is referenced in text but 'def {m}' not found.")
    else:
        print(f"\nMethod: {m} - NOT FOUND")
