# 🛠️ HESA (JARVIS) — Installation & Setup Guide

This guide covers complete installation instructions for setting up HESA (JARVIS) on Windows 10 and 11 systems.

---

## 📋 System Requirements

| Hardware / Software | Minimum Requirement | Recommended |
|---|---|---|
| **OS** | Windows 10 / 11 (64-bit) | Windows 11 (64-bit) |
| **Python** | Python 3.10 | Python 3.11 or 3.12 |
| **RAM** | 8 GB | 16 GB+ |
| **Storage** | 2 GB free disk space | 10 GB (for local LLM weights) |
| **Audio** | Standard Microphone & Speakers | USB Noise-Canceling Microphone |
| **GPU (Optional)** | N/A | NVIDIA GPU with CUDA support for faster local STT & LLM |

---

## 📥 Step-by-Step Installation

### Step 1: Clone Repository
```bash
git clone https://github.com/hchowdary476/HESA.git
cd HESA
```

### Step 2: Create Virtual Environment
Using Python 3.11+:
```cmd
python -m venv .venv
.venv\Scripts\activate
```

### Step 3: Install Dependencies
```cmd
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

*(For development or running tests, also run `pip install -r requirements-dev.txt`)*

### Step 4: Configure Environment Variables
Create your configuration file from the template:
```cmd
copy .env.example .env
```

Open `.env` in any editor and set appropriate values (e.g. `GEMINI_API_KEY`, `GROQ_API_KEY`, or leave blank for local mode).

### Step 5: (Optional) Set Up Local LLM (Ollama)
If you want complete offline AI capabilities without API keys:
1. Download and install [Ollama for Windows](https://ollama.ai/).
2. Pull the default Phi-3 model:
   ```cmd
   ollama pull phi3:latest
   ```
3. Ensure Ollama is running at `http://127.0.0.1:11434`.

---

## 🚀 Launching HESA

Launch HESA using the main controller:
```cmd
python jarvis.py
```

### Windows Startup Integration
To enable auto-start on logon:
```cmd
powershell -ExecutionPolicy Bypass -File create_task.ps1
```

---

## 🧪 Verification

Run the production audit suite to verify your installation:
```cmd
python scripts/run_production_audit.py
```
