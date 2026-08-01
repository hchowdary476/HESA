# TASK RECOVERY ENGINE SPECIFICATION

Details the self-healing and recovery loops of JARVIS.

---

## 1. Exception Log Auditing

If a background task raises an exception, the Task Recovery Engine parses the traceback logs:
- `ModuleNotFoundError`: triggers automatic `pip install <module>`.
- `ConnectionRefusedError` / `TimeoutError`: triggers socket reset check and retry.
- `PermissionError`: logs a security exception requiring user elevated confirmation.

## 2. Checkpoint Restore

Saves state metadata to `logs/mission_control_state.json`. If a worker thread restarts, it parses the JSON dump and resumes execution from the last completed subtask.
