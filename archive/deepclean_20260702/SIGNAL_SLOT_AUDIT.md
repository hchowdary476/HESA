# Signal / Slot Audit Report

## 1. Scope
Detailed inventory of QML signals and Python slots supporting the reactive data loops of the JARVIS HUD.

---

## 2. Event Inventory

### Emitted Signals (Python ➔ QML)
- `metricsUpdated(cpu, ram, threads, services)`: Broadcasts real-time OS loads.
- `stateChanged(state)`: Updates UI state (LISTENING, STANDBY, SPEAKING).
- `logReceived(message, kind)`: Outputs lines to the Console log ListView.
- `clockUpdated(time)`: Synchronizes the holographic corner clock.
- `voiceEngineDiagnosticsChanged()`: Signals Voice status changes.
- `selfHealingStatusChanged()`: Emits health matrix modifications.
- `hybridAIStatusChanged(json)`: Updates multi-model configurations.

### Exposed Slots (QML ➔ Python)
- `submitCommand(text)`: Receives text instructions.
- `switchActiveModel(model_name)`: Updates inference provider.
- `takeSystemScreenshot()`: Triggers OS screenshot thread.
- `killProcess(pid)`: Terminates local windows task processes.
- `setSystemVolume(pct)` / `setSystemBrightness(pct)`: Alters hardware states.
