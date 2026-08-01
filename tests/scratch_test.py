import os
from JARVIS.config.manager import ConfigManager
from JARVIS.core.memory.privacy_mode import memory_reads_enabled

def main():
    config = ConfigManager()
    print("Settings file path:", config.paths.settings_file)
    if config.paths.settings_file.exists():
        print("Settings file exists!")
        with open(config.paths.settings_file, "r") as f:
            print(f.read())
    else:
        print("Settings file does NOT exist.")
        
    os.environ["JARVIS_PRIVACY_MODE"] = "true"
    config.load()
    print("privacy.privacy_mode after loading:", config.get("privacy.privacy_mode"))

if __name__ == "__main__":
    main()
