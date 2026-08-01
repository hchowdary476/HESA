# Detailed Installation Guide for HESA (JARVIS)

This guide provides step-by-step instructions for setting up HESA (JARVIS) on Windows 10/11 systems.

---

## 📌 Prerequisites

1. **Python**: Python 3.10, 3.11, or 3.12 (64-bit). Ensure Python is added to your system `PATH`.
2. **Git**: Installed and available in terminal.
3. **Audio Hardware**: Working microphone input and speaker output.
4. **Ollama (Optional)**: If using local LLM inference, download and install [Ollama](https://ollama.ai/) and pull the Phi-3 model:
   ```cmd
   ollama pull phi3:latest
   ```

---

## ⚙️ Installation Steps

### Step 1: Clone Repository
```cmd
git clone https://github.com/your-org/open-jarvis.git
cd open-jarvis
```

### Step 2: Create Virtual Environment
```cmd
python -m venv .venv
.venv\Scripts\activate
```

### Step 3: Upgrade Pip & Install Dependencies
```cmd
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Environment Configuration
Copy `.env.example` to `.env`:
```cmd
copy .env.example .env
```
Edit `.env` using your text editor to insert your `GEMINI_API_KEY`, `GROQ_API_KEY`, or custom ports.

---

## 🔌 Windows Logon Auto-Launch Setup

To enable zero-touch automatic boot at Windows login:

1. Open Command Prompt as **Administrator**.
2. Run:
   ```cmd
   scripts\setup_autostart.bat
   ```
3. Or run the PowerShell registration script:
   ```powershell
   powershell -ExecutionPolicy Bypass -File create_task.ps1
   ```

---

## 🧪 Verification

Verify your installation by running the production audit suite:
```cmd
python scripts/run_production_feature_audit.py
```
If all 56 feature checks display `[PASS]`, your setup is fully verified and ready.
