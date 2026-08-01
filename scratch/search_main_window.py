filepath = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\JARVIS\gui\main_window.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.splitlines()
print("Search results:")
for idx, line in enumerate(lines):
    if "callback" in line.lower() or "bridge" in line.lower() or "setup_gui" in line.lower():
        print(f"  {idx+1}: {line.strip()}")
