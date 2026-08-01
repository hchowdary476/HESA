"""Utility to locate the .env file path robustly in both source and frozen modes."""

from __future__ import annotations

import sys
from pathlib import Path


def find_env_file() -> Path:
    """Find the correct path to the .env file."""
    if getattr(sys, "frozen", False):
        exe_path = Path(sys.executable).resolve()
        # Candidate 1: same directory as executable
        cand1 = exe_path.parent / ".env"
        if cand1.exists():
            return cand1
        # Candidate 2: parent directory of executable directory (e.g. JARVIS/JARVIS.exe layout)
        cand2 = exe_path.parent.parent / ".env"
        if cand2.exists():
            return cand2
        # Candidate 3: check if .env.example exists in parent directory
        if (exe_path.parent.parent / ".env.example").exists():
            return exe_path.parent.parent / ".env"
        # Fallback to same directory as executable
        return exe_path.parent / ".env"

    # Source mode: walk up parents to locate the repository root containing .env or .env.example
    current = Path(__file__).resolve().parent
    for _ in range(6):
        if (current / ".env").exists() or (current / ".env.example").exists():
            return current / ".env"
        current = current.parent

    # Fallback to repository root (5 levels up from env_helper.py)
    source_root = Path(__file__).resolve().parents[4]
    return source_root / ".env"
