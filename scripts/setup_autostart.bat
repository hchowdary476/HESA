@echo off
:: ============================================================
:: JARVIS AutoStart Setup — Zero-Touch Edition
::
:: Registers JARVIS to start silently at Windows logon using:
::   1. HKCU Registry Run key (primary - no admin, no CMD window)
::   2. Task Scheduler      (optional - enhanced retry/delay)
::
:: Run ONCE after installation. Does NOT need admin rights.
:: No pause, no CMD window, no UAC prompt at logon.
:: ============================================================
setlocal EnableDelayedExpansion

:: Resolve paths dynamically from this script's location
cd /d "%~dp0.."
set "JARVIS_ROOT=%cd%"
set "PYTHONW_EXE=%JARVIS_ROOT%\.venv\Scripts\pythonw.exe"
set "ENTRY_POINT=%JARVIS_ROOT%\jarvis.py"
set "REG_KEY=JARVIS_SilentBoot"
set "TASK_NAME=JARVIS_SilentBoot"

echo =====================================================
echo   JARVIS AutoStart Setup
echo   Root  : %JARVIS_ROOT%
echo   Python: %PYTHONW_EXE%
echo =====================================================
echo.

:: Validate pythonw.exe
if not exist "%PYTHONW_EXE%" (
    echo [ERROR] pythonw.exe not found. Recreate the virtual environment first.
    exit /b 1
)

:: Validate entry point
if not exist "%ENTRY_POINT%" (
    echo [ERROR] jarvis.py not found at: %ENTRY_POINT%
    exit /b 1
)

:: -----------------------------------------------------------
:: METHOD 1: HKCU Registry Run key (no admin, no popup)
:: -----------------------------------------------------------
echo [1/2] Setting HKCU Registry Run key...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" ^
    /v "%REG_KEY%" ^
    /t REG_SZ ^
    /d "\"%PYTHONW_EXE%\" \"%ENTRY_POINT%\"" ^
    /f >nul 2>&1

if %errorLevel% equ 0 (
    echo [OK]  Registry key set: HKCU\...\Run\%REG_KEY%
) else (
    echo [WARN] Failed to set registry key ^(error %errorLevel%^)
)

:: Clean up old keys from previous setups
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "JARVIS" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "JARVIS_AutoLaunch" /f >nul 2>&1

:: -----------------------------------------------------------
:: METHOD 2: Task Scheduler (retry logic, 15s delay)
:: -----------------------------------------------------------
echo.
echo [2/2] Registering Task Scheduler task...

:: Remove old conflicting user-owned tasks
schtasks /delete /tn "%TASK_NAME%"        /f >nul 2>&1
schtasks /delete /tn "JARVIS_AutoStart"   /f >nul 2>&1

:: Register using schtasks /rl limited = no UAC at logon
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "\"%PYTHONW_EXE%\" \"%ENTRY_POINT%\"" ^
    /sc onlogon ^
    /ru "%USERNAME%" ^
    /rl limited ^
    /delay "0000:15" ^
    /f >nul 2>&1

if %errorLevel% equ 0 (
    echo [OK]  Task Scheduler: %TASK_NAME% ^(15s delay, limited privilege^)
) else (
    echo [WARN] Task Scheduler registration failed.
    echo        An old admin-elevated task may be blocking this.
    echo        Run the following in an ELEVATED PowerShell to clear it:
    echo            Unregister-ScheduledTask -TaskName 'JARVIS Auto Start' -Confirm:$false
    echo        Then re-run this script.
    echo        The Registry Run key ^(Method 1^) IS active and sufficient.
)

echo.
echo =====================================================
echo   Setup complete.
echo   JARVIS will auto-start silently at next logon.
echo =====================================================
endlocal
exit /b 0
