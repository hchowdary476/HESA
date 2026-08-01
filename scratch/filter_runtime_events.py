import json

log_path = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\JARVIS\core\system\logs\runtime_events.jsonl"

try:
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    print("Found HESA/startup/speaking greeting events:")
    # Look through the last 500 lines for boot entries
    for line in lines[-500:]:
        try:
            data = json.loads(line)
            detail = data.get("detail", "")
            event_type = data.get("event_type", "")
            
            # Match startup, speaking, or details containing Hesa / Jarvis / siddhanga / active
            if (
                "siddhanga" in detail.lower() or 
                "hesa" in detail.lower() or 
                "startup" in event_type.lower() or 
                "speaking" in detail.lower() or
                "active" in detail.lower()
            ):
                print(f"[{data.get('timestamp')}] {event_type} - {data.get('severity')}: {detail}")
        except Exception:
            pass
except Exception as e:
    print(f"Error: {e}")
