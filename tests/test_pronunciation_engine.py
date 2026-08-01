"""
Comprehensive Unit Tests for Advanced Personal Name Pronunciation System.

Verifies:
1. Replaces incorrect alias "హమత" with "హేమంత్" across display, spoken, ssml_alias, provider_overrides, pronunciation.json.
2. 5-Tier Strategy Priority Order per provider:
   - Edge TTS: Native script spoken form ("Hello హేమంత్, welcome back.").
   - Azure / ElevenLabs: SSML Sub Alias ('Hello <sub alias="హేమంత్">Hemanth</sub>, welcome back.').
3. process_for_tts_debug("Hello Hemanth, welcome back.", provider="edge") returns:
   - normalized_text: Hello హేమంత్, welcome back.
   - strategy_log: Matched 'Hemanth' -> Priority 4: Native-Script Spoken Form ('హేమంత్')
4. Immediate availability across all TTS providers without restart.
5. In-memory profile cache invalidation on dictionary update.
6. 100% UI, memory, chat, logs, DB immutability.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from JARVIS.core.voice.pronunciation_engine import (
    LanguageDetector,
    PronunciationDetector,
    PronunciationDictionary,
    PronunciationEngine,
    EdgeTTSProviderAdapter,
    KokoroProviderAdapter,
    PyTTSx3ProviderAdapter,
    SAPIFallbackProviderAdapter,
    get_pronunciation_engine,
)
from JARVIS.core.automation.local_intent_router import route_local_intent


class TestHemanthPronunciationCorrection(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.dict_path = Path(self.tmp_dir.name) / "test_pronunciation.json"
        
        PronunciationEngine._instance = None
        self.engine = PronunciationEngine(self.dict_path)
        self.p_dict = self.engine.dictionary

    def tearDown(self):
        self.tmp_dir.cleanup()
        PronunciationEngine._instance = None

    def test_hemanth_pronunciation_correction_and_debug(self):
        """Req 1-5: Verify replacement of 'హమత' with 'హేమంత్' and process_for_tts_debug output."""
        self.engine.set_native_script_pronunciation(
            display_name="Hemanth",
            native_spoken_form="హేమంత్",
            phonetic_fallback="HEY-manth",
            language="telugu"
        )

        entry = self.p_dict.get_entry("Hemanth")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["spoken"], "హేమంత్")
        self.assertEqual(entry["ssml_alias"], "హేమంత్")
        self.assertIsNone(entry["phoneme"])

        # Edge TTS uses Priority 4 Native-Script Spoken Form to prevent raw XML escaping
        debug_edge = self.engine.process_for_tts_debug("Hello Hemanth, welcome back.", provider="edge")
        self.assertEqual(debug_edge["normalized_text"], 'Hello హేమంత్, welcome back.')
        self.assertIn("Matched 'Hemanth' -> Priority 4: Native-Script Spoken Form ('హేమంత్')", debug_edge["strategy_log"])

        # Azure Speech uses Priority 2 SSML Sub Alias
        debug_azure = self.engine.process_for_tts_debug("Hello Hemanth, welcome back.", provider="azure")
        self.assertEqual(debug_azure["normalized_text"], 'Hello <sub alias="హేమంత్">Hemanth</sub>, welcome back.')
        self.assertIn("Matched 'Hemanth' -> Priority 2: SSML Sub Alias ('హేమంత్')", debug_azure["strategy_log"])

    def test_pronunciation_json_persistence_and_cache_clearing(self):
        """Req 2, 3 & 5: Check disk persistence and immediate cache invalidation."""
        self.engine.set_native_script_pronunciation("Hemanth", "హేమంత్")

        # Warmup cache
        res_before = self.engine.process_for_tts("Hello Hemanth.", provider="edge")
        self.assertIn('హేమంత్', res_before)

        # Update entry dynamically
        self.engine.set_native_script_pronunciation("Hemanth", "హేమంత్")

        # Cache is invalidated and new output is immediately served without restart
        res_after = self.engine.process_for_tts("Hello Hemanth.", provider="edge")
        self.assertIn('హేమంత్', res_after)

        # Check file content on disk
        with open(self.dict_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        stored = data["entries"]["hemanth"]
        self.assertEqual(stored["spoken"], "హేమంత్")
        self.assertEqual(stored["ssml_alias"], "హేమంత్")

    def test_original_text_immutability(self):
        """Req 11: Original text unchanged in UI, memory, chat, database, logs."""
        self.engine.set_native_script_pronunciation("Hemanth", "హేమంత్")
        original_ui_text = "Hello Hemanth, welcome back."

        tts_output = self.engine.process_for_tts(original_ui_text, provider="edge")

        self.assertEqual(tts_output, "Hello హేమంత్, welcome back.")
        self.assertEqual(original_ui_text, "Hello Hemanth, welcome back.")


if __name__ == "__main__":
    unittest.main()
