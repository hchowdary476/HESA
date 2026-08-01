# ARCHITECTURE PLAN - JARVIS V4

This document defines the architectural transition of J.A.R.V.I.S from a monolithic Python GUI application to a modern multi-process AI Operating System using **Tauri (Rust)**, **React + TypeScript (Frontend)**, and **Python (AI and Voice Core)**.

---

## 1. Current Architecture (V3)
The current J.A.R.V.I.S implementation is single-process-centric, where:
- **GUI Layer:** CustomTkinter + PIL image asset loaders block or coordinate directly in the Python main thread.
- **System Layer:** Python `psutil`, `sounddevice`, `pyaudio`, and shell scripts interact with the OS and handle hardware probes.
- **AI Core:** Handled in Python via Ollama integrations, local transcription, short/long-term memory buffers, and Groq fallback endpoints.
- **Voice Core:** edge-tts audio streaming and local sound playback (via MCI players) coordinated synchronously or with simple threads.

---

## 2. Target Architecture (V4)
J.A.R.V.I.S V4 splits the application into three decoupled layers:

### A. Frontend Layer (React + TypeScript + Tauri)
- **Host Wrapper:** Tauri provides a secure, lightweight webview container (using WebView2 on Windows) that replaces CustomTkinter.
- **Interface UI:** Single Page App built with React, Styled Components, and TypeScript.
- **Visuals:** Modern Iron-Man HUD, high-fidelity real-time voice waveforms, and a living 60 FPS face avatar compiled using HTML5 Canvas / WebGL.
- **Interactions:** User commands and keyboard shortcuts are forwarded instantly to the core via Tauri events and WebSocket bridges.

### B. System Layer (Rust Core)
- **Tauri Main App:** Executable that initializes windows, handles startup parameters, and manages the lifecycle of the Python sidecar.
- **Process & File Manager:** Performance-optimized file search, directory safety checks, and subprocess launching in native Rust.
- **System Monitoring:** Periodic CPU, RAM, and hardware metrics collected using lightweight Rust crates (`sysinfo`, `local_ipaddress`) replacing `psutil`.
- **Security & Sandboxing:**
  - Standardized Tauri commands mapping for file and shell access.
  - Verification of plugin digital signatures in Rust before execution.
  - Strict sandboxing using Tauri's built-in scopes and IPC controls.

### C. AI & Voice Core (Python Sidecar)
- **Execution:** Spanned as a lightweight background daemon process by the Tauri host.
- **AI Router & Memory:** Houses LLM reasoning (Ollama/Groq), RAG document queries, and long-term memory SQLite/vector storage.
- **Voice Engine:** Speech Recognition (Whisper / Vosk) and TTS (edge-tts) are maintained in Python to keep ML/audio model compatibility intact.
- **IPC communication:** Listens on a local loopback WebSocket server and REST API for high-speed, local inter-process message exchange.

---

## 3. Communication Architecture

### A. WebSocket Interface (Real-time Events)
- **Port:** `localhost:8999` (secure token-authorized loopback).
- **Direction:** Bidirectional.
- **Usage:** Real-time speech transcription chunks, active speaking text for avatar lip sync, and real-time audio waveform amplitude updates.

### B. REST API (Request-Response commands)
- **Port:** `localhost:8999/api/v1`
- **Endpoints:**
  - `POST /commands`: Sends text commands to the Automation Engine.
  - `GET /memory`: Queries notes and user memories.
  - `POST /settings`: Updates AI modes, voice options, or permission profiles.

### C. Tauri IPC (Secure Frontend-Backend)
- Tauri commands (`tauri::command`) handle frontend requests that touch the OS, bypassing Python entirely for local desktop tasks (e.g. volume adjustment, file searches, screenshot captures).
