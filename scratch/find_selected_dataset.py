filepath = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\JARVIS\gui\qml\AIMLPage.qml"

with open(filepath, "r", encoding="utf-8") as file:
    lines = file.readlines()

for idx, line in enumerate(lines):
    if "selectedDataset" in line:
        print(f"{idx+1}: {line.strip()}")
