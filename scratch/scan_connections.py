filepath = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\JARVIS\gui\qml\DashboardPage.qml"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.splitlines()
print("Connections in DashboardPage.qml:")
inside = False
brace_count = 0
for idx, line in enumerate(lines):
    if "Connections {" in line or "Connections{" in line:
        inside = True
        brace_count = 0
    if inside:
        print(f"  {idx+1}: {line}")
        brace_count += line.count("{") - line.count("}")
        if brace_count == 0 and idx > 0 and ("}" in line or "Connections" in line):
            inside = False
            print()
