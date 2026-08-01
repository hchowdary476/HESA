#!/usr/bin/env python3
"""
Fast Build Script for Open.Jarvis
Optimized for speed while maintaining quality
"""

import subprocess
import shutil
import time
from pathlib import Path


def clean_build_artifacts():
    """Remove old build artifacts for clean build"""
    print("🧹 Cleaning old build artifacts...")
    dirs_to_remove = [
        Path('build'),
        Path('dist'),
        Path('.pytest_cache'),
    ]
    
    for dir_path in dirs_to_remove:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"   ✓ Removed {dir_path}")


def build_with_pyinstaller():
    """Build using optimized PyInstaller spec"""
    print("\n⚙️  Building Open.Jarvis with PyInstaller...")
    print("   Using optimized spec with:")
    print("   • Module exclusions (scipy, sklearn, pandas)")
    print("   • Python optimization level 2")
    print("   • Strip symbols enabled")
    print("   • UPX compression enabled")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            ['pyinstaller', 'Open.Jarvis.spec', '-y'],
            check=True,
            capture_output=True,
            text=True
        )
        
        elapsed = time.time() - start_time
        print(f"\n✅ Build completed in {elapsed:.1f} seconds")
        
        # Check output
        exe_path = Path('dist/Open.Jarvis/Open.Jarvis.exe')
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"   Executable: {exe_path.name} ({size_mb:.1f} MB)")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed!")
        print(f"Error: {e.stderr}")
        return False


def main():
    """Main build process"""
    print("╔════════════════════════════════════════════╗")
    print("║  OPEN.JARVIS FAST BUILD SCRIPT            ║")
    print("║  Optimized for Speed & Quality            ║")
    print("╚════════════════════════════════════════════╝\n")
    
    # Clean
    clean_build_artifacts()
    
    # Build
    success = build_with_pyinstaller()
    
    if success:
        print("\n" + "="*50)
        print("✅ BUILD SUCCESSFUL")
        print("="*50)
        print("\nBuild available at: ./dist/Open.Jarvis/")
        return 0
    else:
        print("\n" + "="*50)
        print("❌ BUILD FAILED")
        print("="*50)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
