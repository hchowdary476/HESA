import re

filepath = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\JARVIS\gui\qml\AIMLPage.qml"

with open(filepath, "r", encoding="utf-8") as file:
    content = file.read()

# Find references to jarvis.<property> or jarvis.<method>()
matches = re.findall(r"jarvis\.[a-zA-Z0-9_]+(?:\([^\)]*\))?", content)

print(f"Found {len(matches)} references to jarvis:")
for m in sorted(list(set(matches))):
    print(f"  {m}")
