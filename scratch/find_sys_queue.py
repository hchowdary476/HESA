filepath = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\JARVIS\gui\qml_bridge.py"

with open(filepath, "r", encoding="utf-8") as file:
    lines = file.readlines()

print("Lines referencing _sys_queue:")
for idx, line in enumerate(lines):
    if "_sys_queue" in line:
        print(f"{idx+1}: {line.strip()}")
