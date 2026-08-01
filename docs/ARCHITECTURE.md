# HESA (JARVIS) System Architecture Specification

This document details the multi-process architecture, process supervisor, voice pipeline, AI routing strategy, and state management of HESA (JARVIS).

---

## 🏛️ Architectural Overview

HESA (JARVIS) operates as an enterprise multi-process assistant system managed by a core Python Supervisor process.

```mermaid
graph TB
    subgraph Frontend Subsystem
        GUI[PySide6 / QML Main Window]
        Bridge[JarvisBridge QObject Signal Router]
        Tray[SystemTrayManager]
        GUI --- Bridge
        GUI --- Tray
    end

    subgraph Process Supervisor Core
        Supervisor[Process Supervisor Daemon]
        Health[Health & Telemetry Monitor]
        Supervisor --- Health
    end

    subgraph Daemons & Subsystems
        Voice[Voice Pipeline Daemon]
        AI[AI Orchestrator Failover Router]
        Memory[Multi-Tier Memory Engine]
        Auto[Automation & Shell Executor]
        Vision[OpenCV Vision Pipeline]
        Sec[Cyber Security Shield]
    end

    Supervisor --> Frontend Subsystem
    Supervisor --> Daemons & Subsystems

    Voice <--> AI
    AI <--> Memory
    AI <--> Auto
    Frontend Subsystem <--> Health
```

---

## 🛰️ Process Isolation & Single Instance Guard

1. **Named Mutex Lock**: The entry point `jarvis.py` requests `Local\JARVIS_GUI_SINGLETON_MUTEX_v2`. If another instance is running, it exits silently.
2. **Socket Lock Guard**: Port `19106` is bound during GUI execution. Duplicate launch attempts detect the bound port and terminate immediately.
3. **Supervisor Subprocess Management**: The supervisor launches background services using `pythonw.exe -m JARVIS.services.supervisor`, ensuring detached background execution without hanging shell windows.

---

## 🎙️ Voice & Audio Pipeline Architecture

```
Microphone PCM Stream (16kHz, 16-bit mono)
         │
         ▼
[OpenWakeWord ONNX Engine] ──(Detect "Hey JARVIS")──► [Barge-In Interrupt]
         │
         ▼
[Silero VAD Pipeline] ──(Detect Speech End)──► [Faster-Whisper STT]
                                                       │
                                                       ▼
                                            [Text Prompt to AI Router]
                                                       │
                                                       ▼
[Audio Output Speakers] ◄──[Edge / pyttsx3 TTS] ◄──[AI Response Text]
```

---

## 🧠 Hybrid AI Failover Routing Strategy

The `AIOrchestrator` determines response strategy based on query type, latency, and key availability:

1. **Local Ollama Daemon**: Used if active and model `phi3:latest` is loaded.
2. **Cloud APIs**: Switches to **Google Gemini** or **Groq** if cloud access is required or local daemon is busy.
3. **Offline Rules Engine**: Fallback intent classifier for system execution commands when offline.

---

## 🔐 Security & Sandbox Boundaries

- **Key Encryptor**: Fernet encryption protects sensitive memory tokens.
- **Permission Inspector**: Intercepts shell execution commands and verifies execution bounds.
- **Plugin Sandbox**: Plugins execute in isolated subprocess contexts without direct main thread access.
