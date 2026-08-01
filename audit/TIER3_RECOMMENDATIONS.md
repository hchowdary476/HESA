# JARVIS Audit — Tier 3 Recommendations

**Status:** Proposals only — no code changes applied.

---

## T3-01: F-09 — `aiIntegrationHealth` property uses wrong `notify` signal

### Root Cause Hypothesis
`aiIntegrationHealth` (line 1025 in `qml_bridge.py`) is decorated with `@Property(str, notify=hybridAIStatusChanged)`. This is the same signal as `hybridAIStatus` (line 1010). Both properties share one notification signal.

### Why Human Judgment Is Needed
QML property notification works as follows: when `hybridAIStatusChanged` fires, the QML engine re-evaluates every binding that depends on *both* `hybridAIStatus` and `aiIntegrationHealth`. This means any QML binding to `jarvis.aiIntegrationHealth` gets re-evaluated unnecessarily when only `hybridAIStatus` changes (and vice versa). The fix — adding a new `aiIntegrationHealthChanged = Signal()` and wiring it to fire on a different cadence — requires:
1. Adding the new signal declaration.
2. Updating the `_loop()` or `_ai_poll_counter` block to emit it separately.
3. Checking all QML files that bind `jarvis.aiIntegrationHealth` to ensure they still update correctly.

This touches two languages (Python + QML) and the notification topology, which is a correctness boundary.

### Options
- **Option A (Low effort):** Leave as-is. The shared notify signal causes double evaluation but no incorrect values. The `aiIntegrationHealth` computation involves `random.randint()` (line 1069), so it returning slightly stale data is actually *better* than recalculating on every hybrid AI poll.
- **Option B (Correct fix):** Add `aiIntegrationHealthChanged = Signal()`, emit it in a lower-frequency poll (e.g., every 30 s), and update the `@Property` decorator.

### Recommendation
**Option A in the short term.** Option B should be scheduled with a QML UI review pass, because `aiIntegrationHealth` already calls `random.randint()` — the current behavior of not caching the random values is arguably a separate bug (values flicker on every notify).

---

## T3-02: F-11 — Bare `except Exception: pass` in metrics worker outermost loop

### Root Cause Hypothesis
Lines 402–698 in `qml_bridge.py` place the entire metrics loop body inside a `try: ... except Exception: pass`. This was likely added defensively to prevent the 1-second metrics thread from crashing the UI. However, it also silently swallows the F-03 `NameError` (which we identified is the actual production behavior).

### Why Human Judgment Is Needed
The right exception handling policy is a design decision:
- If the goal is **maximum resilience** (current): keep the broad except but add structured logging (`logger.debug("metrics loop error", exc_info=True)`).
- If the goal is **fast failure detection**: narrow the except to exclude `NameError`/`AttributeError` (programming errors should not be silenced).

Changing from `pass` to a log call is low-risk but changes what appears in log files — could affect log volume and any log parsers.

### Options
- **Option A:** Change `except Exception: pass` → `except Exception as _e: logger.debug("metrics_worker error: %s", _e)` — minimal change, adds observability.
- **Option B:** Narrow the except scope — wrap only the network/psutil calls that genuinely can fail transiently, and let programming errors propagate.

### Recommendation
**Option A** — add a single `logger.debug` line. This is safe, minimal, and gives future maintainers visibility without altering fault-tolerance behavior. Submit as a Tier 2 item after F-03 (the NameError) is fixed.

---

## T3-03: F-12 — `pyaudio.py` root-level shadow fragility

### Root Cause Hypothesis
`pyaudio.py` at project root intercepts `import pyaudio` for any code that runs with the project root on `sys.path`. The shim (lines 10–26) strips the project root from `sys.path` temporarily to find the real `pyaudio`, then restores it. This is a non-trivial path manipulation and fails if:
1. The real `pyaudio` is not installed — handled gracefully (sounddevice fallback).
2. Another thread calls `import pyaudio` concurrently during the path manipulation window — `sys.path` is temporarily modified in a non-thread-safe way.
3. The `importlib.util.find_spec()` call returns `None` for a different reason (e.g., broken `.egg-link`) — handled by falling back to sounddevice.

### Why Human Judgment Is Needed
Fixing the thread-safety issue requires either:
- A module-level import lock (`threading.Lock`) around the path manipulation — adds concurrency primitive to module init code.
- Moving the shim to a different location (e.g., `JARVIS/core/audio/`) and updating all `import pyaudio` callers — broad code change.

The threading risk is very low in practice because `pyaudio.py` is imported early during startup before most threads exist. However, documenting it as a known fragility is appropriate.

### Options
- **Option A (Status Quo):** Add a code comment documenting the thread-safety assumption.
- **Option B:** Wrap the `sys.path` manipulation in a module-level `_import_lock = threading.Lock()` guard.

### Recommendation
**Option A** — add comment. The practical risk of concurrent import during startup is negligible, and the shim has been working. A comment prevents future maintainers from "simplifying" the path code and breaking it.
