"""Automated build, verification and release packaging pipeline task manager."""

from __future__ import annotations
import os
import sys
import zipfile
import subprocess
import shutil
import time

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ReleaseBuilder:
    """Build task runner executing automated checks and packaging bundles."""

    def __init__(self, version: str = "1.0.0") -> None:
        self.version = version
        self.dist_dir = os.path.abspath("dist")

    def clean(self) -> None:
        """Cleans output destination folders."""
        print("[Builder] Clearing output 'dist' directory...")
        if os.path.exists(self.dist_dir):
            for _ in range(3):
                try:
                    shutil.rmtree(self.dist_dir)
                    break
                except Exception:
                    time.sleep(0.2)
            else:
                try:
                    shutil.rmtree(self.dist_dir, ignore_errors=True)
                except Exception:
                    pass
        os.makedirs(self.dist_dir, exist_ok=True)

    def run_tests(self) -> bool:
        """Executes full unit/integration test suites."""
        print("[Builder] Executing automated tests sweeps...")
        try:
            # We call pytest subprocess on key test suites
            res = subprocess.run([
                sys.executable, "-m", "pytest",
                "tests/test_ai_os_core.py",
                "tests/test_enterprise_ai_os.py",
                "tests/test_distributed_platform.py",
                "tests/test_production_memory.py"
            ], capture_output=True, text=True)
            
            if res.returncode == 0:
                print("[Builder] Test verification checks: PASSED.")
                return True
            
            print(f"[Builder] Test verification checks: FAILED.\n{res.stdout}\n{res.stderr}")
            return False
        except Exception as e:
            print(f"[Builder] Verification runner execution error: {e}")
            return False

    def package_portable(self) -> str | None:
        """Bundles active code repositories into portable zip archives."""
        print("[Builder] Bundling directories into portable release package...")
        zip_name = f"JARVIS-portable-v{self.version}.zip"
        zip_path = os.path.join(self.dist_dir, zip_name)

        exclude_dirs = {".venv", ".git", "__pycache__", "dist", ".pytest_cache", "logs", "test_sandbox", "test_platform_sandbox"}
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for root, dirs, files in os.walk("."):
                    # Filter directories in place
                    dirs[:] = [d for d in dirs if d not in exclude_dirs]
                    
                    for f in files:
                        # Exclude cache or temp file patterns
                        if f.endswith((".pyc", ".zip", ".pid")) or f.startswith("."):
                            continue
                            
                        file_path = os.path.join(root, f)
                        arc_path = os.path.relpath(file_path, ".")
                        zip_file.write(file_path, arc_path)

            print(f"[Builder] Portable release package generated at: {zip_path}")
            return zip_path
        except Exception as e:
            print(f"[Builder] Packaging failed: {e}")
            return None

    def generate_release_notes(self) -> str:
        """Compiles formatted markdown notes file."""
        print("[Builder] Generating release logs markdown metadata...")
        notes = f"""# JARVIS Developer Platform Release v{self.version}

Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}

## Key Features

- **Official Client SDK**: Python namespace queries routing prompt calls and memory layers.
- **REST & WS Gateway Server**: Full OpenAPI endpoints mapping and real-time streaming notifications.
- **Scaffolding CLI**: Dynamic template generations, DAG cycle checks, and ai speed benchmarks.
- **Upgrade Setup Wizard**: Auto prerequisite validations, rolling backups, and recovery rollbacks.

## Verified Test Suites

- Unit Tests: passed
- Integration Tests: passed
- Distributed Platform: verified
- Memory Engine: verified
- Total regression checks: zero defects
"""
        notes_path = os.path.join(self.dist_dir, "RELEASE_NOTES.md")
        with open(notes_path, "w", encoding="utf-8") as f:
            f.write(notes)
        print(f"[Builder] Release logs written to: {notes_path}")
        return notes_path


def main() -> None:
    builder = ReleaseBuilder("1.0.0")
    builder.clean()
    if builder.run_tests():
        builder.package_portable()
        builder.generate_release_notes()
        print("\nBuild release compile finished successfully!")
    else:
        print("\nBuild aborted due to test checks failure.")


if __name__ == "__main__":
    main()
