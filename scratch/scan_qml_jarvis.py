import os
import re

qml_dir = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\JARVIS\gui\qml"
files = [f for f in os.listdir(qml_dir) if f.endswith(".qml")]

# Find "jarvis" case insensitively as a word, but ignore JarvisFont and jarvis. references
results = []
for file in files:
    path = os.path.join(qml_dir, file)
    with open(path, "r", encoding="utf-8") as fh:
        for idx, line in enumerate(fh, 1):
            # Check for occurrences of "jarvis" or "JARVIS" (excluding JarvisFont or jarvis. property calls)
            # We can search case-insensitively for the word "jarvis"
            matches = re.findall(r'\bjarvis\b', line, re.IGNORECASE)
            # Also check if it contains "JARVIS" as part of a larger string literal
            if matches:
                # Let's inspect the line. If it's a property call like jarvis.xxx or JarvisFont.xxx, we ignore it.
                stripped = line.strip()
                if "JarvisFont" in stripped:
                    continue
                # If it is like "target: jarvis" or "value: jarvis" or "jarvis.kill" or "onClicked: jarvis."
                if re.search(r'\bjarvis\.', stripped) or re.search(r'target:\s*jarvis\b', stripped) or re.search(r'value:\s*jarvis\b', stripped) or re.search(r'model:\s*jarvis\b', stripped):
                    continue
                results.append((file, idx, stripped))

with open(r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\scratch\qml_scan_results.txt", "w", encoding="utf-8") as out:
    out.write(f"Found {len(results)} user-facing QML matches:\n")
    for file, line_no, content in results:
        out.write(f"{file}:{line_no} -> {content}\n")

print(f"Completed scan. Found {len(results)} matches. Results written to scratch/qml_scan_results.txt.")
