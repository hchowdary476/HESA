import os
import shutil
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]

def clean_dir(dir_path: Path):
    if dir_path.exists() and dir_path.is_dir():
        print(f"Removing directory: {dir_path}")
        try:
            shutil.rmtree(dir_path)
            print(f"Successfully deleted {dir_path}")
        except Exception as e:
            print(f"Failed to delete {dir_path}: {e}")

def main():
    print("Starting JARVIS Workspace Cleanup...")

    # 1. Delete dist/
    clean_dir(WORKSPACE_ROOT / "dist")

    # 2. Delete build/
    clean_dir(WORKSPACE_ROOT / "build")

    # 3. Delete .pytest_cache/
    clean_dir(WORKSPACE_ROOT / " .pytest_cache")
    clean_dir(WORKSPACE_ROOT / ".pytest_cache")

    # 4. Delete __pycache__ folders recursively
    for path in list(WORKSPACE_ROOT.rglob("__pycache__")):
        clean_dir(path)

    # 5. Delete duplicate zip files under release/
    release_dir = WORKSPACE_ROOT / "release"
    if release_dir.exists():
        for item in release_dir.glob("*.zip"):
            print(f"Removing duplicate zip file: {item}")
            try:
                item.unlink()
                print(f"Successfully deleted {item}")
            except Exception as e:
                print(f"Failed to delete {item}: {e}")

    # 6. Delete old/duplicate backup files under logs/backups
    # Analyze backups using cleanup_audit logic to find obsolete and duplicate files
    from cleanup_audit import analyze_backups
    backup_info = analyze_backups()
    
    files_to_delete = []
    
    # Add obsolete backups (older than latest 10 versions)
    for b in backup_info.get("obsolete", []):
        files_to_delete.append(Path(b["path"]))
        
    # Add duplicate backups (SHA256 matches)
    for b in backup_info.get("duplicates", []):
        files_to_delete.append(Path(b["path"]))
        
    # Add other temp/backup patterns (.bak files)
    backup_root = WORKSPACE_ROOT / "logs" / "backups"
    if backup_root.exists():
        for item in backup_root.rglob("*.bak"):
            files_to_delete.append(item)

    # Deduplicate paths
    unique_files = list(set(files_to_delete))
    for filepath in unique_files:
        if filepath.exists() and filepath.is_file():
            print(f"Removing backup/temporary file: {filepath}")
            try:
                filepath.unlink()
                print(f"Successfully deleted {filepath}")
            except Exception as e:
                print(f"Failed to delete {filepath}: {e}")

    print("Cleanup process completed successfully.")

if __name__ == "__main__":
    main()
