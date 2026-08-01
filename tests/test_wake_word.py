"""Unit tests for wake_word.py — SAI wake word detection and false positive rejection.

Tests cover:
  - wake_word_detected()  : returns True for "SAI", "Hey SAI", "Hi SAI", "Okay SAI"
  - extract_inline_command(): extracts trailing commands from SAI wake phrases
  - False positive checks  : guarantees rejection of "say", "sigh", "side", "site", "size", "sai ram", "science"
"""
from __future__ import annotations

import os
import sys

# Ensure project root is on path when running standalone
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Disable [WAKE_DEBUG] stdout noise during tests
os.environ.setdefault("JARVIS_WAKE_DEBUG", "0")

import pytest
from JARVIS.core.voice.wake_word import (
    WAKE_ALIASES,
    WAKE_FUZZY_THRESHOLD,
    analyze_wake_word,
    extract_inline_command,
    normalize_voice_phrase,
    wake_word_detected,
)


# ── normalize_voice_phrase ────────────────────────────────────────────────────

class TestNormalize:
    def test_uppercase(self):
        assert normalize_voice_phrase("HEY SAI") == "hey sai"

    def test_punctuation_removed(self):
        assert normalize_voice_phrase("SAI, open calculator.") == "sai open calculator"

    def test_collapsed_spaces(self):
        assert normalize_voice_phrase("  hey   sai  ") == "hey sai"


# ── wake_word_detected ────────────────────────────────────────────────────────

_MUST_DETECT = [
    "hey sai open calculator",
    "sai open calculator",
    "hi sai play music",
    "okay sai shutdown system",
    "sai what is machine learning",
    "hey sai",
    "sai",
    "hi sai",
    "okay sai",
    "saai",
    "hisai",
    "hey saai open browser",
]

_MUST_NOT_DETECT = [
    # ── Requirement #8 false positives to reject ──────────────────────────────
    "say",
    "sigh",
    "side",
    "site",
    "size",
    "sai ram",
    "science",
    # ── Non-wake phrases ──────────────────────────────────────────────────────
    "open calculator",
    "play music",
    "shutdown pc",
    "hello there",
    "what time is it",
    "",
    "    ",
]


class TestWakeWordDetected:
    @pytest.mark.parametrize("text", _MUST_DETECT)
    def test_detects(self, text: str):
        result = analyze_wake_word(text)
        assert result["detected"], (
            f"Expected DETECTED for '{text}' but got:\n"
            f"  normalized='{result['normalized']}'\n"
            f"  alias_match={result['alias_match']}\n"
            f"  fuzzy_score={result['fuzzy_score']:.3f}\n"
            f"  matched_alias='{result['matched_alias']}'"
        )

    @pytest.mark.parametrize("text", _MUST_NOT_DETECT)
    def test_does_not_detect(self, text: str):
        result = analyze_wake_word(text)
        assert not result["detected"], (
            f"Expected NOT detected for '{text}' but got detected=True "
            f"(matched_alias='{result['matched_alias']}', score={result['fuzzy_score']:.3f})"
        )


# ── analyze_wake_word (result dict fields) ────────────────────────────────────

class TestAnalyzeWakeWord:
    def test_result_keys_present(self):
        r = analyze_wake_word("hey sai open calculator")
        for key in ("detected", "enabled", "wake_word", "normalized", "reason",
                    "cooldown_active", "alias_match", "fuzzy_score", "matched_alias"):
            assert key in r, f"Missing key: {key}"

    def test_alias_match_true_for_variant(self):
        r = analyze_wake_word("saai open calculator")
        assert r["alias_match"] is True
        assert r["detected"] is True

    def test_fuzzy_score_is_float(self):
        r = analyze_wake_word("hey sai open calculator")
        assert isinstance(r["fuzzy_score"], float)

    def test_matched_alias_populated(self):
        r = analyze_wake_word("hisai play music")
        assert r["matched_alias"] != "", "matched_alias should be set on a successful alias match"


    def test_disabled_config(self):
        r = analyze_wake_word("hey sai", config={"enabled": False, "wake_word": "sai", "cooldown_seconds": 0})
        assert not r["detected"]
        assert r["reason"] == "wake word disabled"

    def test_cooldown_blocks(self):
        r = analyze_wake_word(
            "hey sai",
            config={"enabled": True, "wake_word": "sai", "cooldown_seconds": 5.0},
            now=100.0,
            last_detected_at=98.0,  # 2s ago, cooldown=5s → blocked
        )
        assert not r["detected"]
        assert r["cooldown_active"]


# ── extract_inline_command ────────────────────────────────────────────────────

_INLINE_CASES: list[tuple[str, str | None]] = [
    ("hey sai open calculator",     "open calculator"),
    ("sai open chrome",              "open chrome"),
    ("sai what time is it",          "what time is it"),
    ("sai play music",               "play music"),
    ("sai shutdown system",          "shutdown system"),
    ("hey sai",                      None),
    ("sai",                          None),
    ("open calculator",              None),
    ("say open calculator",          None),
    ("sai ram open calculator",      None),
]


class TestExtractInlineCommand:
    @pytest.mark.parametrize("text,expected", _INLINE_CASES)
    def test_extract(self, text: str, expected: str | None):
        result = extract_inline_command(text)
        assert result == expected, (
            f"extract_inline_command('{text}')\n"
            f"  expected: {expected!r}\n"
            f"  got:      {result!r}"
        )


# ── Standalone runner ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    PASS = "[OK]"
    FAIL = "[FAIL]"

    total = passed = failed = 0

    def run_case(label: str, ok: bool, detail: str = "") -> None:
        global total, passed, failed
        total += 1
        if ok:
            passed += 1
            print(f"  {PASS} {label}")
        else:
            failed += 1
            print(f"  {FAIL} {label}")
            if detail:
                print(f"       {detail}")

    print("\n-- normalize_voice_phrase -------------------------------------------")
    nt = TestNormalize()
    for m in [nt.test_uppercase, nt.test_punctuation_removed, nt.test_collapsed_spaces]:
        try:
            m()
            run_case(m.__name__, True)
        except AssertionError as e:
            run_case(m.__name__, False, str(e))

    print("\n-- wake_word_detected -- MUST detect ---------------------------------")
    for text in _MUST_DETECT:
        r = analyze_wake_word(text)
        ok = r["detected"]
        detail = f"normalized='{r['normalized']}' score={r['fuzzy_score']:.3f} alias='{r['matched_alias']}'"
        run_case(repr(text), ok, "" if ok else detail)

    print("\n-- wake_word_detected -- MUST NOT detect -----------------------------")
    for text in _MUST_NOT_DETECT:
        r = analyze_wake_word(text)
        ok = not r["detected"]
        detail = f"wrongly matched alias='{r['matched_alias']}' score={r['fuzzy_score']:.3f}"
        run_case(repr(text) if text else "(empty string)", ok, "" if ok else detail)

    print("\n-- extract_inline_command -------------------------------------------")
    for text, expected in _INLINE_CASES:
        result = extract_inline_command(text)
        ok = result == expected
        detail = f"expected={expected!r} got={result!r}"
        run_case(repr(text), ok, "" if ok else detail)

    print(f"\n{'------------------------------------------------------------'}")
    print(f"  Total: {total}  Passed: {passed}  Failed: {failed}")
    if failed:
        sys.exit(1)
    else:
        print("  ALL TESTS PASSED")
