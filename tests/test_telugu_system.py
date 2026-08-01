import unittest
from unittest.mock import patch

from JARVIS.core.system.utils.telugu_formatter import (
    detect_language,
    normalize_telugu_command,
    format_telugu_response,
    contains_telugu_script,
    translate_to_telugu_script,
)
from JARVIS.core.automation.local_intent_router import route_local_intent
from JARVIS.core.automation.komutlar import process_command
from JARVIS.core.memory.memory_preferences import get_preference, set_preference

class TeluguNativeConversationSystemTests(unittest.TestCase):
    def setUp(self):
        # Reset preferences
        set_preference("preferred_language", "english")
        set_preference("learning_command", None)
        set_preference("learned_commands", {})

    def test_contains_telugu_script(self):
        self.assertTrue(contains_telugu_script("సమయం ఎంత"))
        self.assertFalse(contains_telugu_script("time entha"))

    def test_language_detection(self):
        self.assertEqual(detect_language("Jarvis time entha?"), "telugu")
        self.assertEqual(detect_language("Jarvis YouTube open cheyyi"), "telugu")
        self.assertEqual(detect_language("Jarvis naa battery entha undi?"), "telugu")
        self.assertEqual(detect_language("Bagunnava?"), "telugu")
        self.assertEqual(detect_language("Em chestunnav?"), "telugu")
        self.assertEqual(detect_language("thanks"), "english")
        self.assertEqual(detect_language("open chrome"), "english")

    def test_command_normalization(self):
        self.assertEqual(normalize_telugu_command("Chrome open cheyyi"), "open chrome")
        self.assertEqual(normalize_telugu_command("VS Code start cheyyi"), "open vs code")
        self.assertEqual(normalize_telugu_command("YouTube open cheyyi"), "open youtube")
        self.assertEqual(normalize_telugu_command("Jarvis time entha?"), "what time")
        self.assertEqual(normalize_telugu_command("Jarvis naa battery entha undi?"), "battery status")
        self.assertEqual(normalize_telugu_command("Em chestunnav?"), "what are you doing")
        self.assertEqual(normalize_telugu_command("Bagunnava?"), "how are you")

    def test_telugu_script_translation(self):
        self.assertIn("సార్", translate_to_telugu_script("sir"))
        self.assertIn("సమయం", translate_to_telugu_script("samayam"))

    def test_response_formatting(self):
        set_preference("preferred_language", "telugu")
        formatted = format_telugu_response("Opening YouTube, sir.", "Jarvis YouTube open cheyyi")
        self.assertEqual(formatted, "Sare sir, YouTube open chestunnanu.")
        
        # Script matching
        formatted_script = format_telugu_response("Opening YouTube, sir.", "జార్విస్ యూట్యూబ్ ఓపెన్ చేయి")
        self.assertEqual(formatted_script, "సరే సార్, YouTube ఓపెన్ చేస్తున్నాను.")

    def test_conversational_routes(self):
        set_preference("preferred_language", "telugu")
        
        # Em chestunnav
        payload = route_local_intent("Em chestunnav")
        self.assertEqual(payload["action"], "talk")
        self.assertEqual(payload["response"], "Mee commands kosam ready ga unnanu sir.")
        
        # Bagunnava
        payload = route_local_intent("Bagunnava")
        self.assertEqual(payload["action"], "talk")
        self.assertEqual(payload["response"], "Avunu sir, anni systems normal ga pani chestunnayi.")

        # Thanks
        payload = route_local_intent("Thanks")
        self.assertEqual(payload["action"], "talk")
        self.assertEqual(payload["response"], "Welcome sir.")

    def test_learning_system(self):
        # Learn mapping
        set_preference("preferred_language", "telugu")
        set_preference("learning_command", "Jarvis Jio page open cheyyi")
        
        with patch("JARVIS.core.automation.komutlar.speak") as speak_mock:
            result = process_command("open jio.com")
            self.assertTrue(result)
            speak_mock.assert_called_with("Sir, ee command ni future kosam gurthupettukunnanu.")
            
        # Verify learned mapping works
        learned = get_preference("learned_commands")
        self.assertIn("Jarvis Jio page open cheyyi", learned)
        self.assertEqual(learned["Jarvis Jio page open cheyyi"], "open jio.com")
        
        with patch("JARVIS.core.automation.komutlar.speak") as speak_mock:
            # We mock webbrowser open to avoid opening actual browser window during test
            with patch("JARVIS.core.automation.domains.runtime_actions.webbrowser.open") as open_mock:
                result = process_command("Jarvis Jio page open cheyyi")
                self.assertTrue(result)
                open_mock.assert_called_with("https://jio.com")

    def test_startup_greeting(self):
        from JARVIS.gui.main_window import STARTUP_GREETING
        self.assertEqual(STARTUP_GREETING, "Namaskaram sir. HESA siddhanga undi. Mee commands kosam ready ga unnanu sir.")
        
        # Test formatting mapping for startup greeting phrases
        set_preference("preferred_language", "telugu")
        res1 = format_telugu_response("systems are ready")
        self.assertEqual(res1, "Namaskaram sir. HESA siddhanga undi. Mee commands kosam ready ga unnanu sir.")

    def test_mode_switcher_commands(self):
        with patch("JARVIS.core.automation.komutlar.speak") as speak_mock:
            result = process_command("Telugu mode")
            self.assertTrue(result)
            speak_mock.assert_called_with("Telugu mode enabled sir.")
            self.assertEqual(get_preference("language_mode"), "telugu")
            self.assertEqual(get_preference("preferred_language"), "telugu")

        with patch("JARVIS.core.automation.komutlar.speak") as speak_mock:
            result = process_command("English mode")
            self.assertTrue(result)
            speak_mock.assert_called_with("English mode enabled sir.")
            self.assertEqual(get_preference("language_mode"), "english")
            self.assertEqual(get_preference("preferred_language"), "english")

        with patch("JARVIS.core.automation.komutlar.speak") as speak_mock:
            result = process_command("Auto language mode")
            self.assertTrue(result)
            speak_mock.assert_called_with("Automatic language detection enabled sir.")
            self.assertEqual(get_preference("language_mode"), "auto")

    def test_enforced_language_mode_persistence(self):
        # Set language_mode to telugu. Any command run shouldn't change language_mode or preferred_language permanently to english even if user types English command
        set_preference("language_mode", "telugu")
        set_preference("preferred_language", "telugu")
        
        with patch("JARVIS.core.automation.komutlar.route_local_intent", return_value={"action": "talk", "response": "Hello"}):
            with patch("JARVIS.core.automation.komutlar.speak") as speak_mock:
                process_command("open chrome")
                self.assertEqual(get_preference("language_mode"), "telugu")
                self.assertEqual(get_preference("preferred_language"), "telugu")
                
        # Now check "auto" mode: typing English command should switch preferred_language to english
        set_preference("language_mode", "auto")
        set_preference("preferred_language", "telugu")
        with patch("JARVIS.core.automation.komutlar.route_local_intent", return_value={"action": "talk", "response": "Hello"}):
            with patch("JARVIS.core.automation.komutlar.speak") as speak_mock:
                process_command("open chrome")
                self.assertEqual(get_preference("language_mode"), "auto")
                self.assertEqual(get_preference("preferred_language"), "english")

    def test_pure_english_command_translation_bypass(self):
        # Preferred language is telugu
        set_preference("preferred_language", "telugu")
        
        # When user types in English, response translation should be bypassed
        response = format_telugu_response("Opening YouTube, sir.", "open youtube")
        self.assertEqual(response, "Opening YouTube, sir.")
        
        # When user types in Telugu, response should be formatted to Telugu
        response_telugu = format_telugu_response("Opening YouTube, sir.", "YouTube open cheyyi")
        self.assertEqual(response_telugu, "Sare sir, YouTube open chestunnanu.")

    def test_voice_routing_rules(self):
        import asyncio
        from JARVIS.core.voice.ses_motoru import _speak_async
        with patch("edge_tts.Communicate") as mock_comm:
            mock_instance = mock_comm.return_value
            async def mock_stream():
                yield {"type": "audio", "data": b"fake-audio"}
            mock_instance.stream = mock_stream
            
            with patch("JARVIS.core.voice.ses_motoru.tempfile.mkstemp", return_value=(999, "fake.mp3")):
                with patch("JARVIS.core.voice.ses_motoru.os.fdopen") as mock_fdopen:
                    with patch("JARVIS.core.voice.ses_motoru.asyncio.to_thread") as mock_to_thread:
                        with patch("JARVIS.core.voice.ses_motoru.os.remove") as mock_remove:
                            asyncio.run(_speak_async("సమయం ఎంత"))
                            mock_comm.assert_called_with("సమయం ఎంత", voice="te-IN-MohanNeural", rate="-8%", pitch="-12Hz")
                            
                            mock_comm.reset_mock()
                            asyncio.run(_speak_async("Hello, how are you?"))
                            mock_comm.assert_called_with("Hello, how are you?", voice="en-US-AriaNeural", rate="-8%", pitch="-12Hz")

    def test_no_false_positive_intercept(self):
        from JARVIS.runtime.self_healing import SelfHealingEngine, HIGH
        
        # Instantiate the singleton and set pending_repairs directly
        engine = SelfHealingEngine()
        engine.pending_repairs = {
            "some_issue": {
                "id": "some_issue",
                "name": "Some issue",
                "risk": HIGH,
                "action": "Some action"
            }
        }
        
        with patch("JARVIS.core.automation.komutlar.speak") as speak_mock:
            # We mock route_local_intent to return a valid dummy action so we don't depend on LLM/Groq router
            with patch("JARVIS.core.automation.komutlar.route_local_intent", return_value={"action": "talk", "response": "Hello"}):
                result = process_command("whats app lo 6304483871 ee no ki hi anni message pettu")
                # It should not speak "Repair declined, sir."
                for call in speak_mock.call_args_list:
                    self.assertNotEqual(call[0][0], "Repair declined, sir.")

if __name__ == "__main__":
    unittest.main()
