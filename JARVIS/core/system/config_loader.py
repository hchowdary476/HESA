"""
Secure Configuration Loader for HESA (JARVIS) AI Assistant.
Safely loads environment variables, API keys, ports, and feature flags.
"""

from __future__ import annotations

import os
from typing import Any
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass


class ConfigLoader:
    """Unified configuration and environment manager."""

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        return os.environ.get(key, default)

    @classmethod
    def get_bool(cls, key: str, default: bool = False) -> bool:
        val = os.environ.get(key, str(default)).strip().lower()
        return val in ("true", "1", "yes", "on")

    @classmethod
    def get_int(cls, key: str, default: int = 0) -> int:
        try:
            return int(os.environ.get(key, str(default)))
        except ValueError:
            return default

    @classmethod
    def get_float(cls, key: str, default: float = 0.0) -> float:
        try:
            return float(os.environ.get(key, str(default)))
        except ValueError:
            return default

    @classmethod
    def get_api_key(cls, provider: str) -> str | None:
        key_name = f"{provider.upper()}_API_KEY"
        key = os.environ.get(key_name)
        if not key or key.startswith("your_") or key.startswith("here_is_"):
            return None
        return key

    @classmethod
    def is_privacy_mode(cls) -> bool:
        return cls.get_bool("JARVIS_PRIVACY_MODE", False)

    @classmethod
    def get_root_dir(cls) -> Path:
        return ROOT_DIR
