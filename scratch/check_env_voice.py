import os

env_path = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\.env"
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        print("Contents of .env:")
        for line in f:
            if "WAKE_WORD" in line or "VOICE" in line:
                print(f"  {line.strip()}")
else:
    print(".env file does not exist.")
