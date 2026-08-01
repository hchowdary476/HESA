# BACKGROUND EXECUTION ENGINE SPECIFICATION

Details the design of the non-blocking execution loop in JARVIS.

---

## 1. Concurrency Management

- Utilizes python daemon threads `threading.Thread(..., daemon=True)` and system process managers (`subprocess.Popen`).
- Guarantees zero blocking of the main UI loop or QML layout engine.
- Manages connection states and socket binds efficiently to limit file handle overhead.

## 2. Resource Telemetry Monitor

Tracks the following metrics on every interval tick:
- CPU utilization percentage.
- Memory/RSS limits.
- System thread counts.
- Active agent processing speed.
