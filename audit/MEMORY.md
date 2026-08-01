# JARVIS Audit Memory

## Session Log

### Session 1 — 2026-07-01 (Phase 0 + Phase 1)

**Environment facts observed:**
- Python venv at `.venv/` uses Python 3.14 (cpython-314 in __pycache__ names)
- **Git is NOT installed** on this machine — the git-branch requirement cannot be fulfilled literally. All fixes must be logged with diffs instead of branches. Document this limitation at start of every session.
- **No existing `.git` repo** — project was likely downloaded as ZIP from GitHub ("Open.Jarvis-main")
- OS: Windows (OneDrive path), PowerShell available
- QML module: PySide6 ≥ 6.7.0 (renders via D3D11/RHI on Windows)

**Architecture notes:**
- Entry points: `jarvis.py` (CLI/headless), `jarvis_gui.py` (GUI quick-launch)
- GUI: `JARVIS/gui/main_window.py` → creates QApplication + QQmlApplicationEngine → loads `JARVIS/gui/qml/main.qml`
- Bridge: `JARVIS/gui/qml_bridge.py` — JarvisBridge (QObject). Single context property `jarvis` registered in QML.
- Backend supervisor: `JARVIS/services/supervisor.py` — launched as subprocess by GUI via `subprocess.Popen([sys.executable, "-m", "JARVIS.services.supervisor"])`
- Services registered in supervisor: voice_engine, memory_engine, automation_engine, security_engine, ai_agents, diagnostics_engine, system_monitor, camera_engine, network_monitor
- `memory_engine`, `security_engine`, `automation_engine` are "consolidated dummy" services — run in-supervisor, not as real subprocesses
- Single-instance locking via `PortManager.acquire_service_lock()` (socket-based)
- QML pages: DashboardPage, SystemPage, ModulesPage, CyberSecurityPage, DiagnosticsPage, AIStatusPage, AIMLPage, SettingsPage, HelpPage
- Navigation: BottomDock.qml emits `pageSelected(key)`, root.qml handles via `onActivePageChanged`

**Coding conventions observed:**
- All Python files use `from __future__ import annotations`
- Logging via `JARVIS.core.system.utils.jarvis_logging.get_logger()`
- Env loading: `load_dotenv(find_env_file())` — called in multiple entry points (intentional)
- QML signals use camelCase; Python properties use camelCase with `notify=signalName`
- Long `except Exception: pass` blocks are common — intentional fault tolerance design
- ~~`pyaudio.py` root-level shim~~ — **CORRECTED 2026-07-02**: `pyaudio.py` was an orphaned file in the root that shadowed the installed `pyaudio` package. It was archived to `archive/deepclean_20260702/pyaudio.py`. It was NOT an intentional shim.

**False-positive patterns to skip:**
- Multiple `load_dotenv()` calls at different entry points — intentional, not a bug
- `STARTUP_GREETING` in `main_window.py` line 44 — defined but never used in the file (passed implicitly via bridge log events); Tier 1 dead constant but very low risk

**Past fixes applied:**
- 2026-07-02: `EEasing` → `Easing` typo fixed in `JARVIS/gui/qml/MapEngine.qml:27` (ReferenceError prevented GUI from opening). See `audit/AUTOMATIC_REPAIR_REPORT.md`.
- 2026-07-02: Deep clean performed. ~155 items (4.6 MB) moved to `archive/deepclean_20260702/`. See `cleanup/DEEPCLEAN_PLAN.md`.
- 2026-07-02: **MISCLASSIFICATION CORRECTED** — `knowledge/telugu/system_commands.json` was archived as a duplicate of `commands.json` (byte-identical), but `tests/test_telugu_training.py::test_database_files_exist_and_counts` explicitly checks that **both** files exist by name. File restored from archive. Future agents: **do NOT archive `system_commands.json`** even though it is byte-identical to `commands.json` — the test suite requires both.

**Past fixes rejected:** (none yet)

---

## Anti-Recurrence Rules (added 2026-07-02 deep clean)

> Future audit/build/agent runs MUST follow these rules to prevent the root from accumulating report clutter again:

1. **One running file per category** — Do NOT create a new uniquely-named report file per run. Update the existing canonical file:
   - Repair/fix history → `audit/AUTOMATIC_REPAIR_REPORT.md`
   - Performance data → `FINAL_PERFORMANCE_REPORT.md`
   - Release status → `FINAL_AUTONOMOUS_AI_CERTIFICATION.md`
   - Architecture docs → update the relevant `*_ARCHITECTURE.md` in place
   - Audit findings → `audit/AUDIT_FINDINGS.md`

2. **Temp/scratch files** — Any file created during an agent run for temporary purposes (scan JSONs, test stubs, one-off scripts) MUST be deleted or moved to `archive/` at the end of that same run. Do not leave `tmp_*.py`, `*_scan.json`, or similar files in the repo root.

3. **Backups** — Keep only the single most recent `.bak.<timestamp>` per original file. When creating a new backup, delete all older ones for the same file.

4. **Logs** — Session debug logs (`dashboard_ui_*.log`, `gui_test_output.txt`, etc.) are gitignored. Do not commit them and do not let them accumulate — clear on each new session start.

5. **Test artifacts** — Files created by test runs (e.g., `corrupt_test.json`, `rollback_*_test_dummy_file.txt`) must be cleaned up by the test teardown. If they are not, treat them as junk and archive on the next pass.
