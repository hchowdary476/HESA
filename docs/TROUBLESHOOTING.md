# 🔧 HESA Troubleshooting Guide

Common issues and solutions for running HESA (JARVIS).

---

## 🎙️ Voice & Audio Troubleshooting

### 1. Wake word is not triggering ("Hey JARVIS")
- **Cause**: Microphone gain too low or sensitivity threshold set too high.
- **Solution**: Lower `JARVIS_WAKE_THRESHOLD` in `.env` (e.g. from `0.72` to `0.55`).
- Check default recording device in Windows Sound Control Panel.

### 2. Edge-TTS playback fails or sounds robotic
- **Cause**: Network disconnection or Edge-TTS cloud service timeout.
- **Solution**: HESA automatically falls back to SAPI5 `pyttsx3`. Check your internet connection or force offline TTS by setting `JARVIS_TTS_PROVIDER=pyttsx3` in `.env`.

---

## 🤖 AI Routing & Model Troubleshooting

### 1. `Gemini API key missing` warning in logs
- **Cause**: `GEMINI_API_KEY` is empty in `.env`.
- **Solution**: Insert a valid key from Google AI Studio into `.env`, or rely on local Ollama by running `ollama run phi3:latest`.

### 2. Local Ollama queries timing out
- **Cause**: Ollama server not running or system under high RAM load.
- **Solution**: Open terminal and verify Ollama is active: `curl http://127.0.0.1:11434`.

---

## 🖥️ QML GUI & Display Issues

### 1. Window fails to open or exits immediately
- **Cause**: PySide6 QML plugin DLL path resolution failure on Windows logon.
- **Solution**: Launch via `python jarvis.py` directly from an active virtual environment.

---

## 📝 Diagnostic Logs

Diagnostic log outputs are stored in `logs/`:
- `logs/startup.log`: System boot logs
- `logs/supervisor.log`: Process manager logs
- `logs/ai_router.log`: LLM routing decisions
- `logs/stt.log`: Speech recognition outputs
