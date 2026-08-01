# DEPENDENCY MAP - JARVIS V4

This document maps all the packages, libraries, and native modules needed across Python, Rust, and Node.js in the J.A.R.V.I.S V4 architecture.

---

## 1. Python Dependencies (AI & Voice Core)
These dependencies are maintained in the Python virtual environment, specifically for background AI reasoning, audio models, and WebSockets.

| Package | Version | Purpose | Core Subsystem |
| :--- | :--- | :--- | :--- |
| **`groq`** | `^0.9.0` | Cloud LLM processing | `ai_core` (AI Router) |
| **`spotipy`** | `^2.23.0` | Music player API integration | `ai_core` (Automation) |
| **`python-dotenv`**| `^1.0.1` | Environment configurations | Core-wide |
| **`speechrecognition`** | `^3.10.4` | Audio capture wrapper | `voice_core` (Speech Recognition) |
| **`edge-tts`** | `^6.1.9` | High-quality text-to-speech | `voice_core` (TTS Engine) |
| **`sounddevice`** | `^0.4.6` | Microphone audio device polling | `voice_core` (Mic Diagnostics) |
| **`vosk`** | `^0.3.45` | Offline speech-to-text fallback | `voice_core` (STT Fallback) |
| **`websockets`** | `^12.0` | Real-time loopback communication | `communication` |

---

## 2. Rust Dependencies (System Layer & Tauri Wrapper)
These dependencies are managed by Cargo inside the `src-tauri/Cargo.toml` directory.

| Crate | Purpose | Core Subsystem |
| :--- | :--- | :--- |
| **`tauri`** | Tauri desktop framework host | `system_core` |
| **`tauri-build`** | Build-time compilation configurations | Build |
| **`serde`** / **`serde_json`** | Fast JSON serialization for IPC messages | `system_core` |
| **`sysinfo`** | Lightweight system usage scanner | `system_core` (System Monitoring) |
| **`tokio`** | Multi-threaded async runtime | `system_core` (IPC & Sidecars) |
| **`winreg`** | Windows Registry manager | `system_core` (Startup Manager) |
| **`aes-gcm`** / **`pbkdf2`** | Secure encryption and key stretching | `system_core` (Security Services) |

---

## 3. Frontend Dependencies (React + TypeScript HUD)
These packages are managed by npm/yarn inside the `package.json` file in the frontend folder.

| Package | Purpose | Core Subsystem |
| :--- | :--- | :--- |
| **`react`** / **`react-dom`** | Main UI view library | `frontend` |
| **`typescript`** | Type safety and autocompletion | `frontend` |
| **`@tauri-apps/api`** | Client interface wrapper for Tauri commands | `frontend` (IPC connector) |
| **`styled-components`** | Visual elements styling | `frontend` |
| **`lucide-react`** | High-fidelity Iron-Man visual vectors | `frontend` (UI Icons) |
