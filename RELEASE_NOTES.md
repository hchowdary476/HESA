# 🚀 HESA (JARVIS) v1.0.0 Release Notes

We are thrilled to announce the official open-source release of **HESA (JARVIS) v1.0.0**!

HESA is an enterprise-grade, privacy-first, autonomous AI desktop assistant for Windows.

---

## 🌟 Release Highlights

- 🎙️ **Zero-Latency Voice Core**: Powered by custom ONNX OpenWakeWord, Silero VAD, and Faster-Whisper offline STT.
- 🧠 **Adaptive Multi-LLM Routing**: Automatic failover between Google Gemini, Groq Cloud, local Ollama (Phi-3), and deterministic offline rules.
- 📊 **Holographic QML Interface**: PySide6 QML user interface featuring live telemetry, active AI model monitoring, and system tray integration.
- 💾 **Distributed Memory Engine**: SQLite long-term storage, JSON working memory, and Knowledge Graph semantic search index.
- 🛡️ **Security Shield**: Fernet AES-128 key encryption, command/path safety verification, and isolated plugin sandboxing.

---

## 📦 Migration & Asset Information

- **Release Version**: `v1.0.0`
- **Git Tag**: `v1.0.0`
- **Portable Distribution Artifacts**: Large pre-packaged binaries are hosted on the [GitHub Release Assets](https://github.com/hchowdary476/HESA/releases/tag/v1.0.0) page to maintain repository lightness.

---

## 🛠️ Quick Start

```cmd
git clone https://github.com/hchowdary476/HESA.git
cd HESA
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python jarvis.py
```
