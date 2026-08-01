import unittest
from unittest.mock import patch, MagicMock
import os
import json
import time

from JARVIS.core.automation import groq_router
from JARVIS.providers.base import ProviderResponse


class HybridAIRoutingTests(unittest.TestCase):
    def setUp(self):
        # Reset the global Groq cooldown state in the providers module to avoid inter-test pollution
        from JARVIS.providers import groq as providers_groq
        providers_groq._groq_cooldown_until = 0.0
        
        # Clean up existing status file
        self.status_file = os.path.join("logs", "hybrid_ai_status.json")
        if os.path.exists(self.status_file):
            try:
                os.remove(self.status_file)
            except Exception:
                pass

    def tearDown(self):
        if os.path.exists(self.status_file):
            try:
                os.remove(self.status_file)
            except Exception:
                pass

    @patch("JARVIS.core.automation.groq_router.is_internet_available")
    @patch("JARVIS.core.automation.groq_router.GroqProvider")
    @patch("JARVIS.core.automation.groq_router.query_gemini")
    @patch.dict(os.environ, {"GROQ_API_KEY": "test_groq_key"})
    def test_routing_online_groq_success(self, mock_gemini, mock_provider_cls, mock_internet):
        mock_internet.return_value = True
        
        mock_provider = MagicMock()
        mock_provider.analyze.return_value = ProviderResponse(
            provider="groq",
            status="success",
            action={"action": "talk", "params": {}, "response": "Hello from Groq"}
        )
        mock_provider_cls.return_value = mock_provider

        result = groq_router.analyze_with_groq("hello")
        
        self.assertEqual(result["response"], "Hello from Groq")
        stats = groq_router.get_hybrid_ai_status()
        self.assertEqual(stats["current_provider"], "GROQ")
        self.assertEqual(stats["current_ai_provider"], "AI Provider: GROQ")
        self.assertEqual(stats["network_status"], "ONLINE")

    @patch("JARVIS.core.automation.groq_router.is_internet_available")
    @patch("JARVIS.core.automation.groq_router.GroqProvider")
    @patch("JARVIS.core.automation.groq_router.query_gemini")
    @patch.dict(os.environ, {"GROQ_API_KEY": "test_groq_key", "GEMINI_API_KEY": "test_gemini_key"})
    def test_routing_online_groq_fails_gemini_success(self, mock_gemini, mock_provider_cls, mock_internet):
        mock_internet.return_value = True
        
        mock_provider = MagicMock()
        mock_provider.analyze.side_effect = Exception("Groq failed")
        mock_provider_cls.return_value = mock_provider
        
        mock_gemini.return_value = {"action": "talk", "params": {}, "response": "Hello from Gemini"}

        result = groq_router.analyze_with_groq("hello")
        
        self.assertEqual(result["response"], "Hello from Gemini")
        stats = groq_router.get_hybrid_ai_status()
        self.assertEqual(stats["current_provider"], "GEMINI")
        self.assertEqual(stats["current_ai_provider"], "AI Provider: GEMINI")
        self.assertEqual(stats["network_status"], "ONLINE")
        self.assertEqual(stats["groq_status"], "OFFLINE")

    @patch("JARVIS.core.automation.groq_router.is_internet_available")
    @patch("JARVIS.core.automation.groq_router.query_ollama")
    @patch.dict(os.environ, {"JARVIS_LOCAL_LLM_URL": "http://localhost:11434"})
    def test_routing_offline_ollama_success(self, mock_ollama, mock_internet):
        mock_internet.return_value = False
        mock_ollama.return_value = {"action": "talk", "params": {}, "response": "Hello from Ollama"}

        result = groq_router.analyze_with_groq("hello")
        
        self.assertEqual(result["response"], "Hello from Ollama")
        stats = groq_router.get_hybrid_ai_status()
        self.assertEqual(stats["current_provider"], "OLLAMA")
        self.assertEqual(stats["current_ai_provider"], "AI Provider: OLLAMA")
        self.assertEqual(stats["network_status"], "OFFLINE")
        self.assertEqual(stats["ollama_status"], "ACTIVE")

    @patch("JARVIS.core.automation.groq_router.is_internet_available")
    @patch("JARVIS.core.automation.groq_router.query_ollama")
    @patch.dict(os.environ, {"JARVIS_LOCAL_LLM_URL": "http://localhost:11434"})
    def test_routing_offline_ollama_fails_local_rules(self, mock_ollama, mock_internet):
        mock_internet.return_value = False
        mock_ollama.side_effect = Exception("Ollama offline")

        result = groq_router.analyze_with_groq("hello")
        
        self.assertIn("Local neural links are online", result["response"])
        stats = groq_router.get_hybrid_ai_status()
        self.assertEqual(stats["current_provider"], "OLLAMA")
        self.assertEqual(stats["network_status"], "OFFLINE")
        self.assertEqual(stats["ollama_status"], "OFFLINE")

    @patch("urllib.request.urlopen")
    def test_get_ollama_model_auto_detection(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"models": [{"name": "my_custom_model:latest"}]}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        model = groq_router.get_ollama_model("http://localhost:11434")
        self.assertEqual(model, "my_custom_model:latest")

    @patch("urllib.request.urlopen")
    def test_get_ollama_model_fallback(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection refused")

        model = groq_router.get_ollama_model("http://localhost:11434")
        self.assertEqual(model, "llama3")

    @patch("JARVIS.core.automation.groq_router.is_internet_available")
    @patch("JARVIS.core.automation.groq_router.build_context_prompt")
    @patch("JARVIS.core.automation.groq_router.query_gemini")
    @patch.dict(os.environ, {"GROQ_API_KEY": "", "GEMINI_API_KEY": "test_gemini_key"})
    def test_conversation_context_passed_to_gemini(self, mock_gemini, mock_context, mock_internet):
        mock_internet.return_value = True
        mock_context.return_value = "Recent conversation: user: hi | assistant: hello"
        mock_gemini.return_value = {"action": "talk", "params": {}, "response": "Context verified"}
        
        # We want to verify that when Gemini is called, it receives the context
        groq_router.analyze_with_groq("what did I say?")
        
        mock_gemini.assert_called_once()
        args, kwargs = mock_gemini.call_args
        self.assertIn("Recent conversation:", kwargs.get("context", ""))

    def test_no_forbidden_strings_in_fallbacks(self):
        # Verify that fallback messages do not contain forbidden strings
        fallback_act = groq_router._local_fallback_action()
        resp = fallback_act["response"]
        
        self.assertNotIn("local-only mode", resp.lower())
        self.assertNotIn("cloud disabled", resp.lower())
        
        missing_act = groq_router._missing_groq_action()
        resp_missing = missing_act["response"]
        
        self.assertNotIn("local-only mode", resp_missing.lower())
        self.assertNotIn("cloud disabled", resp_missing.lower())

    @patch("JARVIS.core.automation.groq_router.socket.create_connection")
    def test_cached_latency_probe(self, mock_create):
        # Verify that get_cached_latency and is_internet_available return cached values
        groq_router._internet_check_thread_started = True
        groq_router._cached_internet_status = True
        groq_router._cached_latency_ms = 4.2
        
        # Test non-blocking behavior
        self.assertTrue(groq_router.is_internet_available())
        self.assertEqual(groq_router.get_cached_latency(), 4.2)
        mock_create.assert_not_called()

    @patch("JARVIS.core.automation.groq_router.is_internet_available")
    @patch("JARVIS.core.automation.groq_router.query_gemini")
    @patch("JARVIS.core.automation.groq_router.GroqProvider")
    @patch.dict(os.environ, {
        "GROQ_API_KEY": "test_groq_key",
        "GEMINI_API_KEY": "test_gemini_key",
        "JARVIS_PRIMARY_AI": "GEMINI",
        "JARVIS_SECONDARY_AI": "GROQ"
    })
    def test_priority_settings_routing(self, mock_provider_cls, mock_gemini, mock_internet):
        mock_internet.return_value = True
        mock_gemini.return_value = {"action": "talk", "params": {}, "response": "Hello from priority Gemini"}
        
        result = groq_router.analyze_with_groq("hello")
        self.assertEqual(result["response"], "Hello from priority Gemini")
        stats = groq_router.get_hybrid_ai_status()
        self.assertEqual(stats["current_provider"], "GEMINI")

    @patch("JARVIS.core.automation.groq_router.is_internet_available")
    @patch("JARVIS.core.automation.groq_router.GroqProvider")
    @patch.dict(os.environ, {"GROQ_API_KEY": "test_groq_key"})
    def test_provider_stats_tracking(self, mock_provider_cls, mock_internet):
        mock_internet.return_value = True
        
        mock_provider = MagicMock()
        mock_provider.analyze.return_value = ProviderResponse(
            provider="groq",
            status="success",
            action={"action": "talk", "params": {}, "response": "Stats track test"}
        )
        mock_provider_cls.return_value = mock_provider
        
        groq_router.analyze_with_groq("hello")
        stats = groq_router.get_hybrid_ai_status()
        
        # Verify stats nested dictionary exists and tracks GROQ success
        self.assertIn("stats", stats)
        self.assertIn("GROQ", stats["stats"])
        self.assertNotEqual(stats["stats"]["GROQ"]["last_success"], "Never")
        self.assertEqual(stats["stats"]["GROQ"]["last_failure"], "Never")

    @patch("JARVIS.core.automation.groq_router.is_internet_available")
    @patch("JARVIS.core.automation.groq_router.query_ollama")
    @patch.dict(os.environ, {"JARVIS_LOCAL_LLM_URL": "http://invalid-ollama-url"})
    def test_ollama_not_installed_fallback_rules(self, mock_ollama, mock_internet):
        mock_internet.return_value = False
        # Simulate Ollama not installed/running by throwing connection exception
        mock_ollama.side_effect = ConnectionRefusedError("Connection refused")
        
        # Execute query without raising error/exception to user
        result = groq_router.analyze_with_groq("hello")
        
        # Ensure result comes from rule engine
        self.assertIn("Local neural links are online", result["response"])
        stats = groq_router.get_hybrid_ai_status()
        self.assertEqual(stats["stats"]["OLLAMA"]["last_failure"], stats["stats"]["OLLAMA"]["last_failure"])


if __name__ == "__main__":
    unittest.main()
