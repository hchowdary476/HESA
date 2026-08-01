import re

filepath = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\JARVIS\gui\qml\DashboardPage.qml"
pattern = re.compile(r"\b(width|height|x|y|leftMargin|rightMargin|topMargin|bottomMargin|spacing|margins)\s*:\s*(\d+(\.\d+)?)\b")

with open(filepath, "r", encoding="utf-8") as file:
    lines = file.readlines()

results = []
for idx, line in enumerate(lines):
    match = pattern.search(line)
    if match:
        prop = match.group(1)
        val = match.group(2)
        if int(float(val)) > 15 or prop in ("width", "height", "x", "y"):
            results.append(f"{idx+1}: {line.strip()}")

print(f"Found {len(results)} hardcoded properties in DashboardPage.qml:")
for res in results:
    print(res)
