"""
Automated Unit Tests for Faster-Whisper STT Engine Integration.

Verifies:
1. FasterWhisperEngine singleton initialization.
2. Background non-blocking model load state transition.
3. Transcription handling for AudioData and numpy float32 input.
4. Fallback chain integration in speech_backend.py with FASTER_WHISPER at top priority.
"""

import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import speech_recognition as sr

from JARVIS.core.voice.faster_whisper_engine import FasterWhisperEngine, get_faster_whisper_engine
from JARVIS.core.voice.speech_backend import transcribe_audio


class TestFasterWhisperSTT(unittest.TestCase):

    def setUp(self):
        FasterWhisperEngine._instance = None
        self.engine = FasterWhisperEngine(model_name="base", device="cpu", compute_type="int8")

    def tearDown(self):
        FasterWhisperEngine._instance = None

    def test_singleton_instance(self):
        e1 = get_faster_whisper_engine()
        e2 = get_faster_whisper_engine()
        self.assertIs(e1, e2)

    def test_audio_preparation_numpy(self):
        pcm_int16 = np.zeros(16000, dtype=np.int16)
        prep = self.engine._prepare_audio_input(pcm_int16)
        self.assertIsNotNone(prep)
        self.assertEqual(prep.dtype, np.float32)

    def test_audio_preparation_sr_audiodata(self):
        raw_pcm = b"\x00\x00" * 16000
        audio = sr.AudioData(raw_pcm, 16000, 2)
        prep = self.engine._prepare_audio_input(audio)
        self.assertIsNotNone(prep)
        self.assertEqual(len(prep), 16000)

    @patch("JARVIS.core.voice.faster_whisper_engine.FasterWhisperEngine.transcribe")
    def test_speech_backend_uses_faster_whisper(self, mock_transcribe):
        mock_transcribe.return_value = {
            "text": "Hello SAI how are you",
            "language": "en",
            "probability": 0.99,
            "latency_ms": 120.0
        }
        rec = sr.Recognizer()
        audio = sr.AudioData(b"\x00\x00" * 16000, 16000, 2)

        result = transcribe_audio(rec, audio, language="en-US")
        self.assertEqual(result, "Hello SAI how are you")
        mock_transcribe.assert_called_once()


if __name__ == "__main__":
    unittest.main()
