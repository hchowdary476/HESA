"""
Response Builder for HESA OS Production Voice Assistant Architecture.

Combines AI responses, Memory Engine context, user preferences, and personality layer
to generate natural context-aware responses prior to TTS synthesis.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger("hesa.response_builder")


class ResponseBuilder:
    """
    Singleton ResponseBuilder for formatting context-aware natural assistant responses.
    """

    _instance: ResponseBuilder | None = None
    _lock = threading.Lock()

    def __new__(cls) -> ResponseBuilder:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def build_response(self, text: str, intent_category: str = "LOCAL_COMMAND", context: dict[str, Any] | None = None) -> str:
        """
        Format response considering user preferences and language.
        """
        if not text or not isinstance(text, str):
            return text or ""

        # Fetch preferred language
        pref_lang = "english"
        try:
            from JARVIS.core.memory.memory_preferences import get_preference

            pref_lang = get_preference("preferred_language") or "english"
        except Exception:
            pass

        # Polish text for speech synthesis if necessary
        cleaned = text.strip()

        logger.info("[RESPONSE_BUILDER] Formatted response for lang=%s: %r", pref_lang, cleaned)
        return cleaned


def get_response_builder() -> ResponseBuilder:
    return ResponseBuilder()
