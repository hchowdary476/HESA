# JARVIS Audit — Backlog

## Priority-Ordered Unresolved Issues (from Session 1)

All issues below are discovered but not yet fixed. They await go-ahead per the audit protocol.

---

### BACKLOG-1 [TIER 2] — F-03: `status_data` NameError in metrics worker
**File:** `JARVIS/gui/qml_bridge.py` line 682  
**Priority:** HIGH — silent runtime bug active every ~1 second  
**Status:** Awaiting explicit go-ahead for Tier 2 fix  
**Fix:** Change `self._compute_active_modules_cache(status_data)` → `self._compute_active_modules_cache(data)`  
**Risk:** LOW — one-line variable name correction; the `data` variable is in scope, `status_data` is not  

---

### BACKLOG-2 [TIER 1] — F-01: AIMLPage missing from qmldir
**File:** `JARVIS/gui/qml/qmldir`  
**Priority:** HIGH — packaged deployment will fail to find AIMLPage  
**Status:** Awaiting approval (Tier 1 — low risk)  
**Fix:** Add `AIMLPage 1.0 AIMLPage.qml` to qmldir  

---

### BACKLOG-3 [TIER 1] — F-04: Knowledge Graph self-healing always returns PASS
**File:** `JARVIS/gui/qml_bridge.py` line 830  
**Priority:** MEDIUM — diagnostic display misleads user  
**Status:** Awaiting approval (Tier 1 — low risk)  
**Fix:** Change `else "PASS"` to `else "FAIL"` or implement real check  

---

### BACKLOG-4 [TIER 1] — F-02: SecurityPage.qml orphaned in qmldir  
**File:** `JARVIS/gui/qml/qmldir` line 27  
**Priority:** LOW — harmless dead registration  
**Status:** Awaiting approval  

---

### BACKLOG-5 [TIER 1] — F-05: refactor.py no-op dead script  
**File:** `refactor.py`  
**Priority:** LOW  
**Status:** Awaiting approval (recommend: add comment documenting it is historical, not delete)  

---

### BACKLOG-6 [TIER 1] — F-06: Unused STARTUP_GREETING constant  
**File:** `JARVIS/gui/main_window.py` line 44  
**Priority:** LOW  
**Status:** Awaiting approval  

---

### BACKLOG-7 [TIER 1] — F-10: `changed` variable tracking — dead logic  
**File:** `JARVIS/services/supervisor.py` lines 664, 667, 750, 758, 770  
**Priority:** LOW  
**Status:** Awaiting approval (recommend: annotate with comment, not remove)  

---

### BACKLOG-8 [TIER 1] — F-13: Scratch test files in tests/ directory  
**Files:** `tests/scratch_test.py`, `tests/scratch_validate_routing.py`  
**Priority:** LOW  
**Status:** Awaiting approval  

---

### BACKLOG-9 [TIER 3] — F-09: aiIntegrationHealth uses wrong notify signal  
**File:** `JARVIS/gui/qml_bridge.py` line 1025  
**Priority:** MEDIUM (performance concern, not correctness)  
**Status:** See TIER3_RECOMMENDATIONS.md  

---

### BACKLOG-10 [TIER 3] — F-11: Bare except in metrics loop swallows all errors silently  
**File:** `JARVIS/gui/qml_bridge.py` line 697  
**Priority:** MEDIUM (observability concern)  
**Status:** See TIER3_RECOMMENDATIONS.md  

---

### BACKLOG-11 [TIER 3] — F-12: pyaudio.py shadow fragility  
**File:** `pyaudio.py` (root)  
**Priority:** LOW  
**Status:** See TIER3_RECOMMENDATIONS.md  
