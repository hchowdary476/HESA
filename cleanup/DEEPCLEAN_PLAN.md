# JARVIS Deep Clean Plan — 2026-07-02

> **Phase 1 output — SCAN only. Nothing has been archived yet.**
> Review each section, adjust if needed, then approve to trigger Phase 2.

---

## Scan Summary

| Category | Items | Approx Size |
|---|---|---|
| 1. True duplicates | 5 groups, 44 files | ~13 KB |
| 2. Stale / superseded reports | 11 topic groups, ~78 files | ~734 KB |
| 3. Junk / cache / build artifacts | 5 sub-categories | ~3,817 KB |
| 4. Orphaned files | 3 files | ~8 KB |
| 5. Duplicate folders | 1 pair | ~16 KB |
| **Total flagged for archive** | **~155 items** | **~4.6 MB** |
| Needs human review | 5 items | — |

---

## 1. True Duplicates (5 groups, SHA-256 confirmed byte-identical)

### Group 1 — 34 safety rollback test-dummy files
All 34 files in `logs/backups/safety_rollbacks/` are byte-identical (16-byte `"test dummy file"` strings from repeated test runs, not real rollback data).
- KEEP: nothing
- ARCHIVE ALL 34: `logs/backups/safety_rollbacks/rollback_*_test_dummy_file.txt`

### Group 2 — config backup duplicates (4 files)
`logs/backups/config/config_bak_2..5.json` are all byte-identical.
- KEEP: `config_bak_1.json`
- ARCHIVE: `config_bak_2.json`, `config_bak_3.json`, `config_bak_4.json`, `config_bak_5.json`

### Group 3 — memory backup duplicates (4 files)
`logs/backups/memory/memory_bak_2..5.json` are all byte-identical.
- KEEP: `memory_bak_1.json`
- ARCHIVE: `memory_bak_2.json`, `memory_bak_3.json`, `memory_bak_4.json`, `memory_bak_5.json`

### Group 4 — Telugu knowledge duplicate (1 file)
`knowledge/telugu/commands.json` and `system_commands.json` are byte-identical.
Only `commands.json` is referenced in code (`telugu_formatter.py:317`).
- KEEP: `knowledge/telugu/commands.json`
- ARCHIVE: `knowledge/telugu/system_commands.json`

### Group 5 — Production memory empty JSONs (1 file)
`logs/production_memory/procedural.json` and `project.json` both contain `{}`.
- KEEP: `logs/production_memory/procedural.json`
- ARCHIVE: `logs/production_memory/project.json`

---

## 2. Stale / Superseded Reports (~78 files in root)

None of these are imported or opened by any source file (confirmed by full-repo search).

### Architecture and Design — KEEP 1, ARCHIVE 11
- KEEP: `AI_OS_ARCHITECTURE.md` (most comprehensive, 30-Jun)
- ARCHIVE: `AI_ML_PLATFORM_ARCHITECTURE.md`, `AI_ROUTER_ARCHITECTURE.md`, `ARCHITECTURE_PLAN.md`, `ARCHITECTURE_SUMMARY.md`, `COGNITIVE_CORE_PHASE2_ARCHITECTURE.md`, `COGNITIVE_OBSERVABILITY_ARCHITECTURE.md`, `CLOUD_PLATFORM_ARCHITECTURE.md`, `MISSION_CONTROL_ARCHITECTURE.md`, `PLUGIN_ECOSYSTEM_ARCHITECTURE.md`, `TOOL_SDK_ARCHITECTURE.md`, `WORKFLOW_ENGINE_ARCHITECTURE.md`

### SDK / Tool Integration — KEEP 1, ARCHIVE 2
- KEEP: `TOOL_SDK_INTEGRATION_REPORT.md` (8.2 KB, 01-Jul, most complete)
- ARCHIVE: `SDK_ARCHITECTURE.md`, `TOOL_SDK_REPORT.md`

### Performance / Stability — KEEP 1, ARCHIVE 6
- KEEP: `FINAL_PERFORMANCE_REPORT.md`
- ARCHIVE: `PERFORMANCE_REPORT.md`, `PERFORMANCE_OPTIMIZATION_REPORT.md`, `PERFORMANCE_TARGETS.md`, `SYSTEM_PERFORMANCE_CERTIFICATE.md`, `LONG_DURATION_STABILITY_REPORT.md`, `PRODUCTION_STABILITY_REPORT.md`

### Release / QA / Certification — KEEP 2, ARCHIVE 14
- KEEP: `FINAL_AUTONOMOUS_AI_CERTIFICATION.md` (13.2 KB, most complete), `RELEASE_NOTES_v3.0.md`
- ARCHIVE: `FINAL_RELEASE_CERTIFICATION.md`, `FINAL_RELEASE_PACKAGE.md`, `FINAL_QA_CERTIFICATE.md`, `FINAL_v3.0_RELEASE_APPROVAL.md`, `FINAL_PRODUCTION_READINESS_REPORT.md`, `FINAL_PRODUCTION_EXCELLENCE_CERTIFICATION.md`, `FINAL_MISSION_CONTROL_CERTIFICATION.md`, `PRODUCTION_READINESS_REPORT.md`, `RELEASE_PACKAGE_REPORT.md`, `RELEASE_TEST_CERTIFICATE.md`, `INSTALLER_VALIDATION_REPORT.md`, `GITHUB_READINESS_REPORT.md`, `VERSION_MANIFEST.md`, `BUILD_INFORMATION.md`

### Memory / Learning — KEEP 1, ARCHIVE 3
- KEEP: `MEMORY_LEARNING_REPORT.md` (10.3 KB, 01-Jul)
- ARCHIVE: `MEMORY_ARCHITECTURE.md`, `MEMORY_REPORT.md`, `CONTINUOUS_LEARNING_REPORT.md`

### Voice / Audio — KEEP 1, ARCHIVE 1
- KEEP: `VOICE_ORCHESTRATION_REPORT.md` (7.1 KB, 01-Jul)
- ARCHIVE: `VOICE_ENGINE_REPORT.md`

### Cognitive / AI Integration — KEEP 2, ARCHIVE 2
- KEEP: `COGNITIVE_INTEGRATION_REPORT.md`, `AUTONOMOUS_EXECUTION_ARCHITECTURE.md`
- ARCHIVE: `AI_INTEGRATION_REPORT.md`, `AUTONOMOUS_EXECUTION_REPORT.md`

### Workflow / Automation — KEEP 1, ARCHIVE 5
- KEEP: `WORKFLOW_AUTOMATION_REPORT.md` (9.2 KB, 01-Jul)
- ARCHIVE: `WORKFLOW_REPORT.md`, `BACKGROUND_EXECUTION_ENGINE.md`, `DEPENDENCY_MANAGER.md`, `TASK_MANAGER_ENGINE.md`, `TASK_RECOVERY_ENGINE.md`

### Security / Audit — KEEP 1, ARCHIVE 6
- KEEP: `FINAL_PROJECT_EVALUATION.md` (3.9 KB, most comprehensive)
- ARCHIVE: `SECURITY_AUDIT_REPORT.md`, `FUNCTIONAL_AUDIT_REPORT.md`, `UI_AUDIT_REPORT.md`, `BUTTON_AUDIT_REPORT.md`, `CODE_QUALITY_REPORT.md`, `PAT_REPORT.md`

### Bug / Fix Reports — KEEP 2, ARCHIVE 4
- KEEP: `REGRESSION_FIX_REPORT.md`, `AUTO_REPAIR_LOG.md` (running log)
- ARCHIVE: `BUG_REPORT.md`, `FINAL_BUGFIX_REPORT.md`, `TEST_FAILURE_ANALYSIS.md`, `AI_MODEL_HUB_FIX_REPORT.md`

### Integration / Validation — KEEP 2, ARCHIVE 8
- KEEP: `INTEGRATION_REPORT.md`, `FEATURE_VALIDATION_REPORT.md`
- ARCHIVE: `BACKEND_GUI_INTEGRATION_REPORT.md`, `REAL_WORLD_INTEGRATION_REPORT.md`, `LIVE_DATA_VALIDATION_REPORT.md`, `FULL_SYSTEM_VERIFICATION_REPORT.md`, `FUNCTIONAL_TEST_REPORT.md`, `MODEL_SWITCH_TEST_REPORT.md`, `MODEL_ROUTER_VALIDATION.md`, `PRODUCTION_VERIFICATION.md`

### Misc / Meta Reports — KEEP 4, ARCHIVE 20
- KEEP: `REPOSITORY_REVIEW.md`, `DOCUMENTATION_REVIEW.md`, `DEMO_PREPARATION_GUIDE.md`, `MIGRATION_ROADMAP.md`
- ARCHIVE (notable items):
  - PROJECT_CLEANUP_REPORT.md (669 KB! — an old scan from 30-Jun, entirely superseded by this doc)
  - `PROJECT_STRUCTURE_REVIEW.md`, `PROJECT_HEALTH_REPORT.md`, `FINAL_PROJECT_HEALTH_REPORT.md`, `FINAL_TEST_SUMMARY.md`, `PROJECT_DOCUMENTATION_INDEX.md`, `BUTTON_FUNCTIONALITY_REPORT.md`, `SERVICE_HEALTH_REPORT.md`, `SIGNAL_SLOT_AUDIT.md`, `QML_BINDING_AUDIT.md`, `DEPENDENCY_MAP.md`, `API_KEY_MANAGEMENT.md`, `FAILOVER_DESIGN.md`, `MODEL_ROUTING_STRATEGY.md`, `PLUGIN_REPORT.md`, `task.md`, `cleanup_scan_md.json`

---

## 3. Junk / Cache / Build Artifacts

### 3a. __pycache__ directories (41 dirs, ~3,755 KB)
All Python bytecode caches outside .venv — already in .gitignore but present on disk.
ARCHIVE ALL 41 __pycache__ directories (full list in scan notes).

### 3b. .pytest_cache/ (root, ~3 KB)
ARCHIVE: .pytest_cache/ (entire directory — already gitignored)

### 3c. corrupt_test.json backups (19 files, 24 bytes each)
All are identical test artifacts for a file that does not exist in the active codebase.
ARCHIVE ALL 19: `logs/backups/corrupt_test.json.*.bak`

### 3d. MapEngine.qml.bak.20260702121337 — KEEP
Only 1 backup exists for this file. It is the most recent (EEasing fix from this session). Keep per project convention.

### 3e. Stale log files (~48 KB)
ARCHIVE: `logs/dashboard_ui_errors.log`, `logs/dashboard_ui_stderr.log`, `logs/gui_test_output.txt`, `logs/jarvis_autostart.log`, `logs/listener_service.log` (empty), `logs/jarvis_gui_startup.log` (empty)
KEEP: `JARVIS/core/system/utils/logs/jarvis.log` (active runtime log)

---

## 4. Orphaned Files (3 files)

Confirmed not referenced by any import, open(), or string path in the active codebase.

- `refactor.py` (root, 1.8 KB) — one-off helper script, not integrated
- `run_profile.py` (root, 0.7 KB) — standalone profiling script, not integrated
- `pyaudio.py` (root, 5.3 KB) — DANGEROUS: shadows the installed pyaudio package for
  any script run from the repo root. Likely cause of voice feature breakage if it occurs.
  STRONGLY recommend archiving.

---

## 5. Duplicate Folders (1 pair)

docs/ vs release/JARVIS-dev-windows-portable/docs/ — 8 .md files are byte-identical (SHA-256 confirmed).
- KEEP: docs/ (primary source, referenced by README)
- ARCHIVE 8 files from release/.../docs/: BUILD_WINDOWS.md, OFFLINE_STT.md, PLUGIN_DEVELOPMENT.md, PLUGIN_SECURITY.md, RELEASE_SIGNING.md, VOICE_SETUP.md, VOICE_TROUBLESHOOTING.md, WINDOWS_PORTABLE.md
- KEEP in release/: README.txt (unique to release bundle)

---

## 6. Needs Human Review (5 items — NOT auto-archived)

### HR-1: workspace/task_manager/
A complete FastAPI backend project (27 files) inside the auto-generated JARVIS workspace root.
Diagnosis: Likely generated by JARVIS in a prior conversation session. Not referenced by core code.
Decision needed: Archive if no longer needed; keep if it is an active side project.

### HR-2: exports/ — 4 UI regression PNG screenshots
In .gitignore. No code reads them dynamically at runtime.
Decision needed: Archive if screenshots no longer needed for reference/regression baseline.

### HR-3: agents/task_log.json
Not part of JARVIS/agents/ (that is the actual agent module). Appears to be a stale multi-agent session runtime log.
Decision needed: Almost certainly safe to archive.

### HR-4: logs/fast_boot_report.md (326 bytes)
Leftover from a fast-boot optimization session. Not referenced anywhere.
Decision needed: Archive (safe).

### HR-5: test_platform_sandbox/ (contains only empty dist/ subfolder)
Entire folder is vestigial. No code references this path.
Decision needed: Archive entire folder (safe).

---

## Totals

| Category | Files / Dirs | Approx Size |
|---|---|---|
| True duplicates | 44 files | ~13 KB |
| Stale reports | ~78 .md files (incl. 669 KB giant) | ~734 KB |
| Junk / cache / logs | 41 dirs + 28 misc files | ~3,817 KB |
| Orphaned files | 3 files | ~8 KB |
| Duplicate folder files | 8 files | ~16 KB |
| Grand Total | ~155 items | ~4.6 MB |
| Needs human review (untouched) | 5 items | — |

NOTE: The release/JARVIS-dev-windows-portable/ bundle (647 MB) is NOT touched —
it is a build artifact already excluded by .gitignore. The 4.6 MB above is from the source tree only.

---

## Approval Checklist

Before Phase 2 runs, confirm:
[ ] Section 1 - True Duplicates: approved
[ ] Section 2 - Stale Reports: keepers and archives approved
[ ] Section 3 - Junk/Cache: all safe to archive
[ ] Section 4 - Orphaned Files (especially pyaudio.py): archive confirmed
[ ] Section 5 - Duplicate Folders: release/docs duplicates archive approved
[ ] Section 6 - Human Review: each item individually decided

Reply "approved" (or "approved except [item]") and Phase 2 will execute.
