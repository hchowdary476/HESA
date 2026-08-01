@echo off
setlocal EnableDelayedExpansion

:: ============================================================
:: JARVIS GUI AUTO-STARTUP LAUNCHER
:: Fixed: launches GUI (not console backend), detached window,
::        retry logic, duplicate guard, full logging
:: ============================================================

:: Resolve PROJECT_DIR dynamically from this script's own location.
:: This script lives at <project root>\run_jarvis_startup.bat, so %~dp0
:: IS the project root (with trailing backslash — strip it with ~dp0..).
:: Do NOT hardcode any user path here.
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

set "LOG_FILE=%PROJECT_DIR%\logs\jarvis_autostart.log"
set "PYTHON_EXE=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "LOCK_FILE=%PROJECT_DIR%\logs\jarvis_gui.lock"

:: Ensure log directory exists
if not exist "%PROJECT_DIR%\logs" mkdir "%PROJECT_DIR%\logs"

echo [%date% %time%] ============================================ >> "%LOG_FILE%"
echo [%date% %time%] JARVIS Auto-Startup Sequence Initiated       >> "%LOG_FILE%"
echo [%date% %time%] ============================================ >> "%LOG_FILE%"

:: ── STEP 1: Wait for OneDrive / project directory (up to 5 min) ──────────────
set /a retries=0
:WaitForDir
if exist "%PROJECT_DIR%" goto DirReady
set /a retries+=1
if !retries! gtr 60 (
    echo [%date% %time%] ERROR: Project dir not found after 5 min. OneDrive may be offline. >> "%LOG_FILE%"
    exit /b 1
)
echo [%date% %time%] Waiting for project dir... attempt !retries!/60 >> "%LOG_FILE%"
timeout /t 5 /nobreak >nul
goto WaitForDir

:DirReady
echo [%date% %time%] Project directory found: %PROJECT_DIR% >> "%LOG_FILE%"

:: ── STEP 2: Duplicate instance guard ─────────────────────────────────────────
:: Check if a JARVIS GUI python process is already running
powershell -Command "if (Get-CimInstance Win32_Process -Filter 'Name LIKE ''python%%''' | Where-Object { $_.CommandLine -like '*jarvis.py*' }) { exit 0 } else { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    echo [%date% %time%] JARVIS GUI already running. Skipping duplicate launch. >> "%LOG_FILE%"
    exit /b 0
)
echo [%date% %time%] No existing JARVIS GUI instance detected. Proceeding... >> "%LOG_FILE%"

:: ── STEP 3: Verify virtual environment python exists ─────────────────────────
if not exist "%PYTHON_EXE%" (
    echo [%date% %time%] ERROR: venv python not found at %PYTHON_EXE% >> "%LOG_FILE%"
    echo [%date% %time%] Falling back to system python... >> "%LOG_FILE%"
    set "PYTHON_EXE=python"
)
echo [%date% %time%] Python executable: %PYTHON_EXE% >> "%LOG_FILE%"

:: ── STEP 4: Verify main entry point exists ───────────────────────────────────
:: The correct entry point is jarvis.py at the project root.
:: It initialises services, GUI, tray, and the supervisor subprocess.
:: Do NOT use -m JARVIS.gui.main_window — that bypasses all of the above.
if not exist "%PROJECT_DIR%\jarvis.py" (
    echo [%date% %time%] ERROR: jarvis.py not found at %PROJECT_DIR%\jarvis.py >> "%LOG_FILE%"
    exit /b 1
)

:: ── STEP 5: Set environment variables for PySide6/QML ───────────────────────
set "PYTHONPATH=%PROJECT_DIR%"
set "QT_QUICK_BACKEND=rhi"
set "QSG_RHI_BACKEND=d3d11"
set "QT_ENABLE_HIGHDPI_SCALING=1"
set "QT_QUICK_CONTROLS_STYLE=Basic"
set "JARVIS_MANAGED=0"

:: ── STEP 6: Launch GUI with retry logic ──────────────────────────────────────
:: Use START with /B to detach so cmd window doesn't block the GUI
:: pythonw.exe suppresses console flicker; use python.exe for better error capture
set /a attempt=0

:LaunchGUI
set /a attempt+=1
echo [%date% %time%] Launch attempt !attempt!/3 >> "%LOG_FILE%"

:: Launch jarvis.py as a detached process.
:: stdout/stderr go to a separate GUI log to prevent locking the main autostart log file.
start "JARVIS_GUI" /D "%PROJECT_DIR%" "%PYTHON_EXE%" "%PROJECT_DIR%\jarvis.py" >> "%PROJECT_DIR%\logs\jarvis_gui_startup.log" 2>&1

:: Wait 8 seconds (via ping sleep, since timeout doesn't support non-interactive shells)
ping -n 9 127.0.0.1 >nul

:: Check if process is running using standard PowerShell
set "GUI_RUNNING=0"
powershell -Command "if (Get-CimInstance Win32_Process -Filter 'Name LIKE ''python%%''' | Where-Object { $_.CommandLine -like '*jarvis.py*' }) { exit 0 } else { exit 1 }" >nul 2>&1
if not errorlevel 1 set "GUI_RUNNING=1"

if "!GUI_RUNNING!"=="1" (
    echo [%date% %time%] SUCCESS: JARVIS GUI process is running after attempt !attempt!. >> "%LOG_FILE%"
    goto LaunchSuccess
)

if !attempt! lss 3 (
    echo [%date% %time%] WARNING: GUI process not detected after attempt !attempt!. Retrying in 10s... >> "%LOG_FILE%"
    ping -n 11 127.0.0.1 >nul
    goto LaunchGUI
)

echo [%date% %time%] ERROR: JARVIS GUI failed to start after 3 attempts. Check logs. >> "%LOG_FILE%"
exit /b 1

:LaunchSuccess
echo [%date% %time%] JARVIS GUI Auto-Launch COMPLETE. >> "%LOG_FILE%"
echo [%date% %time%] Log: %LOG_FILE% >> "%LOG_FILE%"
endlocal
exit /b 0
