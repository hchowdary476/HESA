import os

brain_dir = r"C:\Users\veera\.gemini\antigravity-ide\brain\23fc8385-d397-4d67-bd3b-6cdac1f5804f"
print("Scanning for log files under brain dir:")
for root, dirs, files in os.walk(brain_dir):
    for f in files:
        if "929" in f or f.endswith(".log"):
            fp = os.path.join(root, f)
            print(f"  {f}: {fp}")
