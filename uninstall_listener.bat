@echo off
title JARVIS Listener — Uninstall
color 0C
echo.
echo  Removing JARVIS Listener and GUI from Windows startup...
python "%~dp0listener_service.py" --uninstall
python -c "import winreg; k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE); winreg.DeleteValue(k, 'JarvisCyberInterface')" >nul 2>&1
echo  Killing any running listener instances...
taskkill /F /FI "WINDOWTITLE eq JARVIS Listener*" /FI "IMAGENAME eq python.exe" >nul 2>&1
echo.
echo  Done. JARVIS Listener Service has been removed.
pause
