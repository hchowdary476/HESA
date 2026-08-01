"""
test_startup_system.py — Tests for JARVIS startup and environment validation.

Covers:
  * Python version gating
  * Per-package dependency error reporting
  * VenvResolver detection order (stub-based)
  * Auto-repair creates .venv when nothing valid is found
  * Shared singleton: EnvironmentValidator and StartupManager read the same resolved path
  * StartupManager sequence and retry logic
  * ServiceHealthMonitor
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from JARVIS.core.system.startup_manager import StartupManager
from JARVIS.core.system.environment_validator import EnvironmentValidator
from JARVIS.core.system.service_monitor import ServiceHealthMonitor
from JARVIS.core.system import venv_resolver as _vr_module
from JARVIS.core.system.venv_resolver import (
    VenvResolver,
    ResolvedEnv,
    get_resolved_env,
    REQUIRED_PACKAGES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_venv(base_dir: Path, name: str = ".venv") -> Path:
    """Create a minimal fake venv structure so the resolver accepts it."""
    venv = base_dir / name
    scripts = venv / "Scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (venv / "pyvenv.cfg").write_text("home = C:\\Python311\n")
    # Write a tiny stub python.exe so _find_python_exe returns it
    python_exe = scripts / "python.exe"
    python_exe.write_bytes(b"\x4d\x5a")   # minimal PE magic bytes
    return venv


# ---------------------------------------------------------------------------
# VenvResolver unit tests
# ---------------------------------------------------------------------------

class VenvResolverDetectionOrderTests(unittest.TestCase):
    """Test the 5-step detection order in VenvResolver.resolve()."""

    def setUp(self):
        # Force a fresh module-level singleton for each test
        _vr_module._resolved_env = None

    # -- Step 1: project root .venv ----------------------------------------

    def test_detects_project_root_dot_venv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fake_venv(root, ".venv")
            resolver = VenvResolver(project_root=root)

            # pip_works would normally be called; stub it out so no subprocess needed
            with patch.object(VenvResolver, "_pip_works", return_value=True), \
                 patch.object(VenvResolver, "_missing_packages", return_value=[]):
                env = resolver.resolve()

        self.assertEqual(env.source, "project root '.venv'")
        self.assertFalse(env.created)

    # -- Step 2: alternative names venv / env --------------------------------

    def test_detects_venv_dir_when_dot_venv_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fake_venv(root, "venv")
            resolver = VenvResolver(project_root=root)

            with patch.object(VenvResolver, "_pip_works", return_value=True), \
                 patch.object(VenvResolver, "_missing_packages", return_value=[]):
                env = resolver.resolve()

        self.assertEqual(env.source, "project root 'venv'")
        self.assertFalse(env.created)

    # -- Step 3: VIRTUAL_ENV env var -----------------------------------------

    def test_detects_virtual_env_envvar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            venv = _make_fake_venv(root, "myenv")
            resolver = VenvResolver(project_root=Path(tmp) / "nonexistent_root")

            with patch.dict(os.environ, {"VIRTUAL_ENV": str(venv)}), \
                 patch.object(VenvResolver, "_pip_works", return_value=True), \
                 patch.object(VenvResolver, "_missing_packages", return_value=[]):
                env = resolver.resolve()

        self.assertEqual(env.source, "VIRTUAL_ENV env-var")
        self.assertFalse(env.created)

    # -- Step 4: running interpreter ------------------------------------------

    def test_detects_running_interpreter_when_all_packages_importable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)   # no venv dirs here
            resolver = VenvResolver(project_root=root)

            # Pretend all packages import fine in-process
            with patch.dict(os.environ, {}, clear=False), \
                 patch.object(VenvResolver, "_check_running_interpreter",
                               return_value=ResolvedEnv(
                                   python_exe=sys.executable,
                                   venv_root=None,
                                   source="running interpreter (sys.executable)",
                               )):
                env = resolver.resolve()

        self.assertIn("running interpreter", env.source)
        self.assertFalse(env.created)

    # -- Step 5: auto-repair -------------------------------------------------

    def test_auto_create_runs_when_nothing_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            req = root / "requirements.txt"
            req.write_text("# test\n")
            resolver = VenvResolver(project_root=root, requirements_file=req)

            with patch.object(VenvResolver, "_check_running_interpreter", return_value=None), \
                 patch.object(VenvResolver, "_find_best_base_python", return_value=sys.executable), \
                 patch("subprocess.run") as mock_run:
                # First call: venv creation succeeds
                # Second call: pip install succeeds
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                # _find_python_exe must find something after creation — fake it
                with patch.object(VenvResolver, "_find_python_exe",
                                   return_value=Path(sys.executable)), \
                     patch.object(VenvResolver, "_missing_packages", return_value=[]):
                    env = resolver.resolve()

        self.assertTrue(env.created)
        self.assertIn("repair", env.source)

    # -- Per-package missing package list ------------------------------------

    def test_missing_packages_returned_individually(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fake_venv(root)
            resolver = VenvResolver(project_root=root)

            missing_two = ["groq", "PySide6"]
            with patch.object(VenvResolver, "_pip_works", return_value=True), \
                 patch.object(VenvResolver, "_missing_packages", return_value=missing_two):
                env = resolver.resolve()

        self.assertEqual(env.missing_packages, missing_two)

    # -- pyvenv.cfg required -------------------------------------------------

    def test_skips_dir_without_pyvenv_cfg(self):
        """A directory named .venv without pyvenv.cfg must not be accepted."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad_venv = root / ".venv"
            bad_venv.mkdir()
            # No pyvenv.cfg
            resolver = VenvResolver(project_root=root)

            with patch.object(VenvResolver, "_check_running_interpreter", return_value=None), \
                 patch.object(VenvResolver, "_find_best_base_python", return_value=sys.executable), \
                 patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                with patch.object(VenvResolver, "_find_python_exe",
                                   return_value=Path(sys.executable)), \
                     patch.object(VenvResolver, "_missing_packages", return_value=[]):
                    env = resolver.resolve()

        # Should have fallen through to auto-repair
        self.assertTrue(env.created)


# ---------------------------------------------------------------------------
# Singleton / shared-source tests
# ---------------------------------------------------------------------------

class SharedSingletonTests(unittest.TestCase):
    """EnvironmentValidator and StartupManager must read from the same singleton."""

    def setUp(self):
        _vr_module._resolved_env = None

    def test_env_validator_and_startup_manager_use_same_singleton(self):
        """
        After get_resolved_env() is called once (by EnvironmentValidator.__init__),
        the module-level singleton is populated and StartupManager.get_resolved_env()
        returns the identical object.
        """
        fake_env = ResolvedEnv(
            python_exe=sys.executable,
            venv_root=None,
            source="test singleton",
        )
        with patch.object(VenvResolver, "resolve", return_value=fake_env):
            validator = EnvironmentValidator()
            validator_env = validator.resolved_env

            from JARVIS.core.system.venv_resolver import get_resolved_env as _gre
            sm_env = _gre()   # same call startup_manager uses

        self.assertIs(validator_env, sm_env,
                      "EnvironmentValidator and StartupManager must share the same "
                      "ResolvedEnv object from the module-level singleton.")


# ---------------------------------------------------------------------------
# EnvironmentValidator unit tests
# ---------------------------------------------------------------------------

class EnvironmentValidatorTests(unittest.TestCase):

    def setUp(self):
        _vr_module._resolved_env = None

    def _make_validator_with_env(self, resolved_env: ResolvedEnv) -> EnvironmentValidator:
        with patch.object(VenvResolver, "resolve", return_value=resolved_env):
            v = EnvironmentValidator()
        return v

    def test_python_version_error_on_old_version(self):
        env = ResolvedEnv(python_exe=sys.executable, venv_root=None, source="test")
        validator = self._make_validator_with_env(env)
        with patch("sys.version_info", (3, 9)):
            validator._validate_python_version()
        self.assertTrue(any("Python 3.10+ required" in e for e in validator.errors))

    def test_auto_repair_surfaces_as_warning_not_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            venv_root = Path(tmp) / ".venv"
            venv_root.mkdir()
            (venv_root / "pyvenv.cfg").write_text("home = C:\\Python311\n")
            env = ResolvedEnv(
                python_exe=sys.executable,
                venv_root=venv_root,
                source="auto-created .venv (repair)",
                created=True,
            )
            # Validator must run INSIDE the tempdir context so venv_root exists
            validator = self._make_validator_with_env(env)
            validator._validate_venv()

        self.assertFalse(any("auto" in e.lower() for e in validator.errors),
                         "auto-repair must not produce an error")
        self.assertTrue(any("auto-created" in w for w in validator.warnings))

    def test_per_package_error_names_the_package(self):
        """Each missing package should appear by name in a separate error."""
        with tempfile.TemporaryDirectory() as tmp:
            venv_root = Path(tmp) / ".venv"
            venv_root.mkdir()
            (venv_root / "pyvenv.cfg").write_text("home = C:\\Python311\n")
            env = ResolvedEnv(
                python_exe=sys.executable,
                venv_root=venv_root,
                source="test",
                missing_packages=["groq", "PySide6"],
            )
            # Validator must run INSIDE the tempdir context so venv_root exists
            validator = self._make_validator_with_env(env)
            validator._validate_venv()

        errors_text = "\n".join(validator.errors)
        self.assertIn("groq", errors_text)
        self.assertIn("PySide6", errors_text)

    def test_dependencies_reported_individually(self):
        """Each ImportError from _validate_dependencies must produce one error."""
        # python_exe must equal sys.executable so the "running outside venv" guard
        # does NOT skip the in-process __import__ checks.
        env = ResolvedEnv(python_exe=sys.executable, venv_root=None, source="test")
        validator = self._make_validator_with_env(env)
        with patch("builtins.__import__", side_effect=ImportError("mock")):
            validator._validate_dependencies()
        # One error per package in REQUIRED_PACKAGES
        self.assertEqual(len(validator.errors), len(REQUIRED_PACKAGES))


    def test_get_report_includes_venv_source_and_python_exe(self):
        env = ResolvedEnv(
            python_exe="/fake/python",
            venv_root=None,
            source="running interpreter (sys.executable)",
        )
        validator = self._make_validator_with_env(env)
        report = validator.get_report()
        self.assertIn("venv_source", report)
        self.assertIn("python_exe", report)
        self.assertEqual(report["python_exe"], "/fake/python")
        self.assertEqual(report["venv_source"], "running interpreter (sys.executable)")


# ---------------------------------------------------------------------------
# StartupManager tests (unchanged logic, carried forward)
# ---------------------------------------------------------------------------

class StartupManagerTests(unittest.TestCase):

    def test_startup_manager_initializes_services_in_dependency_order(self):
        manager = StartupManager()
        manager._init_service_instance = MagicMock()
        success = manager.initialize_all_services()
        self.assertTrue(success)
        self.assertEqual(manager.service_status["memory_engine"], "READY")
        self.assertEqual(manager.service_status["voice_engine"], "READY")

    def test_startup_manager_recovers_on_retry(self):
        manager = StartupManager()
        calls = []

        def mock_init(name):
            if name == "memory_engine" and not calls:
                calls.append(True)
                raise RuntimeError("transient load error")
            return MagicMock()

        manager._init_service_instance = mock_init
        success = manager.initialize_all_services()
        self.assertTrue(success)
        self.assertEqual(manager.service_status["memory_engine"], "READY")


# ---------------------------------------------------------------------------
# ServiceHealthMonitor tests (unchanged)
# ---------------------------------------------------------------------------

class ServiceMonitorTests(unittest.TestCase):

    def test_service_monitor_registers_services(self):
        monitor = ServiceHealthMonitor()
        mock_service = MagicMock()
        monitor.register_service("test_service", mock_service)
        self.assertEqual(monitor.get_service_status("test_service"), "UNKNOWN")

    def test_service_monitor_health_check_success(self):
        monitor = ServiceHealthMonitor()
        mock_service = MagicMock()
        mock_service.is_alive.return_value = True
        monitor.register_service("test_service", mock_service)
        monitor._check_service_health("test_service", monitor.services["test_service"])
        self.assertEqual(monitor.get_service_status("test_service"), "HEALTHY")

    def test_service_monitor_restarts_crashed_service(self):
        monitor = ServiceHealthMonitor()
        mock_service = MagicMock()
        mock_service.is_alive.return_value = False
        monitor.register_service("test_service", mock_service)
        monitor._check_service_health("test_service", monitor.services["test_service"])
        # ServiceHealthMonitor emits RECOVERING (not RESTARTED) when restart is triggered
        self.assertIn(
            monitor.get_service_status("test_service"),
            ("RESTARTED", "RECOVERING"),
            "Expected service to be in a restart/recovery state after crash",
        )
        mock_service.restart.assert_called_once()


if __name__ == "__main__":
    unittest.main()
