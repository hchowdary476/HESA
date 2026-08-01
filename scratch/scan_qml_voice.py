import os
import re

qml_dir = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\JARVIS\gui\qml"
print("Scanning QML files for voice/state bindings:")
for f in os.listdir(qml_dir):
    if f.endswith(".qml"):
        fp = os.path.join(qml_dir, f)
        with open(fp, "r", encoding="utf-8") as file:
            content = file.read()
        matches = re.findall(r"jarvis\.[a-zA-Z0-9_]+", content)
        matches = sorted(list(set(matches)))
        voice_matches = [m for m in matches if "voice" in m.lower() or "state" in m.lower() or "speak" in m.lower() or "listen" in m.lower()]
        if voice_matches:
            print(f"  {f}:")
            for m in voice_matches:
                print(f"    {m}")
