"""
venv_resolver.py — canonical Python-environment resolver for JARVIS.

Detection order (first valid match wins):
  1. Project root .venv
  2. Project root 'venv' or 'env'
  3. VIRTUAL_ENV environment variable (currently activated venv)
  4. Running interpreter (sys.executable) if all required packages are importable
  5. py-launcher installations (Windows) — used ONLY as a base to create a new .venv

If nothing valid is found:
  * Auto-creates a .venv at the project root using the best available base Python.
  * Installs requirements.txt into it silently.
  * Logs the creation event — never shows a blocking popup.

Both environment_validator.py and startup_manager.py import ONLY from this module
to retrieve the resolved interpreter path.  That single shared value eliminates the
class of bugs where two files resolve the path independently.

Public API
----------
  VenvResolver.resolve()          -> ResolvedEnv(python_exe, venv_root, source, created)
  get_resolved_env()              -> cached ResolvedEnv (module-level singleton)
  get_python_exe()                -> str path to python.exe inside the resolved env
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("venv_resolver")

# ---------------------------------------------------------------------------
# Project root — resolved relative to this file's location so it works
# regardless of CWD or how Python was invoked.
# File is at: <root>/JARVIS/core/system/venv_resolver.py
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Required packages that MUST be importable inside the chosen environment.
REQUIRED_PACKAGES: list[str] = [
    "PySide6",
    "psutil",
    "cryptography",
    "groq",
    "requests",
    "dotenv",
]

# Map import-name -> pip install name (when they differ)
_PIP_NAME: dict[str, str] = {
    "PySide6":      "PySide6>=6.7.0",
    "psutil":       "psutil>=5.9.0",
    "cryptography": "cryptography>=41.0.0",
    "groq":         "groq>=0.9.0",
    "requests":     "requests>=2.31.0",
    "dotenv":       "python-dotenv>=1.0.0",
}


@dataclass
class ResolvedEnv:
    """Result of a successful environment resolution."""
    python_exe: str                    # absolute path to python.exe (or 'python' as fallback)
    venv_root: Optional[Path]          # root directory of the venv (None if bare interpreter)
    source: str                        # human-readable label for where this env came from
    created: bool = False              # True when we auto-created a new .venv
    missing_packages: list[str] = field(default_factory=list)  # packages not importable


# ---------------------------------------------------------------------------
# Module-level singleton — populated once on first call to get_resolved_env()
# ---------------------------------------------------------------------------
_resolved_env: Optional[ResolvedEnv] = None


class VenvResolver:
    """Stateless resolver; instantiate fresh or use module-level singleton."""

    def __init__(self, project_root: Optional[Path] = None,
                 requirements_file: Optional[Path] = None):
        self.root = project_root or _PROJECT_ROOT
        self.req_file = requirements_file or (self.root / "requirements.txt")
        self._log_file = self.root / "logs" / "venv_resolver.log"

    # ------------------------------------------------------------------ #
    #  Main entry-point                                                    #
    # ------------------------------------------------------------------ #

    def resolve(self) -> ResolvedEnv:
        """
        Walk through the detection order and return the first valid env.
        On total failure, auto-create a .venv and return it.
        Never raises; always returns a ResolvedEnv.
        """
        self._log("INFO", "Starting environment resolution ...")

        # -- 1. Project root .venv ------------------------------------------
        candidate = self._check_named_venv(".venv")
        if candidate:
            return candidate

        # -- 2. Alternative names: venv / env --------------------------------
        for name in ("venv", "env"):
            candidate = self._check_named_venv(name)
            if candidate:
                return candidate

        # -- 3. VIRTUAL_ENV environment variable -----------------------------
        venv_from_env = os.environ.get("VIRTUAL_ENV", "").strip()
        if venv_from_env:
            candidate = self._check_venv_dir(
                Path(venv_from_env), source="VIRTUAL_ENV env-var"
            )
            if candidate:
                return candidate

        # -- 4. Running interpreter — check package availability in-process --
        candidate = self._check_running_interpreter()
        if candidate:
            return candidate

        # -- 5. Auto-repair: create a new .venv ------------------------------
        return self._auto_create_venv()

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _check_named_venv(self, name: str) -> Optional[ResolvedEnv]:
        """Check <root>/<name> as a candidate venv directory."""
        venv_dir = self.root / name
        return self._check_venv_dir(venv_dir, source=f"project root '{name}'")

    def _check_venv_dir(self, venv_dir: Path, source: str) -> Optional[ResolvedEnv]:
        """Validate a venv directory.  Returns ResolvedEnv or None."""
        if not venv_dir.exists():
            return None

        # Must have pyvenv.cfg (marks a real venv, not a random dir named venv)
        if not (venv_dir / "pyvenv.cfg").exists():
            self._log("WARN", f"{venv_dir} exists but has no pyvenv.cfg -- skipping")
            return None

        python_exe = self._find_python_exe(venv_dir)
        if not python_exe:
            self._log("WARN", f"{venv_dir} has no python.exe -- skipping")
            return None

        # Validate pip works
        if not self._pip_works(python_exe):
            self._log("WARN", f"{python_exe}: pip does not work -- skipping")
            return None

        missing = self._missing_packages(str(python_exe))
        self._log(
            "INFO",
            f"Found valid env at '{venv_dir}' (source: {source})"
            + (f" -- missing: {missing}" if missing else " -- all packages OK"),
        )
        return ResolvedEnv(
            python_exe=str(python_exe),
            venv_root=venv_dir,
            source=source,
            missing_packages=missing,
        )

    def _check_running_interpreter(self) -> Optional[ResolvedEnv]:
        """
        Accept sys.executable if ALL required packages are importable in-process.
        We only trust the running interpreter (no subprocess) because the user
        explicitly invoked Python -- so we're already in their desired env.
        """
        missing: list[str] = []
        for pkg in REQUIRED_PACKAGES:
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)

        if missing:
            self._log(
                "INFO",
                f"Running interpreter {sys.executable!r} missing: {missing} -- skipping",
            )
            return None

        self._log("INFO", f"Running interpreter {sys.executable!r} has all packages")
        return ResolvedEnv(
            python_exe=sys.executable,
            venv_root=None,
            source="running interpreter (sys.executable)",
        )

    def _auto_create_venv(self) -> ResolvedEnv:
        """
        Create a .venv at project root using the best available base Python,
        then install requirements.txt.  Never prompts the user.
        """
        venv_dir = self.root / ".venv"
        self._log("INFO", f"No valid environment found -- auto-creating {venv_dir} ...")

        base_python = self._find_best_base_python()
        if not base_python:
            # Last resort: hope 'python' is on PATH
            base_python = "python"
            self._log("WARN", "No base Python found via py launcher; trying 'python'")

        self._log("INFO", f"Using base Python: {base_python}")

        # Create the venv
        try:
            result = subprocess.run(
                [base_python, "-m", "venv", str(venv_dir)],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                self._log("ERROR", f"venv creation failed: {result.stderr.strip()}")
            else:
                self._log("INFO", f"Successfully created {venv_dir}")
        except Exception as exc:
            self._log("ERROR", f"venv creation exception: {exc}")

        # Install requirements
        python_exe_path = self._find_python_exe(venv_dir)
        if python_exe_path and self.req_file.exists():
            self._log("INFO", f"Installing requirements from {self.req_file} ...")
            try:
                result = subprocess.run(
                    [str(python_exe_path), "-m", "pip", "install",
                     "-r", str(self.req_file), "--quiet"],
                    capture_output=True, text=True, timeout=600,
                )
                if result.returncode != 0:
                    self._log("WARN", f"pip install had errors: {result.stderr[:500]}")
                else:
                    self._log("INFO", "requirements.txt installed successfully")
            except Exception as exc:
                self._log("WARN", f"pip install exception: {exc}")

        python_exe = python_exe_path or Path(base_python)
        missing = self._missing_packages(str(python_exe)) if python_exe_path else list(REQUIRED_PACKAGES)

        return ResolvedEnv(
            python_exe=str(python_exe),
            venv_root=venv_dir if venv_dir.exists() else None,
            source="auto-created .venv (repair)",
            created=True,
            missing_packages=missing,
        )

    # ------------------------------------------------------------------ #
    #  Windows-specific: py launcher scan                                  #
    # ------------------------------------------------------------------ #

    def _find_best_base_python(self) -> Optional[str]:
        """
        On Windows: use 'py -X.Y' to find the newest Python 3.10+ installation.
        Falls back to sys.executable (only if it is NOT inside a venv).
        Never returns a venv interpreter -- only a base installation.
        """
        # Try py launcher (Windows)
        if os.name == "nt":
            for minor in range(13, 9, -1):   # 3.13 -> 3.10
                tag = f"-3.{minor}"
                try:
                    proc = subprocess.run(
                        ["py", tag, "-c", "import sys; print(sys.executable)"],
                        capture_output=True, text=True, timeout=10,
                    )
                    if proc.returncode == 0:
                        exe = proc.stdout.strip()
                        if exe and Path(exe).exists():
                            self._log("INFO", f"py launcher found Python 3.{minor}: {exe}")
                            return exe
                except FileNotFoundError:
                    break   # py launcher not installed
                except Exception:
                    continue

        # Fallback: use the running interpreter itself as the base
        base = sys.executable
        # Only if it is NOT inside a venv (otherwise we'd clone a possibly broken env)
        if not self._is_venv_interpreter(Path(base)):
            self._log("INFO", f"Using running interpreter as base: {base}")
            return base

        self._log("WARN", "Running interpreter is inside a venv; trying 'python' on PATH")
        return None

    @staticmethod
    def _is_venv_interpreter(exe: Path) -> bool:
        """Heuristic: a venv interpreter lives under a Scripts/ or bin/ directory."""
        try:
            parts = exe.parts
            return "Scripts" in parts or "bin" in parts
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    #  Package / pip helpers                                               #
    # ------------------------------------------------------------------ #

    def _missing_packages(self, python_exe: str) -> list[str]:
        """Return import names of REQUIRED_PACKAGES that fail to import in python_exe."""
        if python_exe == sys.executable:
            # Fast in-process check
            missing = []
            for pkg in REQUIRED_PACKAGES:
                try:
                    __import__(pkg)
                except ImportError:
                    missing.append(pkg)
            return missing

        # Out-of-process check
        checks = " ".join(
            f"print('{pkg}') if not __import__('importlib').util.find_spec('{pkg}') else None;"
            for pkg in REQUIRED_PACKAGES
        )
        script = checks
        try:
            proc = subprocess.run(
                [python_exe, "-c", script],
                capture_output=True, text=True, timeout=30,
            )
            if proc.returncode == 0:
                return [line.strip() for line in proc.stdout.splitlines() if line.strip()]
            return []
        except Exception:
            return []

    @staticmethod
    def _pip_works(python_exe: str | Path) -> bool:
        """Return True if pip is functional inside the given interpreter."""
        try:
            result = subprocess.run(
                [str(python_exe), "-m", "pip", "--version"],
                capture_output=True, text=True, timeout=15,
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def _find_python_exe(venv_dir: Path) -> Optional[Path]:
        """Return the python executable inside venv_dir, or None."""
        for rel in (
            Path("Scripts") / "python.exe",   # Windows
            Path("bin") / "python3",           # macOS / Linux
            Path("bin") / "python",
        ):
            candidate = venv_dir / rel
            if candidate.exists():
                return candidate
        return None

    # ------------------------------------------------------------------ #
    #  Logging                                                             #
    # ------------------------------------------------------------------ #

    def _log(self, level: str, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{level:<5}] [venv_resolver] {message}"
        print(line, flush=True)
        log_fn = {
            "DEBUG": logger.debug,
            "INFO":  logger.info,
            "WARN":  logger.warning,
            "ERROR": logger.error,
        }.get(level, logger.info)
        log_fn(message)
        try:
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._log_file, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Module-level convenience API
# ---------------------------------------------------------------------------

def get_resolved_env(force: bool = False) -> ResolvedEnv:
    """
    Return the cached ResolvedEnv, resolving on first call.

    Parameters
    ----------
    force : bool
        If True, discard the cached result and re-resolve.
    """
    global _resolved_env
    if _resolved_env is None or force:
        _resolved_env = VenvResolver().resolve()
    return _resolved_env


def get_python_exe(force: bool = False) -> str:
    """Convenience shortcut -- returns the python executable path string."""
    return get_resolved_env(force=force).python_exe
