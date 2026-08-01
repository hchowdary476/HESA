filepath = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\JARVIS\gui\qml_bridge.py"

with open(filepath, "r", encoding="utf-8") as file:
    lines = file.readlines()

def print_method(name):
    print(f"--- Implementation of {name} ---")
    start = -1
    for idx, line in enumerate(lines):
        if f"def {name}" in line:
            start = idx
            break
    if start == -1:
        print("Not found.")
        return
    # Find matching indentation lines
    indent = None
    for idx in range(start, len(lines)):
        line = lines[idx]
        if idx == start:
            print(line.rstrip())
            continue
        line_indent = len(line) - len(line.lstrip())
        if line.strip() == "":
            print(line.rstrip())
            continue
        if indent is None:
            indent = line_indent
        if line_indent < indent:
            break
        print(line.rstrip())

print_method("getDatasetStats")
print_method("previewDataset")
print_method("startMLTraining")
