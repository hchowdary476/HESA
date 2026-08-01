import json

log_path = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\JARVIS\core\system\logs\runtime_events.jsonl"

try:
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    print(f"Total entries: {len(lines)}")
    print("Most recent 15 entries:")
    # Print the last 15 entries
    for line in lines[-15:]:
        # Try formatting as pretty JSON
        try:
            data = json.loads(line)
            print(json.dumps(data, indent=2))
        except Exception:
            print(line.strip())
except Exception as e:
    print(f"Error: {e}")
