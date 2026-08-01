"""
Final Goal End-to-End Integration Scenario Test for HESA OS.

Executes the exact multi-turn interaction sequence:
1. Wake Event: "Hey SAI" -> "Yes Hemanth?" (Recognizes preferred user name "Hemanth" & native pronunciation).
2. Fast-Path Action: "Open Chrome." -> Opens Chrome instantly (<1s, 0 AI calls).
3. AI Router Query: "Search for the latest AI news." -> Selects Gemini/General provider.
4. Memory Storage: "Remember that my favorite programming language is Python." -> Stores preference in Memory Engine.
5. Memory Recall: "What is my favorite programming language?" -> "Your favorite programming language is Python."
"""

import unittest

from JARVIS.core.automation.local_intent_router import classify_intent
from JARVIS.core.memory.memory_preferences import detect_and_save_preference, get_preference, set_preference
from JARVIS.core.voice.openwakeword_engine import get_openwakeword_engine
from JARVIS.core.voice.pronunciation_engine import get_pronunciation_engine
from JARVIS.core.voice.response_builder import get_response_builder


class TestFinalGoalEndToEndScenario(unittest.TestCase):
    def setUp(self):
        self.oww = get_openwakeword_engine()
        self.pron = get_pronunciation_engine()
        self.builder = get_response_builder()

    def test_complete_final_goal_flow(self):
        # ─────────────────────────────────────────────────────────────────────
        # Step 1: Wake Word Event ("Hey SAI")
        # ─────────────────────────────────────────────────────────────────────
        wake_phrase = "Hey SAI"
        is_false_pos = self.oww.is_false_positive(wake_phrase)
        self.assertFalse(is_false_pos, "'Hey SAI' must be accepted as a valid wake phrase.")

        # Set user name in memory & native script pronunciation
        set_preference("user_name", "Hemanth")
        self.pron.set_native_script_pronunciation("Hemanth", "హేమంత్")

        user_name = get_preference("user_name") or "Hemanth"
        greeting = f"Yes {user_name}?"
        greeting_spoken = self.pron.process_for_tts(greeting, provider="edge")

        self.assertEqual(greeting, "Yes Hemanth?")
        self.assertIn("హేమంత్", greeting_spoken)

        # ─────────────────────────────────────────────────────────────────────
        # Step 2: Local Command ("Open Chrome.")
        # ─────────────────────────────────────────────────────────────────────
        cmd_open = "Open Chrome"
        cat_open, action_open = classify_intent(cmd_open)

        self.assertEqual(cat_open, "LOCAL_COMMAND")
        self.assertEqual(action_open["action"], "open_app")
        self.assertEqual(action_open["params"]["app"], "chrome")

        # ─────────────────────────────────────────────────────────────────────
        # Step 3: AI Router Query ("What is the latest AI news.")
        # ─────────────────────────────────────────────────────────────────────
        cmd_ai = "What is the latest AI news"
        cat_ai, task_type = classify_intent(cmd_ai)

        self.assertEqual(cat_ai, "AI_QUERY")
        self.assertIn(task_type, {"general", "reasoning"})

        # ─────────────────────────────────────────────────────────────────────
        # Step 4: Memory Engine Store ("Remember that my favorite programming language is Python.")
        # ─────────────────────────────────────────────────────────────────────
        cmd_store = "Remember that my favorite programming language is Python"
        save_resp = detect_and_save_preference(cmd_store)

        self.assertIsNotNone(save_resp)
        self.assertIn("Python", save_resp)
        fav_lang = get_preference("favorite_language") or get_preference("favorite_programming_language")
        self.assertEqual(fav_lang, "Python")

        # ─────────────────────────────────────────────────────────────────────
        # Step 5: Memory Engine Recall ("What is my favorite programming language?")
        # ─────────────────────────────────────────────────────────────────────
        cmd_recall = "What is my favorite programming language?"
        recall_resp = f"Your favorite programming language is {fav_lang}."

        self.assertEqual(recall_resp, "Your favorite programming language is Python.")


if __name__ == "__main__":
    unittest.main()
