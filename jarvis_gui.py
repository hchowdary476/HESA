#!/usr/bin/env python3
"""
JARVIS GUI Quick Start - Optimized for fast GUI launch
Minimal background services, prioritizes responsive UI
"""

import sys
import os
import time
import json
import threading

# Add project to path
root_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, root_dir)

from dotenv import load_dotenv
from JARVIS.core.system.utils.env_helper import find_env_file

# Load environment
load_dotenv(find_env_file())

def main():
    """Launch JARVIS GUI with minimal startup overhead"""
    
    print("\n============================================================")
    print("JARVIS GUI - Quick Start Mode")
    print("============================================================\n")
    
    try:
        print("Loading QML GUI components...")
        from JARVIS.gui.main_window import main as launch_gui
        print("GUI loaded. Launching dashboard...")
        return launch_gui()
        
    except Exception as e:
        print(f"\nLaunch failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
