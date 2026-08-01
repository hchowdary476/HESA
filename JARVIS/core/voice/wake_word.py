"""Wake-word configuration and matching without microphone dependencies.

External User Wake Word: "SAI" (or "Hey SAI", "Hi SAI", "Okay SAI")
Internal Project Identity: HESA (HESA Assistant, HESA OS, HESA Cognitive Core, etc.)
"""

from __future__ import annotations

import difflib
import os
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass

# ── Phonetic wake aliases for external wake word "SAI" ───────────────────────
# Includes regional / Indian English accent phonetics ("saai", "hisai", "heysai").
WAKE_ALIASES: list[str] = [
    "sai",
    "hey sai",
    "hi sai",
    "okay sai",
    "ok sai",
    "heysai",
    "hisai",
    "okaysai",
    "saai",
    "hey saai",
    "hi saai",
    "okay saai",
]

# Explicit false positives to reject (Requirement #8)
REJECTED_WAKE_PHRASES: set[str] = {
    "say",
    "sigh",
    "side",
    "site",
    "size",
    "sai ram",
    "science",
}

# Fuzzy match threshold — phrase-level.
WAKE_FUZZY_THRESHOLD: float = 0.85

_TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}
_FALSE_VALUES = {"0", "false", "no", "off", "disabled"}

# Debug logging control — set JARVIS_WAKE_DEBUG=0 to suppress [WAKE_DEBUG] lines
_WAKE_DEBUG = os.getenv("JARVIS_WAKE_DEBUG", "1") not in {"0", "false", "no"}


def parse_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return default


def normalize_voice_phrase(text: str) -> str:
    """Lowercase, strip ALL punctuation and apostrophes, collapse whitespace.

    Examples::

        normalize_voice_phrase("Hey SAI!")      -> "hey sai"
        normalize_voice_phrase("SAI, open...") -> "sai open"
    """
    cleaned = text.lower().replace("'", "").replace("’", "")
    cleaned = re.sub(r"[^a-zA-Z0-9 ]+", " ", cleaned)
    return " ".join(cleaned.split())


def _alias_match(normalized_text: str) -> tuple[bool, str, float]:
    """Return (matched, matched_alias, best_score) for *normalized_text*.

    Checks explicit false positives first to guarantee rejection of 'say',
    'sigh', 'side', 'site', 'size', 'sai ram', 'science'.
    """
    text_tokens = normalized_text.split()
    if not text_tokens:
        return False, "", 0.0

    # ── 0. Reject False Positives ─────────────────────────────────────────────
    full_norm = " ".join(text_tokens)
    for r in REJECTED_WAKE_PHRASES:
        if full_norm == r or full_norm.startswith(r + " "):
            return False, "", 0.0

    best_alias = ""
    best_score = 0.0

    # Sort aliases longest-first for greedy matching
    sorted_aliases = sorted(WAKE_ALIASES, key=len, reverse=True)

    for alias in sorted_aliases:
        alias_tokens = alias.split()
        n = len(alias_tokens)
        if n == 0:
            continue

        # ── 1. Exact substring (anchored at token positions 0, 1, or 2) ──────
        max_start = min(3, max(0, len(text_tokens) - n + 1))
        for i in range(max_start):
            ngram = " ".join(text_tokens[i: i + n])
            if ngram == alias:
                return True, alias, 1.0

        # ── 2. Phrase-level fuzzy on the first n tokens ───────────────────────
        if len(text_tokens) >= n:
            ngram_tokens = text_tokens[:n]
            ngram = " ".join(ngram_tokens)
            # Skip if any token in the candidate is a known false positive word
            if any(tok in {"say", "sigh", "side", "site", "size", "science"} for tok in ngram_tokens):
                continue

            ratio = difflib.SequenceMatcher(None, ngram, alias).ratio()
            if ratio > best_score:
                best_score = ratio
                best_alias = alias
            if ratio >= WAKE_FUZZY_THRESHOLD:
                return True, alias, ratio

    return False, best_alias, best_score


@dataclass(frozen=True)
class WakeWordConfig:
    wake_word: str = "sai"
    enabled: bool = True
    voice_enabled: bool = True
    cooldown_seconds: float = 1.0


def build_wake_word_config(env: Mapping[str, str] | None = None) -> dict[str, object]:
    source = os.environ if env is None else env
    wake_word = normalize_voice_phrase(source.get("JARVIS_WAKE_WORD", "sai")) or "sai"
    voice_enabled = parse_bool(source.get("JARVIS_VOICE_ENABLED"), True)
    enabled = parse_bool(source.get("JARVIS_WAKE_WORD_ENABLED"), True) and voice_enabled
    try:
        cooldown_seconds = max(0.0, float(source.get("JARVIS_WAKE_WORD_COOLDOWN_SECONDS", "1.0")))
    except (TypeError, ValueError):
        cooldown_seconds = 1.0
    return {
        "wake_word": wake_word,
        "enabled": enabled,
        "voice_enabled": voice_enabled,
        "cooldown_seconds": cooldown_seconds,
    }


def _config_value(config: WakeWordConfig | Mapping[str, object] | None, key: str, default: object) -> object:
    if config is None:
        return default
    if isinstance(config, WakeWordConfig):
        return getattr(config, key)
    return config.get(key, default)


def wake_word_detected(
    text: str,
    *,
    wake_word: str | None = None,
    config: WakeWordConfig | Mapping[str, object] | None = None,
    now: float | None = None,
    last_detected_at: float | None = None,
) -> bool:
    result = analyze_wake_word(text, wake_word=wake_word, config=config, now=now, last_detected_at=last_detected_at)
    return bool(result["detected"])


def analyze_wake_word(
    text: str,
    *,
    wake_word: str | None = None,
    config: WakeWordConfig | Mapping[str, object] | None = None,
    now: float | None = None,
    last_detected_at: float | None = None,
) -> dict[str, object]:
    """Analyse *text* for wake word 'SAI' and return a rich result dict."""
    configured_word = normalize_voice_phrase(wake_word or str(_config_value(config, "wake_word", "sai"))) or "sai"
    enabled = bool(_config_value(config, "enabled", True))
    cooldown_seconds = float(_config_value(config, "cooldown_seconds", 0.0))
    normalized_text = normalize_voice_phrase(text)
    cooldown_active = False

    if not enabled:
        return {
            "detected": False,
            "enabled": False,
            "wake_word": configured_word,
            "normalized": normalized_text,
            "reason": "wake word disabled",
            "cooldown_active": False,
            "alias_match": False,
            "fuzzy_score": 0.0,
            "matched_alias": "",
        }

    if last_detected_at is not None and now is not None and now - last_detected_at < cooldown_seconds:
        cooldown_active = True

    tokens = normalized_text.split()
    wake_tokens = configured_word.split()
    detected = False
    alias_match = False
    fuzzy_score = 0.0
    matched_alias = ""

    if not cooldown_active:
        # ── 0. Reject Explicit False Positives (Requirement #8) ───────────────
        full_norm = " ".join(tokens)
        is_rejected = any(
            full_norm == r or full_norm.startswith(r + " ")
            for r in REJECTED_WAKE_PHRASES
        )
        if not is_rejected:
            # ── 1. Exact token-sequence match against configured wake word ────
            if wake_tokens and len(tokens) >= len(wake_tokens):
                detected = any(
                    tokens[i: i + len(wake_tokens)] == wake_tokens
                    for i in range(min(3, len(tokens) - len(wake_tokens) + 1))
                )

            # ── 2. Phonetic alias + fuzzy match ───────────────────────────────
            if not detected:
                alias_match, matched_alias, fuzzy_score = _alias_match(normalized_text)
                detected = alias_match


    if _WAKE_DEBUG:
        print(
            f"[WAKE_DEBUG] normalized=\"{normalized_text}\" "
            f"alias_match={alias_match} fuzzy_score={fuzzy_score:.3f} "
            f"matched_alias=\"{matched_alias}\" detected={detected}",
            flush=True,
        )

    reason = "detected" if detected else ("cooldown active" if cooldown_active else "not detected")
    return {
        "detected": detected,
        "enabled": enabled,
        "wake_word": configured_word,
        "normalized": normalized_text,
        "reason": reason,
        "cooldown_active": cooldown_active,
        "alias_match": alias_match,
        "fuzzy_score": fuzzy_score,
        "matched_alias": matched_alias,
    }


class WakeWordDetector:
    def __init__(
        self,
        wake_word: str = "sai",
        *,
        enabled: bool = True,
        cooldown_seconds: float = 1.0,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.config = WakeWordConfig(
            wake_word=normalize_voice_phrase(wake_word) or "sai",
            enabled=enabled,
            cooldown_seconds=max(0.0, cooldown_seconds),
        )
        self.clock = clock or time.monotonic
        self.last_detected_at: float | None = None

    def detect(self, text: str) -> dict[str, object]:
        now = self.clock()
        result = analyze_wake_word(text, config=self.config, now=now, last_detected_at=self.last_detected_at)
        if result["detected"]:
            self.last_detected_at = now
        return result


# ── Inline-command extraction for SAI ─────────────────────────────────────────

def extract_inline_command(
    text: str,
    *,
    config: WakeWordConfig | Mapping[str, object] | None = None,
) -> str | None:
    """Strip the wake phrase 'SAI' / 'Hey SAI' / 'Hi SAI' from *text* and return any trailing command.

    Examples::

        extract_inline_command("hey sai open calculator")      -> "open calculator"
        extract_inline_command("sai open chrome")              -> "open chrome"
        extract_inline_command("sai what time is it")          -> "what time is it"
        extract_inline_command("sai play music")               -> "play music"
        extract_inline_command("sai shutdown system")          -> "shutdown system"
        extract_inline_command("hey sai")                      -> None
        extract_inline_command("open calculator")              -> None
    """
    normalized = normalize_voice_phrase(text)
    if not normalized:
        return None

    text_tokens = normalized.split()
    sorted_aliases = sorted(WAKE_ALIASES, key=len, reverse=True)

    # Check false positives
    for r in REJECTED_WAKE_PHRASES:
        if normalized == r or normalized.startswith(r + " "):
            return None

    # ── 1. Exact prefix match ─────────────────────────────────────────────────
    for alias in sorted_aliases:
        if normalized.startswith(alias + " "):
            remainder = normalized[len(alias):].strip()
            return remainder if remainder else None
        if normalized == alias:
            return None

    # ── 2. Fuzzy prefix matching ──────────────────────────────────────────────
    for n in range(4, 0, -1):
        if len(text_tokens) <= n:
            continue
        prefix_tokens = text_tokens[:n]
        if any(tok in {"say", "sigh", "side", "site", "size", "science"} for tok in prefix_tokens):
            continue

        prefix = " ".join(prefix_tokens)
        for alias in sorted_aliases:
            if len(alias.split()) != n:
                continue
            ratio = difflib.SequenceMatcher(None, prefix, alias).ratio()
            if ratio >= WAKE_FUZZY_THRESHOLD:
                remainder = " ".join(text_tokens[n:]).strip()
                return remainder if remainder else None

    return None
