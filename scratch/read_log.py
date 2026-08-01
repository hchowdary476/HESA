import os

log_path = r"C:\Users\veera\.gemini\antigravity-ide\brain\23fc8385-d397-4d67-bd3b-6cdac1f5804f\.system_generated\tasks\task-929.log"
if os.path.exists(log_path):
    with open(log_path, "r", encoding="utf-8") as f:
        print(f.read())
else:
    print(f"Log path does not exist: {log_path}")
