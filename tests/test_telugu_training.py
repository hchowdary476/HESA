import unittest
import os
import json
from unittest.mock import patch

from JARVIS.core.system.utils.telugu_formatter import (
    detect_language,
    get_similarity_score,
    match_telugu_intent,
)
from JARVIS.core.automation.local_intent_router import route_local_intent
from JARVIS.core.automation.komutlar import process_command
from JARVIS.core.memory.memory_preferences import get_preference, set_preference

class TeluguNativeTrainingSystemTests(unittest.TestCase):
    def setUp(self):
        # Reset preferences
        set_preference("preferred_language", "telugu")
        set_preference("learning_command", None)
        set_preference("learned_commands", {})
        set_preference("last_telugu_context", None)

    def test_database_files_exist_and_counts(self):
        """Verify the 11 knowledge base JSON files exist and have correct record volumes."""
        kb_dir = os.path.join("knowledge", "telugu")
        
        required_files = [
            "greetings.json", "daily_conversations.json", "commands.json",
            "questions.json", "responses.json", "technology.json",
            "education.json", "system_commands.json", "synonyms.json",
            "dialects.json", "learning_memory.json"
        ]
        
        for name in required_files:
            file_path = os.path.join(kb_dir, name)
            self.assertTrue(os.path.exists(file_path), f"{name} does not exist in {kb_dir}")
            
        # Verify specific counts
        with open(os.path.join(kb_dir, "synonyms.json"), "r", encoding="utf-8") as f:
            synonyms = json.load(f)
            self.assertGreaterEqual(len(synonyms), 1000, "Synonyms count should be >= 1000")
            
        with open(os.path.join(kb_dir, "commands.json"), "r", encoding="utf-8") as f:
            commands = json.load(f)
            self.assertGreaterEqual(len(commands), 2000, "Commands count should be >= 2000")
            
        with open(os.path.join(kb_dir, "daily_conversations.json"), "r", encoding="utf-8") as f:
            daily = json.load(f)
            self.assertGreaterEqual(len(daily), 5000, "Daily conversations count should be >= 5000")
            
        with open(os.path.join(kb_dir, "technology.json"), "r", encoding="utf-8") as f:
            tech = json.load(f)
            self.assertGreaterEqual(len(tech), 500, "Technology questions count should be >= 500")
            
        with open(os.path.join(kb_dir, "education.json"), "r", encoding="utf-8") as f:
            edu = json.load(f)
            self.assertGreaterEqual(len(edu), 500, "Education questions count should be >= 500")

        total_phrases = len(synonyms) + len(commands) + len(daily) + len(tech) + len(edu)
        self.assertGreaterEqual(total_phrases, 10000, "Total phrases across concepts should be >= 10000")

    def test_fuzzy_matching_similarity(self):
        """Verify the Jaccard similarity scoring function works correctly."""
        self.assertAlmostEqual(get_similarity_score("time entha", "time entha"), 1.0)
        self.assertEqual(get_similarity_score("open chrome", "close whatsapp"), 0.0)
        
        # Test close spelling/transliteration variations
        score1 = get_similarity_score("time entha", "time yenti")
        self.assertGreaterEqual(score1, 0.3)
        
        # Subphrase similarity check
        score2 = get_similarity_score("chrome open cheyyi", "open chrome")
        self.assertGreater(score2, 0.5)

    def test_fuzzy_matching_intent_routing(self):
        """Verify that fuzzy Telugu intents match correctly and return the expected payloads."""
        # Test a direct matching command in Telugu Knowledge Base
        res = match_telugu_intent("naa battery entha undi")
        self.assertIsNotNone(res)
        self.assertEqual(res["intent"], "system_query")
        self.assertEqual(res["target"], "get_battery")
        self.assertGreaterEqual(res["confidence"], 0.6)

        # Test slightly fuzzy variation of a daily conversation question
        res_convo = match_telugu_intent("bagunnava sir yenti")
        self.assertIsNotNone(res_convo)
        self.assertEqual(res_convo["intent"], "talk")
        self.assertIn("systems normal", res_convo["target"])

    def test_context_memory_routing(self):
        """Verify context-aware routing for short/ambiguous queries like 'enti' or 'cheppu'."""
        # Set context to battery
        set_preference("last_telugu_context", "battery")
        res_batt = match_telugu_intent("enti")
        self.assertIsNotNone(res_batt)
        self.assertEqual(res_batt["intent"], "system_query")
        self.assertEqual(res_batt["target"], "battery status")
        
        # Set context to time
        set_preference("last_telugu_context", "time")
        res_time = match_telugu_intent("cheppu")
        self.assertIsNotNone(res_time)
        self.assertEqual(res_time["intent"], "system_query")
        self.assertEqual(res_time["target"], "what time")

    def test_owner_phrase_learning_and_fuzzy_learned(self):
        """Verify learned owner phrases are persisted and matched fuzzily."""
        # 1. Simulate learning flow
        set_preference("learning_command", "Jarvis Jio cinema open cheyyi")
        
        with patch("JARVIS.core.automation.komutlar.speak") as speak_mock:
            result = process_command("open jiocinema.com")
            self.assertTrue(result)
            speak_mock.assert_called_with("Sir, ee command ni future kosam gurthupettukunnanu.")
            
        # Verify it was saved to the learning_memory.json file
        learned_path = os.path.join("knowledge", "telugu", "learning_memory.json")
        self.assertTrue(os.path.exists(learned_path))
        with open(learned_path, "r", encoding="utf-8") as f:
            learned_db = json.load(f)
            self.assertIn("Jarvis Jio cinema open cheyyi", learned_db)
            self.assertEqual(learned_db["Jarvis Jio cinema open cheyyi"], "open jiocinema.com")
            
        # 2. Test exact match routing
        with patch("JARVIS.core.automation.komutlar.speak") as speak_mock:
            with patch("JARVIS.core.automation.domains.runtime_actions.webbrowser.open") as open_mock:
                result_run = process_command("Jarvis Jio cinema open cheyyi")
                self.assertTrue(result_run)
                open_mock.assert_called_with("https://jiocinema.com")
                
        # 3. Test fuzzy match routing
        with patch("JARVIS.core.automation.komutlar.speak") as speak_mock:
            with patch("JARVIS.core.automation.domains.runtime_actions.webbrowser.open") as open_mock:
                result_run_fuzzy = process_command("Jio cinema open chey")
                self.assertTrue(result_run_fuzzy)
                open_mock.assert_called_with("https://jiocinema.com")

if __name__ == "__main__":
    unittest.main()
