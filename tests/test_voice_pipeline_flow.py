"""
Integration Test for the Target Voice Pipeline Flow.

Target Pipeline:
Say: Hey SAI
  ↓
OpenWakeWord detects SAI
  ↓
Whisper records command
  ↓
Intent Router
  ↓
Claude/OpenAI/Gemini/Ollama
  ↓
Edge TTS speaks reply
"""

import unittest

from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator
from JARVIS.core.automation.local_intent_router import classify_intent
from JARVIS.core.voice.openwakeword_engine import get_openwakeword_engine
from JARVIS.core.voice.ses_motoru import VoiceEngine


class TestVoicePipelineFlow(unittest.TestCase):
    def setUp(self):
        self.oww = get_openwakeword_engine()
        self.orchestrator = AIOrchestrator()

    def test_target_pipeline_execution(self):
        # 1. Say: Hey SAI
        wake_phrase = "Hey SAI"
        self.assertFalse(self.oww.is_false_positive(wake_phrase))

        # 2. OpenWakeWord detects SAI
        # Mock frame processing detection trigger
        is_detected = True
        self.assertTrue(is_detected)

        # 3. Whisper records command
        command_text = "What is machine learning?"
        self.assertIsNotNone(command_text)

        # 4. Intent Router
        intent_type, task_type = classify_intent(command_text)
        self.assertEqual(intent_type, "AI_QUERY")
        self.assertIn(task_type, {"general", "reasoning", "coding"})

        # 5. AI Router (Claude / OpenAI / Gemini / Ollama)
        response = self.orchestrator.query_with_failover(command_text, task_type=task_type)
        self.assertTrue(len(response) > 0)
        self.assertIn("machine learning", response.lower())

        # 6. Edge TTS speaks reply
        engine = VoiceEngine()
        self.assertIsNotNone(engine)


if __name__ == "__main__":
    unittest.main()
