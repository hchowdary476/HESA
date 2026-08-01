import os

root = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main"
found = []
for r, dirs, files in os.walk(root):
    for f in files:
        if f == "runtime_events.jsonl":
            found.append(os.path.join(r, f))

if found:
    print("Found files:")
    for path in found:
        print(path)
else:
    print("Not found.")
