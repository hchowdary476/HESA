"""
environment_validator.py — JARVIS environment validation with auto-repair.

Key changes vs. legacy version:
  * Delegates ALL venv/interpreter path resolution to venv_resolver.get_resolved_env()
    (single shared singleton — startup_manager.py reads from the same source).
  * Detection order: .venv -> venv/env -> VIRTUAL_ENV -> running interpreter -> auto-create.
  * Auto-repairs silently (no blocking popup); surfaces repair state as a warning so
    the GUI log panel can show it.
  * Per-package error reporting: each missing package is listed individually by name,
    not as a single generic "Environment invalid" message.
  * Never terminates the GUI for a venv issue.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from JARVIS.core.system.venv_resolver import (
    REQUIRED_PACKAGES,
    get_resolved_env,
)


class EnvironmentValidator:
    """
    Validates the JARVIS runtime environment.

    After construction, call validate_all() which returns True when startup
    can safely proceed.  Always inspect get_report() for per-item detail.

    The resolved venv path is available via self.resolved_env (a ResolvedEnv
    dataclass from venv_resolver) so callers do not need to resolve it again.
    """

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        # Resolved once; shared with StartupManager via the module singleton.
        self.resolved_env = get_resolved_env()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def validate_all(self) -> bool:
        """Run all validation checks.  Returns True iff no blocking errors."""
        self._validate_python_version()
        self._validate_venv()  # uses venv_resolver singleton
        self._validate_dependencies()  # per-package, individual errors
        self._validate_config_files()
        self._validate_ai_providers()
        self._validate_voice_config()
        self._validate_database()
        self._validate_plugins()
        return len(self.errors) == 0

    def get_report(self) -> dict:
        """Return a structured validation report dict."""
        return {
            "valid": len(self.errors) == 0,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "venv_source": self.resolved_env.source,
            "venv_root": str(self.resolved_env.venv_root or "N/A"),
            "python_exe": self.resolved_env.python_exe,
            "venv_created": self.resolved_env.created,
        }

    # ------------------------------------------------------------------ #
    #  Individual checks                                                   #
    # ------------------------------------------------------------------ #

    def _validate_python_version(self) -> None:
        """Check Python version (3.10+)."""
        if sys.version_info < (3, 10):
            major, minor = sys.version_info[:2]
            self.errors.append(f"Python 3.10+ required (found {major}.{minor})")

    def _validate_venv(self) -> None:
        """
        Validate the resolved environment (from venv_resolver singleton).

        If auto-repair ran (created == True), record it as a warning, not an
        error — startup should continue.  If the venv has missing packages,
        list each one individually so the user knows exactly what to fix.
        """
        env = self.resolved_env

        # Auto-repair note — informational, not a blocker
        if env.created:
            self.warnings.append(
                f"Virtual environment was missing; auto-created at "
                f"'{env.venv_root}' using base Python "
                f"(source: {env.source}). "
                f"See logs/venv_resolver.log for details."
            )

        # Check venv_root integrity only when we resolved a directory-based env
        if env.venv_root is not None:
            venv_dir = Path(env.venv_root)
            if not venv_dir.exists():
                self.errors.append(f"Virtual environment directory not found: {venv_dir}\n  (resolved from: {env.source})")
                return
            if not (venv_dir / "pyvenv.cfg").exists():
                self.errors.append(f"Virtual environment appears corrupted (pyvenv.cfg missing): {venv_dir}")
                return

        # Per-package missing package errors
        for pkg in env.missing_packages:
            self.errors.append(f"Required package not importable in resolved env: '{pkg}'\n  Fix: {env.python_exe} -m pip install {pkg}")

    def _validate_dependencies(self) -> None:
        """
        Verify that each package in REQUIRED_PACKAGES can be imported.

        When JARVIS is launched from inside the resolved venv (the normal
        production path) sys.executable == resolved python_exe, so
        __import__ tests run in the right interpreter — this is the
        belt-and-suspenders check.

        When the caller is a *different* Python (e.g. system python used
        to run launcher.py before the venv is activated), running
        __import__ in-process tests the WRONG interpreter and will always
        false-positive on packages that ARE installed inside the venv.
        In that case the resolver already verified packages out-of-process
        via 'pip list' inside the venv and populated missing_packages; we
        trust that list and skip the in-process probe entirely.
        """
        resolved_exe = os.path.normcase(os.path.normpath(self.resolved_env.python_exe))
        running_exe = os.path.normcase(os.path.normpath(sys.executable))

        if resolved_exe != running_exe:
            # Running outside the resolved venv (e.g. system python via launcher).
            # The resolver's missing_packages is the authoritative source; it was
            # checked out-of-process in the correct interpreter. _validate_venv()
            # already converted those into individual errors above — nothing more
            # to add here.
            return

        # Running inside the resolved venv — belt-and-suspenders import check.
        for package in REQUIRED_PACKAGES:
            try:
                __import__(package)
            except ImportError:
                self.errors.append(
                    f"Required package not installed in active interpreter: '{package}'\n"
                    f"  Active interpreter: {sys.executable}\n"
                    f"  Fix: {self.resolved_env.python_exe} -m pip install {package}"
                )
            except Exception as exc:
                # Non-ImportError (e.g. C extension load failure) — still report
                self.errors.append(f"Package '{package}' import raised {type(exc).__name__}: {exc}")

    def _validate_config_files(self) -> None:
        """Check that .env configuration file exists."""
        # Resolve from __file__ so this works regardless of CWD
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        env_file = project_root / ".env"
        if not env_file.exists():
            self.warnings.append(
                f".env file is missing at project root ({project_root}). Copy .env.example to .env and fill in your API keys."
            )

    def _validate_ai_providers(self) -> None:
        """Check AI provider configuration keys."""
        load_dotenv()
        if not os.getenv("GROQ_API_KEY"):
            self.warnings.append("Groq API key (GROQ_API_KEY) not configured. AI features requiring Groq will be unavailable.")

    def _validate_voice_config(self) -> None:
        """Check voice engine dependencies (non-blocking)."""
        try:
            from JARVIS.core.voice.ses_motoru import VoiceEngine  # noqa: F401
        except Exception as exc:
            self.warnings.append(f"Voice engine check issue: {exc}")

    def _validate_database(self) -> None:
        """Verify memory persistence file path is resolvable."""
        try:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            memory_file = project_root / "memory.json"
            if not memory_file.exists():
                self.warnings.append("memory.json not found — it will be auto-created on first run.")
        except Exception as exc:
            self.errors.append(f"Database path resolution failed: {exc}")

    def _validate_plugins(self) -> None:
        """Check that installed plugin directories contain manifest.json."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        plugins_dir = project_root / "plugins"
        if plugins_dir.exists():
            for plugin_dir in plugins_dir.glob("*/"):
                manifest = plugin_dir / "manifest.json"
                if not manifest.exists():
                    self.warnings.append(f"Plugin '{plugin_dir.name}' is missing manifest.json")
