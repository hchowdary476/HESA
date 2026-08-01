filepath = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\JARVIS\gui\qml_bridge.py"

with open(filepath, "r", encoding="utf-8") as file:
    lines = file.readlines()

print("Found lines in qml_bridge.py:")
count = 0
for idx, line in enumerate(lines):
    if "Property(" in line or "@Slot" in line or "Slot(" in line:
        print(f"{idx+1}: {line.strip()}")
        count += 1
        if count >= 100:
            break
