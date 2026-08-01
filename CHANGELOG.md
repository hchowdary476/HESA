# 📜 Changelog

All notable changes to the HESA (JARVIS) AI Assistant project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-08-01

### 🌟 Added
- **Holographic QML Interface**: PySide6 / QML cyber-aesthetic UI with 6 live monitoring pages, system tray integration, and customizable themes.
- **Single-Instance Boot Engine**: Consolidated Win32 Mutex guard and Windows logon auto-start via Registry and Task Scheduler (`create_task.ps1`).
- **Hybrid AI Router**: Adaptive failover cascading across Google Gemini, Groq Cloud, local Ollama (Phi-3), and deterministic offline rules.
- **Zero-Latency Voice Pipeline**: OpenWakeWord engine (ONNX), Silero VAD, Faster-Whisper offline STT, and Edge-TTS synthesis.
- **Distributed Memory System**: SQLite long-term storage, JSON working memory, and Knowledge Graph semantic index with TF-IDF search.
- **Security Shield**: Fernet AES-128 key encryption, command/path safety layer, and sandboxed plugin runtime.
- **Open Source Infrastructure**: Standardized `.gitignore`, `.env.example`, full documentation suite in `docs/`, GitHub Actions CI pipeline, and community guidelines.

### 🧪 Verified
- **100% PASS** on all unit and integration test suites (`tests/`).
- Clean repository verification with zero exposed secrets or temporary build artifacts.
