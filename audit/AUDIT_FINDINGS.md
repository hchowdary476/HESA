# JARVIS Audit — Findings

**Date:** 2026-07-01  
**Scope:** Full codebase scan — 185 Python files + 19 QML files + requirements.txt + qmldir  
**Python syntax check result:** ALL 185 files PASS `py_compile` — no syntax errors  

---

## Findings Table

| ID | Area | File(s) | Issue | Severity | Suggested Fix Tier |
|----|------|---------|-------|----------|--------------------|
| F-01 | QML Registration | `qml/qmldir` | `AIMLPage.qml` exists (53 KB) and is used in `main.qml` (line 40, 168) and navigated from `BottomDock.qml` (`key: "ai_ml"`), but is **not declared in `qmldir`**. Qt resolves it via filesystem fallback, but this is fragile — broken in any packaged/installed deployment. | HIGH | Tier 1 |
| F-02 | QML Registration | `qml/qmldir` | `SecurityPage.qml` is declared in `qmldir` (line 27) and has full QML content, but is **never instantiated in `main.qml`** and is not reachable via any navigation key in `BottomDock.qml`. It is dead/orphaned code. | LOW | Tier 1 |
| F-03 | Python Bug — Variable NameError | `JARVIS/gui/qml_bridge.py` L682 | In `_start_metrics_worker._loop()`, the system status dict is loaded into local variable `data` (line 416), but line 682 calls `self._compute_active_modules_cache(status_data)` — referencing the **undefined** name `status_data`. The `try/except Exception: pass` at L681 silently swallows the `NameError` every ~1 second, causing `_compute_active_modules_cache` to always fall back to reading the disk file instead of using the already-loaded dict. This wastes I/O on every metrics tick and defeats the worker-thread optimization comment at L703–707. | MEDIUM | Tier 2 |
| F-04 | Logic Bug — Dead Else Branch | `JARVIS/gui/qml_bridge.py` L830 | Knowledge Graph self-healing check: `kg_status = "PASS" if ... else "PASS"` — both branches of the conditional return `"PASS"`. The `else "PASS"` is a tautology; the status can never be `"FAIL"`. This means the self-healing dashboard will always show Knowledge Graph as healthy even when it isn't. | LOW | Tier 1 |
| F-05 | Dead Code — No-op Replacements | `refactor.py` (root) | All `replacements` in `refactor.py` map module paths to themselves (e.g., `"JARVIS.gui": "JARVIS.gui"`), making every `replace_in_files()` call a no-op. The script also calls `replace_in_files()` twice (lines ~45 and ~50) and calls `print("Refactoring complete.")` twice. This is a leftover migration script with no effect. | LOW | Tier 1 |
| F-06 | Dead Constant | `JARVIS/gui/main_window.py` L44 | `STARTUP_GREETING` is defined at module level but never used anywhere in the file. It was likely intended to be passed to the bridge or TTS. | LOW | Tier 1 |
| F-07 | Service Key Inconsistency | `JARVIS/services/supervisor.py` L355, L753 | `launch_service()` (L355) and the watchdog loop (L753) reference `"dashboard_ui"` as a service name, but `"dashboard_ui"` is **not a key in the `SERVICES` dict**. The `launch_service` branch is guarded by `if name == "dashboard_ui"` so it opens a log file for stdout — but since the supervisor's own main loop only calls `launch_service(name)` for names in `SERVICES`, this branch is never triggered. The dashboard_ui heartbeat check at L753 (`if name != "dashboard_ui"`) prevents a re-launch of the GUI process, which is correct intent but references a phantom key. | LOW | Tier 1 (document/comment only — no runtime effect) |
| F-08 | Missing requirements entry | `requirements.txt` | `pyaudio` (native) is not listed in `requirements.txt`. The root-level `pyaudio.py` shim works without it, but when users do have native PyAudio installed system-wide, the shim at L10–26 bypasses the project directory to load it — yet no version constraint is documented. Users who install `pyaudio` manually get it without guidance. This is a documentation gap. | LOW | Tier 1 |
| F-09 | QML Signal Overloading — Wrong Notify | `JARVIS/gui/qml_bridge.py` L1025 | `aiIntegrationHealth` property (L1025) declares `notify=hybridAIStatusChanged`. This is the same notify signal as `hybridAIStatus` (L1010). Two different properties sharing the same notify signal causes QML to re-evaluate both properties whenever `hybridAIStatusChanged` fires. While not technically broken, it causes unnecessary QML binding evaluations. The correct signal would be a dedicated `aiIntegrationHealthChanged` signal. | MEDIUM | Tier 3 (new signal addition touches both Python and all QML consumers — requires verification) |
| F-10 | Supervisor — `changed` uninitialized first iteration risk | `JARVIS/services/supervisor.py` L664 | In `monitor_loop()`, the variable `changed` is first assigned at L664 *inside* a conditional block (`if voice_cfg["process"] is not None`). If voice is enabled and `process` is None (first boot), `changed` is never assigned before the for-loop at L693 which sets it further, but `changed` is only ever *set* never *read* conditionally — all `if changed:` uses are absent. `write_status_file()` is called unconditionally at L792. The `changed` variable is set but never consumed as a condition. This is dead logic — all calls to `write_status_file()` happen regardless. Not a runtime bug but misleading code. | LOW | Tier 1 (annotate as dead tracking variable or remove assignments) |
| F-11 | Background Services — Bare Except in Metrics Loop | `JARVIS/gui/qml_bridge.py` L697 | The outermost `try/except Exception: pass` at L697 inside the `while self._is_alive:` metrics loop swallows **all exceptions silently** every second. This includes the F-03 NameError. Any future bug in the loop is invisible. At minimum, a `logger.debug` on the exception would help diagnosis. | MEDIUM | Tier 3 (changing exception handling policy) |
| F-12 | Root-level shadow module placement | `pyaudio.py` (root) | `pyaudio.py` lives at project root which shadows the real `pyaudio` package when the project root is on `sys.path`. The shim handles this correctly via path manipulation (L10–26), but is fragile — if `sys.path` is modified by another import before this module is first imported, the shim's path exclusion may fail. Low probability in practice. | LOW | Tier 3 (path ordering is architecture-level concern) |
| F-13 | Tests — Scratch files in test directory | `tests/scratch_test.py`, `tests/scratch_validate_routing.py` | Two scratch/development scripts are committed in the `tests/` directory but are not proper test files (no `unittest`/`pytest` classes, no assertions). They pollute test discovery. | LOW | Tier 1 |
| F-14 | Root-level dead script | `run_profile.py`, `refactor.py` | Two development utility scripts at project root (`run_profile.py` for cProfile, `refactor.py` as no-op migration) have no callers and are not part of any documented workflow. | LOW | Tier 1 (safe to document; removal is optional) |

---

## Summary by Tier

| Tier | Count | IDs |
|------|-------|-----|
| Tier 1 (auto-fixable, low risk) | 8 | F-01, F-02, F-04, F-05, F-06, F-07, F-08, F-10, F-13, F-14 |
| Tier 2 (fix + verify required) | 1 | F-03 |
| Tier 3 (propose only) | 3 | F-09, F-11, F-12 |

---

## Key Positives Observed
- All 185 Python source files pass `py_compile` — zero syntax errors
- QML signal/slot wiring is comprehensive and consistent (42 signals, all with matching `@Property(notify=...)` declarations)
- Supervisor has solid single-instance locking via `PortManager`
- GUI/Backend separation is clean: GUI launches supervisor as subprocess; bridge decouples them
- Self-healing and backup systems are implemented and functional in design
