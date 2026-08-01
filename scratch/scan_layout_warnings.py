import os

logs_dir = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\logs"
warnings = []
for f in os.listdir(logs_dir):
    if f.endswith(".log"):
        filepath = os.path.join(logs_dir, f)
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as file:
                lines = file.readlines()
            for line in lines:
                if "warning" in line.lower() or "qml" in line.lower() or "clipping" in line.lower():
                    warnings.append(f"{f}: {line.strip()}")
        except Exception:
            pass

print(f"Found {len(warnings)} potential warnings in logs:")
for w in warnings[:50]:
    print(w)
if len(warnings) > 50:
    print(f"... and {len(warnings) - 50} more")
