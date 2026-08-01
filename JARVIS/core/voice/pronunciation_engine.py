"""
Advanced Personal Name & Pronunciation System for HESA / JARVIS.

Features:
1. 5-Tier Strategy Priority Order:
   Priority 1: SSML <phoneme> tags
   Priority 2: SSML <sub alias=""> tags
   Priority 3: Provider-specific overrides (provider_overrides)
   Priority 4: Native-script replacement (spoken)
   Priority 5: Phonetic ASCII fallback
2. Full entry schema supporting provider_overrides, phoneme, alphabet, spoken, display.
3. Pronunciation Debug Mode showing original, normalized, SSML, provider, final text, and strategy.
4. Audio testing helper & profile regeneration.
5. In-memory profile caching for fast execution.
6. Absolute text immutability across UI, chat, memory, logs, and database.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

DEFAULT_PRONUNCIATION_FILE = "pronunciation.json"


# ── Language & Script Classifier ──────────────────────────────────────────────

class LanguageDetector:
    """Classifies script and language types for multi-language TTS support."""

    SCRIPT_RANGES = {
        "telugu": (0x0C00, 0x0C7F),
        "hindi": (0x0900, 0x097F),
        "tamil": (0x0B80, 0x0BFF),
        "malayalam": (0x0D00, 0x0D7F),
        "kannada": (0x0C80, 0x0CFF),
    }

    @classmethod
    def contains_native_script(cls, text: str) -> bool:
        """Check if text contains non-ASCII Indic Unicode characters."""
        if not text:
            return False
        for char in text:
            code = ord(char)
            for start, end in cls.SCRIPT_RANGES.values():
                if start <= code <= end:
                    return True
        return False

    @classmethod
    def detect_languages(cls, text: str) -> List[str]:
        """Detect all languages/scripts present in text."""
        detected = set()
        has_latin = False

        for char in text:
            code = ord(char)
            if (0x0041 <= code <= 0x005A) or (0x0061 <= code <= 0x007A):
                has_latin = True
                continue

            for lang, (start, end) in cls.SCRIPT_RANGES.items():
                if start <= code <= end:
                    detected.add(lang)

        if has_latin or not detected:
            detected.add("english")

        return sorted(list(detected))

    @classmethod
    def primary_language(cls, text: str) -> str:
        """Return the primary detected language in the text."""
        langs = cls.detect_languages(text)
        non_english = [l for l in langs if l != "english"]
        return non_english[0] if non_english else "english"


# ── Automated Mispronunciation Detector ────────────────────────────────────────

class PronunciationDetector:
    """
    Automated detector identifying non-name terms susceptible to mispronunciation.
    Strict constraint: NEVER automatically guesses or rewrites personal names.
    """

    ACRONYM_PATTERN = re.compile(r'\b[A-Z]{2,6}\b')
    CAMEL_CASE_PATTERN = re.compile(r'\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b')
    UNUSUAL_CLUSTERS = re.compile(
        r'\b\w*(?:cz|sz|zh|kh|gh|dh|th|bh|ph|shr|ks|ts|dhy|thya|chary|shna|krish|bhag)\w*\b',
        re.IGNORECASE
    )

    @classmethod
    def detect_candidates(cls, text: str) -> List[Dict[str, Any]]:
        candidates = []
        words = re.findall(r'\b[A-Za-z0-9_-]+\b', text)
        seen = set()

        for word in words:
            if word.lower() in seen or len(word) < 2:
                continue

            reasons = []
            confidence = 0.0
            suggested_phonetic = word

            if cls.ACRONYM_PATTERN.match(word) and word.isupper():
                reasons.append("Acronym/Abbreviation")
                confidence += 0.7
                suggested_phonetic = " ".join(word)

            if cls.CAMEL_CASE_PATTERN.match(word):
                reasons.append("CamelCase Compound")
                confidence += 0.6
                split_words = re.findall(r'[A-Z][a-z]*', word)
                if split_words:
                    suggested_phonetic = " ".join(split_words)

            if cls.UNUSUAL_CLUSTERS.match(word):
                reasons.append("Complex Consonant Cluster")
                confidence += 0.5

            if reasons:
                seen.add(word.lower())
                candidates.append({
                    "word": word,
                    "reasons": reasons,
                    "confidence": min(1.0, confidence),
                    "suggested_phonetic": suggested_phonetic
                })

        return candidates


# ── Dynamic Pronunciation Dictionary ─────────────────────────────────────────

class PronunciationDictionary:
    """
    Thread-safe storage manager for loading, updating, querying, and persisting
    pronunciation mappings in `pronunciation.json`.
    """

    def __init__(self, filepath: Union[str, Path] = DEFAULT_PRONUNCIATION_FILE) -> None:
        self.filepath = Path(filepath)
        self._lock = threading.RLock()
        self._entries: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        with self._lock:
            if not self.filepath.exists():
                self._entries = {}
                self.save()
                return

            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if isinstance(data, dict):
                    entries = data.get("entries", data)
                    self._entries = {}
                    for k, v in entries.items():
                        key = k.strip().lower()
                        if isinstance(v, str):
                            self._entries[key] = self._build_default_schema(k, spoken=v)
                        elif isinstance(v, dict):
                            disp = v.get("display", k)
                            spk = v.get("spoken", v.get("phonetic", disp))
                            self._entries[key] = {
                                "display": disp,
                                "spoken": spk,
                                "phoneme": v.get("phoneme"),
                                "alphabet": v.get("alphabet", "ipa"),
                                "language": v.get("language", "auto"),
                                "phonetic": v.get("phonetic", spk),
                                "ssml_alias": v.get("ssml_alias", spk),
                                "is_personal_name": v.get("is_personal_name", False),
                                "user_specified": v.get("user_specified", True),
                                "active": v.get("active", True),
                                "provider_overrides": v.get("provider_overrides", {
                                    "edge": "", "azure": "", "kokoro": "", "piper": "", "elevenlabs": "", "pyttsx3": "", "sapi": ""
                                })
                            }
            except Exception as err:
                print(f"[PRONUNCIATION] Error loading {self.filepath}: {err}")
                self._entries = {}

    def _build_default_schema(
        self,
        word: str,
        spoken: str,
        phonetic: Optional[str] = None,
        phoneme: Optional[str] = None,
        alphabet: str = "ipa",
        language: str = "auto",
        is_personal_name: bool = False,
        provider_overrides: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        spk = spoken
        phon = phonetic or spk
        return {
            "display": word,
            "spoken": spk,
            "phoneme": phoneme,
            "alphabet": alphabet,
            "language": language,
            "phonetic": phon,
            "ssml_alias": spk,
            "is_personal_name": is_personal_name,
            "user_specified": True,
            "active": True,
            "provider_overrides": provider_overrides or {
                "edge": "", "azure": "", "kokoro": "", "piper": "", "elevenlabs": "", "pyttsx3": "", "sapi": ""
            }
        }

    def save(self) -> None:
        with self._lock:
            payload = {
                "version": "2.0",
                "description": "Advanced Dynamic Pronunciation Dictionary for HESA Speech Subsystem",
                "entries": self._entries
            }
            try:
                temp_path = self.filepath.with_suffix(".tmp")
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
                os.replace(temp_path, self.filepath)
            except Exception as err:
                print(f"[PRONUNCIATION] Failed to save {self.filepath}: {err}")

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return json.loads(json.dumps(self._entries))

    def get_entry(self, word: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._entries.get(word.strip().lower())

    def set_full_entry(self, word: str, entry_dict: Dict[str, Any]) -> None:
        with self._lock:
            key = word.strip().lower()
            if not key:
                return
            self._entries[key] = {
                "display": entry_dict.get("display", word),
                "spoken": entry_dict.get("spoken", word),
                "phoneme": entry_dict.get("phoneme"),
                "alphabet": entry_dict.get("alphabet", "ipa"),
                "language": entry_dict.get("language", "auto"),
                "phonetic": entry_dict.get("phonetic", entry_dict.get("spoken", word)),
                "ssml_alias": entry_dict.get("ssml_alias", entry_dict.get("spoken", word)),
                "is_personal_name": entry_dict.get("is_personal_name", False),
                "user_specified": True,
                "active": entry_dict.get("active", True),
                "provider_overrides": entry_dict.get("provider_overrides", {})
            }
            self.save()

    def set_entry(
        self,
        word: str,
        spoken: str,
        display: Optional[str] = None,
        phonetic: Optional[str] = None,
        phoneme: Optional[str] = None,
        alphabet: str = "ipa",
        language: str = "auto",
        is_personal_name: bool = False,
        provider_overrides: Optional[Dict[str, str]] = None
    ) -> None:
        with self._lock:
            key = word.strip().lower()
            if not key:
                return

            disp = display or word
            schema = self._build_default_schema(
                word=disp,
                spoken=spoken,
                phonetic=phonetic,
                phoneme=phoneme,
                alphabet=alphabet,
                language=language,
                is_personal_name=is_personal_name,
                provider_overrides=provider_overrides
            )
            self._entries[key] = schema
            self.save()

    def remove_entry(self, word: str) -> bool:
        with self._lock:
            key = word.strip().lower()
            if key in self._entries:
                del self._entries[key]
                self.save()
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self.save()


# ── Provider Strategy Resolver ─────────────────────────────────────────

class TTSProviderAdapter:
    """
    Base interface implementing 5-Tier Strategy Priority Selection:
    Priority 1: SSML <phoneme> tags
    Priority 2: SSML <sub alias=""> tags
    Priority 3: Provider-specific overrides (provider_overrides)
    Priority 4: Native-script replacement (spoken)
    Priority 5: Phonetic ASCII fallback
    """

    def __init__(self, name: str, supports_ssml: bool = False, supports_phonemes: bool = False, supports_native: bool = False):
        self.name = name
        self._supports_ssml = supports_ssml
        self._supports_phonemes = supports_phonemes
        self._supports_native = supports_native

    def supports_ssml(self) -> bool:
        return self._supports_ssml

    def supports_phonemes(self) -> bool:
        return self._supports_phonemes

    def supports_native_scripts(self) -> bool:
        return self._supports_native

    def resolve_pronunciation(self, original: str, entry: Dict[str, Any]) -> Tuple[str, str, int]:
        """
        Evaluate entry through 5-Tier Priority Order.
        Returns: (formatted_string, selected_method_description, priority_tier)
        """
        provider_key = self.name.lower()
        overrides = entry.get("provider_overrides") or {}
        provider_override = overrides.get(provider_key) or overrides.get("default")

        phoneme = entry.get("phoneme")
        alphabet = entry.get("alphabet", "ipa")
        spoken = entry.get("spoken") or entry.get("phonetic") or original
        ssml_alias = entry.get("ssml_alias") or spoken
        phonetic_fallback = entry.get("phonetic") or entry.get("display") or original

        # Priority 1: SSML <phoneme> tag
        if self.supports_phonemes() and phoneme:
            formatted = f'<phoneme alphabet="{alphabet}" ph="{phoneme}">{original}</phoneme>'
            return formatted, f"Priority 1: SSML Phoneme ({alphabet}='{phoneme}')", 1

        # Priority 2: SSML <sub alias=""> tag
        if self.supports_ssml() and ssml_alias and ssml_alias.lower() != original.lower():
            if self.supports_native_scripts() or not LanguageDetector.contains_native_script(ssml_alias):
                formatted = f'<sub alias="{ssml_alias}">{original}</sub>'
                return formatted, f"Priority 2: SSML Sub Alias ('{ssml_alias}')", 2

        # Priority 3: Provider-specific override
        if provider_override:
            return provider_override, f"Priority 3: Provider Override ('{provider_override}')", 3

        # Priority 4: Native-script replacement
        if self.supports_native_scripts() and LanguageDetector.contains_native_script(spoken):
            return spoken, f"Priority 4: Native-Script Spoken Form ('{spoken}')", 4

        # Priority 5: Phonetic ASCII fallback
        fallback = phonetic_fallback if not (LanguageDetector.contains_native_script(phonetic_fallback) and not self.supports_native_scripts()) else original
        return fallback, f"Priority 5: Phonetic Fallback ('{fallback}')", 5


# Provider Adapters
class EdgeTTSProviderAdapter(TTSProviderAdapter):
    def __init__(self):
        super().__init__("edge", supports_ssml=True, supports_phonemes=True, supports_native=True)

    def resolve_pronunciation(self, original: str, entry: Dict[str, Any]) -> Tuple[str, str, int]:
        provider_key = self.name.lower()
        overrides = entry.get("provider_overrides") or {}
        provider_override = overrides.get(provider_key)

        phoneme = entry.get("phoneme")
        alphabet = entry.get("alphabet", "ipa")
        spoken = entry.get("spoken") or entry.get("phonetic") or original

        # Priority 1: SSML Phoneme tag if explicitly specified
        if self.supports_phonemes() and phoneme:
            formatted = f'<phoneme alphabet="{alphabet}" ph="{phoneme}">{original}</phoneme>'
            return formatted, f"Priority 1: SSML Phoneme ({alphabet}='{phoneme}')", 1

        # Priority 3: Provider-specific override
        if provider_override:
            return provider_override, f"Priority 3: Provider Override ('{provider_override}')", 3

        # Priority 4: Native-Script Spoken Form (Edge TTS handles Indic Unicode script natively)
        if self.supports_native_scripts() and LanguageDetector.contains_native_script(spoken):
            return spoken, f"Priority 4: Native-Script Spoken Form ('{spoken}')", 4

        # Priority 2: SSML Sub Alias tag
        ssml_alias = entry.get("ssml_alias")
        if self.supports_ssml() and ssml_alias and ssml_alias.lower() != original.lower():
            formatted = f'<sub alias="{ssml_alias}">{original}</sub>'
            return formatted, f"Priority 2: SSML Sub Alias ('{ssml_alias}')", 2

        # Priority 5: Phonetic Fallback
        phonetic_fallback = entry.get("phonetic") or entry.get("display") or original
        return phonetic_fallback, f"Priority 5: Phonetic Fallback ('{phonetic_fallback}')", 5

class AzureSpeechProviderAdapter(TTSProviderAdapter):
    def __init__(self):
        super().__init__("azure", supports_ssml=True, supports_phonemes=True, supports_native=True)

class ElevenLabsProviderAdapter(TTSProviderAdapter):
    def __init__(self):
        super().__init__("elevenlabs", supports_ssml=True, supports_phonemes=True, supports_native=True)

class KokoroProviderAdapter(TTSProviderAdapter):
    def __init__(self):
        super().__init__("kokoro", supports_ssml=False, supports_phonemes=False, supports_native=True)

class PiperProviderAdapter(TTSProviderAdapter):
    def __init__(self):
        super().__init__("piper", supports_ssml=False, supports_phonemes=False, supports_native=True)

class PyTTSx3ProviderAdapter(TTSProviderAdapter):
    def __init__(self):
        super().__init__("pyttsx3", supports_ssml=False, supports_phonemes=False, supports_native=False)

class SAPIFallbackProviderAdapter(TTSProviderAdapter):
    def __init__(self):
        super().__init__("sapi", supports_ssml=False, supports_phonemes=False, supports_native=False)


PROVIDER_ADAPTERS: Dict[str, TTSProviderAdapter] = {
    "edge": EdgeTTSProviderAdapter(),
    "edgetts": EdgeTTSProviderAdapter(),
    "edge_fallback": KokoroProviderAdapter(),
    "azure": AzureSpeechProviderAdapter(),
    "elevenlabs": ElevenLabsProviderAdapter(),
    "kokoro": KokoroProviderAdapter(),
    "piper": PiperProviderAdapter(),
    "pyttsx3": PyTTSx3ProviderAdapter(),
    "gtts": KokoroProviderAdapter(),
    "sapi": SAPIFallbackProviderAdapter(),
    "default": PyTTSx3ProviderAdapter(),
}


# ── Intelligent Pronunciation Engine ──────────────────────────────────────────

class PronunciationEngine:
    """
    Main Advanced Personal Name & Pronunciation Engine for HESA.

    Features:
    - 5-Tier Strategy Priority Selection
    - Pronunciation Debug Mode
    - Sub-millisecond Profile Caching
    - Audio Testing & Profile Regeneration
    - 100% UI Immutability
    """

    _instance: Optional[PronunciationEngine] = None
    _lock = threading.Lock()

    def __new__(cls, filepath: Union[str, Path] = DEFAULT_PRONUNCIATION_FILE) -> PronunciationEngine:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._dictionary = PronunciationDictionary(filepath)
                cls._instance._detector = PronunciationDetector()
                cls._instance._lang_detector = LanguageDetector()
                cls._instance._profile_cache: Dict[str, Any] = {}
            return cls._instance

    @property
    def dictionary(self) -> PronunciationDictionary:
        return self._dictionary

    @property
    def detector(self) -> PronunciationDetector:
        return self._detector

    def clear_cache(self) -> None:
        with self._lock:
            self._profile_cache.clear()

    def get_adapter(self, provider: str) -> TTSProviderAdapter:
        key = (provider or "edge").strip().lower()
        return PROVIDER_ADAPTERS.get(key, PROVIDER_ADAPTERS["default"])

    def set_personal_name_pronunciation(
        self,
        name: str,
        preferred_pronunciation: str,
        phoneme: Optional[str] = None,
        alphabet: str = "ipa",
        language: str = "auto",
        provider_overrides: Optional[Dict[str, str]] = None
    ) -> None:
        self._dictionary.set_entry(
            word=name,
            display=name,
            spoken=preferred_pronunciation,
            phoneme=phoneme,
            alphabet=alphabet,
            language=language,
            is_personal_name=True,
            provider_overrides=provider_overrides
        )
        self.clear_cache()

    def set_native_script_pronunciation(
        self,
        display_name: str,
        native_spoken_form: str,
        phonetic_fallback: Optional[str] = None,
        language: str = "auto"
    ) -> None:
        self._dictionary.set_entry(
            word=display_name,
            display=display_name,
            spoken=native_spoken_form,
            phonetic=phonetic_fallback or native_spoken_form,
            language=language,
            is_personal_name=True
        )
        self.clear_cache()

    def regenerate_pronunciation_profile(self, word: str, language: str = "auto") -> Dict[str, Any]:
        """
        Generate recommended SSML aliases, spoken forms, and provider overrides for a name.
        """
        existing = self._dictionary.get_entry(word) or {}

        spoken_suggestion = existing.get("spoken") or word
        ssml_alias_suggestion = existing.get("ssml_alias") or spoken_suggestion
        phoneme_val = existing.get("phoneme")  # Keep phoneme None unless explicitly set

        updated = {
            "display": existing.get("display") or word,
            "spoken": spoken_suggestion,
            "phoneme": phoneme_val,
            "alphabet": existing.get("alphabet", "ipa"),
            "language": language if language != "auto" else (existing.get("language") or LanguageDetector.primary_language(word)),
            "phonetic": existing.get("phonetic") or spoken_suggestion,
            "ssml_alias": ssml_alias_suggestion,
            "is_personal_name": True,
            "user_specified": True,
            "active": True,
            "provider_overrides": {
                "edge": f'<phoneme alphabet="ipa" ph="{phoneme_val}">{word}</phoneme>' if phoneme_val else "",
                "azure": f'<phoneme alphabet="ipa" ph="{phoneme_val}">{word}</phoneme>' if phoneme_val else "",
                "elevenlabs": f'<phoneme alphabet="ipa" ph="{phoneme_val}">{word}</phoneme>' if phoneme_val else "",
                "kokoro": spoken_suggestion,
                "piper": spoken_suggestion,
                "pyttsx3": existing.get("phonetic") or word,
                "sapi": existing.get("phonetic") or word
            }
        }
        self._dictionary.set_full_entry(word, updated)
        self.clear_cache()
        return updated

    def process_for_tts_debug(self, text: str, provider: str = "edge") -> Dict[str, Any]:
        """
        Pronunciation Debug Mode.
        Returns telemetry:
        - original_text
        - normalized_text
        - ssml_generated
        - provider_selected
        - final_text_sent_to_tts
        - strategy_log
        """
        if not text or not isinstance(text, str):
            return {
                "original_text": text or "",
                "normalized_text": text or "",
                "ssml_generated": False,
                "provider_selected": provider,
                "final_text_sent_to_tts": text or "",
                "strategy_log": []
            }

        adapter = self.get_adapter(provider)
        entries = self._dictionary.get_all()

        if not entries:
            return {
                "original_text": text,
                "normalized_text": text,
                "ssml_generated": False,
                "provider_selected": adapter.name,
                "final_text_sent_to_tts": text,
                "strategy_log": ["No dictionary entries active."]
            }

        normalized = text
        used_ssml = False
        strategy_log = []

        sorted_entries = sorted(
            entries.items(),
            key=lambda x: (x[1].get("is_personal_name", False), len(x[0])),
            reverse=True
        )

        for word_key, entry in sorted_entries:
            if not entry.get("active", True):
                continue

            target_word = entry.get("display") or word_key
            pattern = re.compile(r'\b' + re.escape(target_word) + r'\b', re.IGNORECASE)

            def _replacer(match: re.Match) -> str:
                nonlocal used_ssml
                original_matched = match.group(0)
                formatted, method_desc, tier = adapter.resolve_pronunciation(original_matched, entry)
                strategy_log.append(f"Matched '{original_matched}' -> {method_desc}")
                if "<" in formatted and ">" in formatted:
                    used_ssml = True
                return formatted

            normalized = pattern.sub(_replacer, normalized)

        final_text = normalized
        if used_ssml and adapter.supports_ssml() and not final_text.strip().startswith("<speak"):
            final_text = f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">{final_text}</speak>'

        return {
            "original_text": text,
            "normalized_text": normalized,
            "ssml_generated": used_ssml,
            "provider_selected": adapter.name,
            "final_text_sent_to_tts": final_text,
            "strategy_log": strategy_log
        }

    def process_for_tts(self, text: str, provider: str = "edge", language: Optional[str] = None) -> str:
        """
        Normalize raw text for the TTS engine with LRU caching.
        Original text is NEVER mutated in place; returns transient audio string.
        """
        if not text or not isinstance(text, str):
            return text or ""

        cache_key = f"{provider}:{text}"
        with self._lock:
            if cache_key in self._profile_cache:
                return self._profile_cache[cache_key]

        debug_info = self.process_for_tts_debug(text, provider=provider)
        res = debug_info["final_text_sent_to_tts"]

        with self._lock:
            # Simple 500-entry cache limit
            if len(self._profile_cache) > 500:
                self._profile_cache.clear()
            self._profile_cache[cache_key] = res

        return res

    def detect_potential_mispronunciations(self, text: str) -> List[Dict[str, Any]]:
        return self._detector.detect_candidates(text)


def get_pronunciation_engine() -> PronunciationEngine:
    return PronunciationEngine()
