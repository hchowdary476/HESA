import re

html_path = 'JARVIS/gui/jarvis_os/jarvis_os.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace visible text and classes
# 1. Title
content = content.replace("<title>JARVIS — Core OS", "<title>HESA — Core OS")
# 2. CSS classes
content = content.replace(".jarvis-brand", ".hesa-brand")
content = content.replace("class=\"jarvis-brand\"", "class=\"hesa-brand\"")
content = content.replace("document.querySelector('.jarvis-brand')", "document.querySelector('.hesa-brand')")
content = content.replace(".chat-msg.jarvis", ".chat-msg.hesa")
content = content.replace("class=\"chat-msg jarvis\"", "class=\"chat-msg hesa\"")
content = content.replace("appendMessage(\"jarvis\"", "appendMessage(\"hesa\"")
# 3. Logo core
content = content.replace("<span>JARVIS</span>", "<span>HESA</span>")
# 4. Visible texts
content = content.replace("JARVIS CONSCIOUSNESS", "HESA CONSCIOUSNESS")
content = content.replace("JARVIS CONSOLE STREAM", "HESA CONSOLE STREAM")
content = content.replace("JARVIS is processing...", "HESA is processing...")
content = content.replace("id=\"jarvis-notes\"", "id=\"hesa-notes\"")
content = content.replace("document.getElementById(\"jarvis-notes\")", "document.getElementById(\"hesa-notes\")")
content = content.replace("jarvis_tactical_notes", "hesa_tactical_notes")
content = content.replace("JARVIS SYSTEM CONFIGURATION CONSOLE", "HESA SYSTEM CONFIGURATION CONSOLE")
content = content.replace("placeholder=\"e.g. jarvis\"", "placeholder=\"e.g. hesa\"")
content = content.replace("defaultValue = \"jarvis\"", "defaultValue = \"hesa\"")
content = content.replace("[BOOT] JARVIS v7.0 ONLINE", "[BOOT] HESA v7.0 ONLINE")
content = content.replace("SYSTEM INITIALIZED. JARVIS v7.0 ON-STANDBY", "SYSTEM INITIALIZED. HESA v7.0 ON-STANDBY")
content = content.replace("Activation phrase: 'Jarvis'", "Activation phrase: 'Hesa'")
content = content.replace("generateJarvisReply", "generateHesaReply")
content = content.replace("JARVIS RESPONSE", "HESA RESPONSE")
content = content.replace("I am JARVIS, your integrated cybernetic operating system", "I am HESA, your integrated cybernetic operating system")
content = content.replace("WARNING: JARVIS entered Safe Mode", "WARNING: HESA entered Safe Mode")
content = content.replace("getValue(\"Voice\", \"voice.wake_word\", \"jarvis\")", "getValue(\"Voice\", \"voice.wake_word\", \"hesa\")")
content = content.replace("name: \"Jarvis-Web\"", "name: \"Hesa-Web\"")
content = content.replace("Hello JARVIS status report", "Hello HESA status report")
content = content.replace("/* ?? JARVIS CONSOLE LOGGER", "/* ?? HESA CONSOLE LOGGER")
content = content.replace("[JARVIS] Vitals card clicked", "[HESA] Vitals card clicked")
content = content.replace("[JARVIS] Agent row clicked", "[HESA] Agent row clicked")
content = content.replace("[JARVIS] Self-healed event handler", "[HESA] Self-healed event handler")
content = content.replace("[JARVIS] Interaction event on element", "[HESA] Interaction event on element")
content = content.replace("logConsole(`[JARVIS] ", "logConsole(`[HESA] ")

# Exposing boot completed notification to python
# Let's add call to on_boot_complete in completeBoot()
content = content.replace('logConsole("SYSTEM INITIALIZED. HESA v7.0 ON-STANDBY.");', 
                          'logConsole("SYSTEM INITIALIZED. HESA v7.0 ON-STANDBY.");\n      if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.on_boot_complete === "function") {\n        window.pywebview.api.on_boot_complete();\n      }')

content = content.replace('function skipBoot() {\n      completeBoot();\n    }',
                          'function skipBoot() {\n      if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.on_boot_complete === "function") {\n        window.pywebview.api.on_boot_complete();\n      } else {\n        completeBoot();\n      }\n    }')

# Also define window.hesaCommand to call jarvisCommand or map both
content = content.replace("window.jarvisCommand = function(cmd) {",
                          "window.hesaCommand = window.jarvisCommand = function(cmd) {")

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Rebranding of jarvis_os.html completed successfully!")
