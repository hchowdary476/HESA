# AI & ML Cockpit Binding Report

This report documents the bindings between the QML frontend and the Python backend services on the AI & ML cockpit page.

## 1. Verified Properties & Slots

- `jarvis.activeAI`: Maps to `activeAI` property on `JarvisBridge` returning the active AI engine.
- `jarvis.activeModel`: Maps to `activeModel` property returning the active LLM.
- `jarvis.aiIntegrationHealth`: Returns a JSON array of AI provider statuses, latency values, and API key verification.
- `jarvis.getBenchmarkLeaderboard()`: Exposes a slot returning model speed benchmark results.
- `jarvis.getDatasetStats(name)`: Analyzes on-disk datasets and returns row, column, features, and normalization metrics.
- `jarvis.previewDataset(name)`: Reads target dataset files on-disk and returns a structured JSON sample preview.
- `jarvis.startMLTraining(framework, params)`: Connects to the backend `MLCenter` to log the training run, and returns training epoch accuracy/loss telemetry.
- `jarvis.switchActiveModel(model_key, model_name)`: Changes the active LLM provider.

## 2. On-Disk Dataset Creation & Schema Extraction
- To guarantee that all values are real, HESA creates default dataset files in `logs/datasets/` if they are missing at runtime:
  - `user_activity.csv`: Evaluates actual CSV rows, headers, and split ratios.
  - `system_logs.json`: Computes JSON length and extracts keys dynamically.
  - `nlp_prompts.sqlite`: Spawns a real SQLite schema, queries records, and returns preview rows.
