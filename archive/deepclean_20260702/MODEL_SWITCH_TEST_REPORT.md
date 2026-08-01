# Model Switching Test Report

## Overview
This report verifies that switching AI models inside the Cockpit updates the Dashboard Active AI card instantly and persists selections across restarts.

## Verification Details

### 1. Dashboard Synchronization (Task 4)
When a user clicks "SWITCH TO MODEL", the following backend updates are performed instantly in `JarvisBridge` without requiring a application restart:
- **Active AI & Model Name**: Sets the display name and active provider.
- **Latency & Status**: Maps and updates default latency baseline (e.g. 120ms for Gemini, 12ms for Ollama) and status ("Online" or "Standby").
- **Signal Broadcast**: Emits QML notify signals:
  - `activeAIChanged` -> triggers refresh on Dashboard Active AI card
  - `activeModelChanged` -> triggers refresh on Dashboard Model card
  - `apiStatusChanged` -> triggers refresh on Dashboard Status card
  - `latencyMsChanged` -> triggers refresh on Dashboard Latency card

### 2. Configuration Persistence (Task 5)
- Model choices are persisted using `ConfigManager` inside the `switchActiveModel` slot.
- Saves the following properties to `settings.json`:
  - `"ai.active_model"`: The active model's display name.
  - `"ai.active_provider"`: The active model's provider.
- On startup, the constructor of `JarvisBridge` loads the settings and automatically restores the active AI state in the orchestrator, propagating the data to the dashboard instantly.

## Test Matrix

| Target Model | Provider | Expected Latency | Expected Status | Persistence OK | Dashboard Sync OK |
| :--- | :--- | :---: | :---: | :---: | :---: |
| ChatGPT 4o | OpenAI | 165 ms | ONLINE | Yes | Yes |
| Gemini 1.5 Pro | Google | 120 ms | ONLINE | Yes | Yes |
| Claude 3.5 Sonnet | Anthropic | 180 ms | ONLINE | Yes | Yes |
| Grok 3 | xAI | 145 ms | ONLINE | Yes | Yes |
| DeepSeek R1 | DeepSeek | 250 ms | ONLINE | Yes | Yes |
| Ollama (Llama 3) | Local | 12 ms | STANDBY | Yes | Yes |
| LM Studio (Mistral) | Local | 14 ms | STANDBY | Yes | Yes |
