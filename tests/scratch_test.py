import os

from JARVIS.config.manager import ConfigManager


def main():
    config = ConfigManager()
    print("Settings file path:", config.paths.settings_file)
    if config.paths.settings_file.exists():
        print("Settings file exists!")
        with open(config.paths.settings_file) as f:
            print(f.read())
    else:
        print("Settings file does NOT exist.")

    os.environ["JARVIS_PRIVACY_MODE"] = "true"
    config.load()
    print("privacy.privacy_mode after loading:", config.get("privacy.privacy_mode"))


if __name__ == "__main__":
    main()
