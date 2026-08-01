import os
import re

qml_dir = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\JARVIS\gui\qml"
pattern = re.compile(r"\b(width|height|x|y|leftMargin|rightMargin|topMargin|bottomMargin|spacing|margins)\s*:\s*(\d+(\.\d+)?)\b")

results = []
for r, dirs, files in os.walk(qml_dir):
    for f in files:
        if f.endswith(".qml"):
            filepath = os.path.join(r, f)
            with open(filepath, "r", encoding="utf-8") as file:
                lines = file.readlines()
            for idx, line in enumerate(lines):
                match = pattern.search(line)
                if match:
                    prop = match.group(1)
                    val = match.group(2)
                    # Ignore standard small/common values like margins: 0, border.width: 1, spacing: 0, index-like offsets
                    if int(float(val)) > 15 or prop in ("width", "height", "x", "y"):
                        results.append(f"{f}:{idx+1}: {line.strip()}")

print(f"Found {len(results)} hardcoded properties:")
for res in results[:100]:
    print(res)
if len(results) > 100:
    print(f"... and {len(results) - 100} more")
