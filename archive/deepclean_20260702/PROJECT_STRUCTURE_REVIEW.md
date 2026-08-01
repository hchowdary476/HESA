# Project Structure Review (PROJECT_STRUCTURE_REVIEW.md)

This report reviews the folder structure and module imports of **JARVIS v3.0** to verify structural consistency, naming alignment, and code cleanliness.

## 1. Directory Structure Mapping

Below is the evaluation of the actual repository layout compared to the expected structure.

| Folder / File | Expected in standard v3.0 | Status | Description / Notes |
|---|---|---|---|
| `JARVIS/` | Yes | **PASS** | Contains core modules (`core/`, `services/`, `app/`, `gui/`, `sdk/`, `utils/`, `release/`). |
| `assets/` | Yes | **PASS** | Contains global assets such as `jarvis_face.png` and typography fonts. |
| `plugins/` | Yes | **PARTIAL** | The repository contains `sample_plugins/` at the root level, but the active runtime `plugins/` folder is initialized dynamically by `PluginManager` upon installing the first plugin. |
| `knowledge/` | Yes | **PASS** | Holds language databases under `knowledge/telugu/`. |
| `docs/` | Yes | **PASS** | Contains developer and user documentation files. |
| `tests/` | Yes | **PASS** | Organized into domain-focused suites (`audio/`, `config/`, `plugins/`, `release/`, `security/`). |
| `scripts/` | Yes | **PASS** | Production helpers and release utilities (e.g. `public_release_check.py`, `cleanup_audit.py`). |
| `requirements.txt`| Yes | **PASS** | Project dependency specifications. |
| `README.md` | Yes | **PASS** | Primary entrypoint documentation. |
| `LICENSE` | Yes | **PASS** | Project license (MIT). |
| `CHANGELOG.md` | Yes | **PASS** | Historical record of updates. |

---

## 2. Architecture & Root Directory Findings

### 2.1 Root-level Python Modules
The root directory of the project contains numerous Python scripts:
- `api_gateway.py`
- `ai_kernel.py`
- `ai_fabric.py`
- `distributed_memory.py`
- `event_bus.py`
- `memory_engine.py`
- `memory_manager.py`
- `plugin_manager.py`
- `remote_api.py`
- `service_mesh.py`
- `tool_manager.py`
- `workflow_engine.py`

**Rationale:** These scripts act as execution entrypoints, shim wrappers, and daemon loaders for the API Gateway and CLI. They link the clean modular packages inside the `JARVIS/` subdirectory to the runtime shell. This structure is preserved to maintain API backward compatibility and simplify CLI imports.

### 2.2 Namespace Integrity & Import Style
Imports are structured using two primary patterns:
1. **Absolute Package Imports:** Inside `JARVIS/`, submodules import using absolute namespace declarations, for example:
   ```python
   from JARVIS.core.system.event_bus import EventBusServer
   from JARVIS.core.security.path_safety import validate_path_within_root
   ```
2. **Local Entrypoint Imports:** Scripts at the root level and within `api/` or `cli/` load peer modules locally. To ensure correctness when execution is initiated from deep directories, the codebase consistently prepends the project root path using:
   ```python
   import sys, os
   sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   ```

---

## 3. Structural Recommendations

1. **Move `sample_plugins/` to `plugins/`**:
   To align with the expected clean directory structure, the `sample_plugins/` directory should be renamed to `plugins/` in the code references and build profiles. Or, a default `plugins/` directory containing a `.gitkeep` file should be checked in at the root.
2. **Consolidate Gateway Entrypoints**:
   The root-level wrapper files (like `api_gateway.py`, `distributed_memory.py`, and `remote_api.py`) could eventually be refactored into the `JARVIS/` package under `JARVIS.app` or `JARVIS.services` in future version releases. For v3.0, they should remain as-is to preserve test regressions.
