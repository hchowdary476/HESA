import winreg
import os
import sys

def set_autostart():
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    value_name = "JARVIS_AutoLaunch"
    
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    startup_bat = os.path.join(root_dir, "run_jarvis_startup.bat")
    target_cmd = f'cmd.exe /c "{startup_bat}"'

    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
    
    # Clean old keys
    for old in ["JARVIS", "JARVIS_SilentBoot"]:
        try:
            winreg.DeleteValue(key, old)
            print(f"Removed legacy key: {old}")
        except FileNotFoundError:
            pass

    winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, target_cmd)
    winreg.CloseKey(key)
    print(f"Set registry key '{value_name}' -> '{target_cmd}' successfully.")

if __name__ == "__main__":
    set_autostart()
