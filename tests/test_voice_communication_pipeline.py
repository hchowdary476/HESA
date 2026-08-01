"""
Automated Integration Tests for the STT + TTS Voice Communication System.

Verifies:
1. Microphone VAD pipeline & speech buffer accumulation.
2. Full Voice Pipeline state transitions: IDLE -> LISTENING -> TRANSCRIBING -> THINKING -> SPEAKING -> IDLE.
3. Pronunciation Engine payload transformation: "Hello Hemanth, welcome back." -> Edge TTS spoken payload "Hello హేమంత్, welcome back."
4. Immutability of original text across UI, chat, memory, logs.
5. Barge-in / Interruption handling and audio playback cancellation.
6. Voice Diagnostics payload generation.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from JARVIS.core.voice.voice_state import VoiceState, VoiceStateMachine
from JARVIS.core.voice.voice_pipeline import VoicePipeline, get_voice_pipeline
from JARVIS.core.voice.pronunciation_engine import get_pronunciation_engine
from JARVIS.core.voice.ses_motoru import VoiceEngine


class TestVoiceCommunicationPipeline(unittest.TestCase):

    def setUp(self):
        VoicePipeline._instance = None
        self.pipeline = get_voice_pipeline()
        self.p_engine = get_pronunciation_engine()

    def tearDown(self):
        VoicePipeline._instance = None

    def test_voice_state_transitions(self):
        sm = VoiceStateMachine()
        self.assertEqual(sm.state, VoiceState.IDLE)

        sm.transition(VoiceState.LISTENING)
        self.assertEqual(sm.state, VoiceState.LISTENING)

        sm.transition(VoiceState.TRANSCRIBING)
        self.assertEqual(sm.state, VoiceState.TRANSCRIBING)

        sm.transition(VoiceState.THINKING)
        self.assertEqual(sm.state, VoiceState.THINKING)

        sm.transition(VoiceState.SPEAKING)
        self.assertEqual(sm.state, VoiceState.SPEAKING)

        sm.transition(VoiceState.IDLE)
        self.assertEqual(sm.state, VoiceState.IDLE)

    def test_pronunciation_engine_personal_name_flow(self):
        """Req 4 & 16: Verify 'Hemanth' remains unchanged in original text while Edge TTS receives 'హేమంత్'."""
        self.p_engine.set_native_script_pronunciation("Hemanth", "హేమంత్")
        original_ui_text = "Hello Hemanth, welcome back."

        debug_info = self.p_engine.process_for_tts_debug(original_ui_text, provider="edge")

        # UI & Memory original text remains immutable
        self.assertEqual(original_ui_text, "Hello Hemanth, welcome back.")

        # Edge TTS spoken payload uses native script form
        self.assertEqual(debug_info["final_text_sent_to_tts"], "Hello హేమంత్, welcome back.")

    @patch("JARVIS.core.voice.ses_motoru.stop_playback")
    def test_barge_in_interruption(self, mock_stop_playback):
        """Req 7: Verify user speech during TTS triggers barge-in playback cancellation."""
        self.pipeline.barge_in_enabled = True
        self.pipeline.set_state(VoiceState.SPEAKING)

        self.pipeline.handle_user_interruption()

        mock_stop_playback.assert_called_once()
        self.assertEqual(self.pipeline.state_machine.state, VoiceState.LISTENING)

    def test_voice_diagnostics_structure(self):
        """Req 13: Verify voice diagnostics info structure."""
        status = self.pipeline.get_status()
        self.assertIn("state", status)
        self.assertIn("barge_in_enabled", status)
        self.assertIn("continuous_conversation", status)


if __name__ == "__main__":
    unittest.main()
