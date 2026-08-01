# HESA (JARVIS) Troubleshooting Guide

This document contains solutions for common operational and installation issues.

---

## 🔍 Log File Locations

- **Startup & Launcher Logs**: `logs/startup.log`
- **GUI & Traceback Logs**: `logs/gui_traceback.log`
- **Heartbeat & Telemetry Logs**: `logs/heartbeats/`
- **Feature Audit Results**: `logs/feature_audit_results.json`

---

## 🛠️ Common Issues & Fixes

### 1. GUI Exits Immediately After Launch
- **Cause**: A duplicate instance of JARVIS is already running in the background.
- **Fix**: Check your Windows Task Tray for the JARVIS icon, or end existing Python processes via Task Manager:
  ```cmd
  taskkill /F /IM python.exe /IM pythonw.exe
  ```

### 2. Microphone Input Not Detected
- **Cause**: Audio device permissions disabled or incorrect default recording device.
- **Fix**: Ensure Windows Settings $\rightarrow$ Privacy & Security $\rightarrow$ Microphone permissions are allowed for desktop applications.

### 3. OpenWakeWord Initialization Error
- **Cause**: ONNX models missing from virtual environment cache.
- **Fix**: Download base models manually by running:
  ```cmd
  python -c "import openwakeword; openwakeword.utils.download_models()"
  ```

### 4. Ollama Local LLM Connection Refused
- **Cause**: Ollama daemon is not running on `http://127.0.0.1:11434`.
- **Fix**: Start Ollama desktop or run `ollama serve` in a terminal window.

### 5. Task Scheduler Fails at Logon
- **Cause**: Permission denial or UAC elevation blocking GUI rendering.
- **Fix**: Ensure `create_task.ps1` was registered with `-RunLevel Limited` and `-LogonType Interactive` so it executes in your user session.
