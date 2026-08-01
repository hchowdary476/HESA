"""Interactive Setup and Installation Wizard for JARVIS."""

from __future__ import annotations
import os
import sys
import shutil
import time
from memory_engine import MemoryEngine


class SetupWizard:
    """Pre-flight check validation installer and migration upgrade tools."""

    def __init__(self) -> None:
        self.min_python_version = (3, 9)

    def run_checks(self) -> bool:
        """Evaluates hardware capacity, python versions, and dependencies maps."""
        print("[Wizard] Executing system compatibility audits...")
        time.sleep(0.2)

        # 1. Check Python version
        cur_version = sys.version_info
        if cur_version < self.min_python_version:
            print(f"  - [Audit] FAILED: Requires Python >= 3.9 (Current: {cur_version.major}.{cur_version.minor})")
            return False
        print(f"  - [Audit] PASSED: Python version: {cur_version.major}.{cur_version.minor}")

        # 2. Check Disk Space availability
        try:
            total, used, free = shutil.disk_usage(".")
            free_mb = free / (1024 * 1024)
            if free_mb < 100.0:
                print(f"  - [Audit] WARNING: Low free disk space ({free_mb:.1f} MB available)")
            else:
                print(f"  - [Audit] PASSED: Disk space: {free_mb/1024:.1f} GB free")
        except Exception:
            pass

        # 3. Check requirements mapping exists
        if os.path.exists("requirements.txt"):
            print("  - [Audit] PASSED: requirements.txt dependencies mapping located.")
        else:
            print("  - [Audit] WARNING: requirements.txt is missing in current path.")

        return True

    def configure_environment(self, mock_inputs: dict[str, str] | None = None) -> None:
        """Prompts wizard parameters config options and updates settings .env."""
        print("\n--- JARVIS Environment Configuration ---")
        
        # Default choices
        port = "18010"
        api_key = "jarvis_secret_key"

        if mock_inputs:
            port = mock_inputs.get("port", port)
            api_key = mock_inputs.get("api_key", api_key)
        else:
            # Interactive prompts in terminal
            try:
                user_port = input(f"Enter server HTTP API Port [{port}]: ").strip()
                if user_port:
                    port = user_port
                user_key = input(f"Enter developer security API Key [{api_key}]: ").strip()
                if user_key:
                    api_key = user_key
            except (KeyboardInterrupt, EOFError):
                print("\nConfiguration aborted. Using defaults.")

        # Write or append to .env
        env_path = ".env"
        try:
            lines = []
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            
            # Update key/port values
            new_lines = []
            keys_written = set()
            for line in lines:
                if line.startswith("API_PORT="):
                    new_lines.append(f"API_PORT={port}\n")
                    keys_written.add("API_PORT")
                elif line.startswith("API_KEY="):
                    new_lines.append(f"API_KEY={api_key}\n")
                    keys_written.add("API_KEY")
                else:
                    new_lines.append(line)
                    
            if "API_PORT" not in keys_written:
                new_lines.append(f"API_PORT={port}\n")
            if "API_KEY" not in keys_written:
                new_lines.append(f"API_KEY={api_key}\n")

            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            print(f"[Wizard] Configuration environment successfully updated in '{env_path}'")
        except Exception as e:
            print(f"[Wizard] Failed to save configuration to .env: {e}")

    def backup_before_upgrade(self, backup_dir: str = "logs/backups") -> str | None:
        """Pre-upgrade rolling safety database pack."""
        print("[Wizard] Executing pre-upgrade safety database snapshot...")
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = int(time.time())
        backup_zip = os.path.join(backup_dir, f"pre_upgrade_backup_{timestamp}.zip")
        
        mem = MemoryEngine()
        success = mem.create_backup(backup_zip)
        if success:
            print(f"[Wizard] Safe restore backup compiled successfully at: {backup_zip}")
            return backup_zip
        
        print("[Wizard] WARNING: Database backup failed.")
        return None

    def rollback_upgrade(self, backup_zip: str) -> bool:
        """Restores memory database if upgrade experiences failure."""
        print(f"[Wizard] Triggering rollback sequence using: {backup_zip}")
        mem = MemoryEngine()
        return mem.restore_backup(backup_zip)


def main() -> None:
    wiz = SetupWizard()
    if wiz.run_checks():
        wiz.configure_environment()
        print("\nSetup wizard successfully finished! You can start JARVIS by typing 'jarvis start'")
    else:
        print("\nPrerequisite check failed. Please check errors above.")


if __name__ == "__main__":
    main()
