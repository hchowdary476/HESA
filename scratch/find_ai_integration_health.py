filepath = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\JARVIS\gui\qml_bridge.py"

with open(filepath, "r", encoding="utf-8") as file:
    content = file.read()

if "aiIntegrationHealth" in content:
    print("Found 'aiIntegrationHealth' in content.")
    # Find matching lines
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        if "aiIntegrationHealth" in line:
            print(f"{idx+1}: {line}")
else:
    print("Not found 'aiIntegrationHealth'.")
