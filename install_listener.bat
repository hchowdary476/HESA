@echo off
title JARVIS Listener Service — Installer
color 0B
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║        JARVIS LISTENER SERVICE INSTALLER         ║
echo  ╚══════════════════════════════════════════════════╝
echo.

SET JARVIS_DIR=%~dp0
SET PYTHON_EXE=python

echo [1/4] Checking Python installation...
%PYTHON_EXE% --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo  ERROR: Python not found. Please install Python 3.9+
    pause
    exit /b 1
)
echo  OK: Python found.

echo [2/4] Installing required packages...
%PYTHON_EXE% -m pip install sounddevice numpy pystray Pillow pyaudio speechrecognition psutil --quiet
IF ERRORLEVEL 1 (
    echo  WARNING: Some packages may not have installed. Check manually.
) ELSE (
    echo  OK: Packages installed.
)

echo [3/4] Registering JARVIS Listener and Core GUI at Windows startup...
%PYTHON_EXE% "%JARVIS_DIR%listener_service.py" --install
%PYTHON_EXE% -c "import winreg; k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE); winreg.SetValueEx(k, 'JarvisCyberInterface', 0, winreg.REG_SZ, r'%JARVIS_DIR%run_jarvis_startup.bat')"
IF ERRORLEVEL 1 (
    echo  ERROR: Failed to register startup. Try running as Administrator.
    pause
    exit /b 1
)
echo  OK: Startup registered.

echo [4/4] Starting JARVIS Listener Service now...
start "" /B %PYTHON_EXE% "%JARVIS_DIR%listener_service.py" --hidden

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║   JARVIS LISTENER SERVICE INSTALLED SUCCESSFULLY ║
echo  ║                                                  ║
echo  ║  • Starts automatically on Windows login         ║
echo  ║  • Running in system tray right now              ║
echo  ║  • Double Clap  → Launch JARVIS                  ║
echo  ║  • Say "Jarvis" → Launch JARVIS                  ║
echo  ║                                                  ║
echo  ║  To uninstall: run uninstall_listener.bat        ║
echo  ╚══════════════════════════════════════════════════╝
echo.
pause
