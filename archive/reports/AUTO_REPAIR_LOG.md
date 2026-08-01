# JARVIS Auto Repair Log

All fixes applied in the absence of a git environment use the `[NO-GIT]` protocol.

## Fix Log

### Fix F-03: `status_data` NameError in metrics worker
- **File:** [qml_bridge.py](file:///c:/Users/veera/OneDrive/Desktop/Open.Jarvis-main/JARVIS/gui/qml_bridge.py)
- **Risk Rating:** LOW
- **Description:** Fixed a `NameError` where `status_data` was called instead of the in-scope variable `data` within `_start_metrics_worker._loop()`.
- **Rollback Note:** To roll back, change `self._compute_active_modules_cache(data)` back to `self._compute_active_modules_cache(status_data)` in [qml_bridge.py](file:///c:/Users/veera/OneDrive/Desktop/Open.Jarvis-main/JARVIS/gui/qml_bridge.py).
- **Diff:**
```diff
--- JARVIS/gui/qml_bridge.py
+++ JARVIS/gui/qml_bridge.py
@@ -700,3 +700,3 @@
                     try:
-                        new_modules_json = self._compute_active_modules_cache(status_data)
+                        new_modules_json = self._compute_active_modules_cache(data)
                         if new_modules_json != self._active_modules_cache:
```

### Fix F-04: Knowledge Graph self-healing diagnostic bug
- **File:** [qml_bridge.py](file:///c:/Users/veera/OneDrive/Desktop/Open.Jarvis-main/JARVIS/gui/qml_bridge.py)
- **Risk Rating:** LOW
- **Description:** Fixed a bug where the self-healing status check for the Knowledge Graph was hardcoded to always return `"PASS"`, regardless of whether `knowledge_graph.json` exists. Corrected `else "PASS"` to `else "FAIL"`.
- **Rollback Note:** To roll back, change `else "FAIL"` back to `else "PASS"` on line 849 of [qml_bridge.py](file:///c:/Users/veera/OneDrive/Desktop/Open.Jarvis-main/JARVIS/gui/qml_bridge.py).
- **Diff:**
```diff
--- JARVIS/gui/qml_bridge.py
+++ JARVIS/gui/qml_bridge.py
@@ -849,1 +849,1 @@
-        kg_status = "PASS" if os.path.exists(os.path.join("logs", "knowledge_graph.json")) or os.path.exists("knowledge_graph.json") else "PASS"
+        kg_status = "PASS" if os.path.exists(os.path.join("logs", "knowledge_graph.json")) or os.path.exists("knowledge_graph.json") else "FAIL"
```

### Fix F-05: Annotate historical dead script `refactor.py`
- **File:** [refactor.py](file:///c:/Users/veera/OneDrive/Desktop/Open.Jarvis-main/refactor.py)
- **Risk Rating:** LOW
- **Description:** Added comment documentation to clarify that `refactor.py` is historical/inactive, preventing developer confusion.
- **Rollback Note:** Delete the comment block from [refactor.py](file:///c:/Users/veera/OneDrive/Desktop/Open.Jarvis-main/refactor.py).
- **Diff:**
```diff
--- refactor.py
+++ refactor.py
@@ -1,1 +1,4 @@
+# NOTE: This script is a historical migration utility and is currently INACTIVE.
+# It is kept for historical reference. Do not run it.
+
 import os
```


