# GUI CRASH REPORT

**Generated:** 2026-07-31 15:07:41  
**PID:** 66052  
**Startup Timestamp:** 2026-07-31T15:07:22  
**Crash #:** 1  

---

## Crash Details

| Field | Value |
|-------|-------|
| Source Thread | `THREAD:WakeListener` |
| Exception Type | `OSError` |
| Exception Message | `[Errno 22] Invalid argument` |
| Offending File | `jarvis.py` |
| Offending Line | `656` |

---

## Full Traceback

```python
Traceback (most recent call last):
  File "JARVIS/core/voice/openwakeword_engine.py", line 104, in _init_engine
    print("[WAKE] Model loaded.", flush=True)
OSError: [Errno 22] Invalid argument

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "jarvis.py", line 651, in run_wake_listener_with_recovery
    listen_for_wake_word(logger=logger, send_log=send_log)
  File "JARVIS/runtime/wake_listener.py", line 181, in listen_for_wake_word
    oww_engine = get_openwakeword_engine()
                 ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "JARVIS/core/voice/openwakeword_engine.py", line 170, in get_openwakeword_engine
    return OpenWakeWordEngine()
           ^^^^^^^^^^^^^^^^^^^^
  File "JARVIS/core/voice/openwakeword_engine.py", line 66, in __new__
    cls._instance._init_engine()
  File "JARVIS/core/voice/openwakeword_engine.py", line 114, in _init_engine
    print(f"[WAKE] OpenWakeWord initialization failed: {err}", flush=True)
OSError: [Errno 22] Invalid argument

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "Python312/Lib/threading.py", line 1075, in _bootstrap_inner
    self.run()
  File "Python312/Lib/threading.py", line 1012, in run
    self._target(*self._args, **self._kwargs)
  File "jarvis.py", line 656, in run_wake_listener_with_recovery
    print(f"[ERROR] Wake listener crashed: {e}", flush=True)
OSError: [Errno 22] Invalid argument
```

---

## Recommended Fix

1. Open **`jarvis.py`** at **line 656**
2. Inspect the exception: `OSError: [Errno 22] Invalid argument`
3. Add `try/except` or null-check around the offending call
4. Check `logs/gui_traceback.log` for full history

---

*Full traceback history: `logs/gui_traceback.log`*  
