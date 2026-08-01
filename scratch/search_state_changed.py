filepath = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\JARVIS\gui\qml_bridge.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.splitlines()
print("stateChanged.emit calls:")
for idx, line in enumerate(lines):
    if "stateChanged.emit" in line:
        print(f"  {idx+1}: {line.strip()}")
