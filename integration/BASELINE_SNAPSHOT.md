# AIMLPage.qml Cockpit Baseline Snapshot — 2026-07-02

This snapshot lists every existing button, interactive control, and sub-tab on the `AIMLPage.qml` cockpit before applying the Multi-Agent Core changes.

## 1. Sidebar Navigation (Left Panel)
* **Tab Selection MouseArea:** Cycles `activeSubTab` value through 12 options:
  1. AI Model Hub (`model_hub`)
  2. Local LLM Manager (`llm_manager`)
  3. Dataset Manager (`dataset_mgr`)
  4. Training Center (`training_ctr`)
  5. AI Playground (`playground`)
  6. AI Agents Pool (`agents_mgr` / `agents_core`)
  7. Computer Vision (`vision_ai`)
  8. Speech AI (`speech_ai`)
  9. Reinforcement RL (`reinforce_rl`)
  10. Benchmark Lab (`benchmark_ctr`)
  11. Research Lab (`research_lab`)
  12. Prompt Library (`prompt_lib`)

## 2. Interactive Sections & Buttons

### Section 1: AI Model Hub
* **Button "SAVE PROVIDER SETTINGS"** (line 287): Triggers settings persistence and logging.

### Section 2: Local LLM Manager
* **Button "RELOAD MODELS"** (line 331): Emits local Ollama model refresh signal.
* **Button "CONNECT HOST"** (line 345): Triggers LM Studio local port check.

### Section 3: Dataset Ingestion & Feature Store
* **Button "ANALYZE DATASET"** (line 369): Sets `analyzingDataset = true` and shows file details.

### Section 4: Training Center (Model Optimization)
* **Button "RUN MODEL OPTIMIZATION"** (line 455): Toggles `isTraining` state and starts training chart updates.

### Section 5: AI Playground
* **Button "RUN PLAYGROUND QUERY"** (line 599): Runs playground prompt comparison checks.

### Section 6: Multi-Agent Core Panel (AI Agents Pool)
* **Kill-Switch Toggle Button** (line 740): Toggles agent system state (`ON`/`OFF`) via `jarvis.setAgentsEnabled()`.
* **Button "▶ RUN"** (line 818): Submits task prompt to orchestrator via `jarvis.runAgentTask()`.
* **Button "CLEAR"** (line 836): Wipes log history via `jarvis.clearAgentLog()`.

### Section 7: Computer Vision (YOLO & MediaPipe)
* **Button "INITIALIZE COMPUTER VISION SUB-LAYERS"** (line 1096).

### Section 9: Reinforcement RL
* **Button "RUN ITERATION STEP"** (line 1161).

### Section 11: Research Lab
* **Button "EXPORT BENCHMARK PDF REPORT"** (line 1227).

### Section 12: Prompt Library
* **Button "INJECT PROMPT TO PLAYGROUND"** (line 1259).
