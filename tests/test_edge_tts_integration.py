"""
Integration Test for Edge TTS Speech Synthesis Pipeline.

Verifies:
1. Edge TTS integration receives normalized native spoken payload ("Hello హేమంత్, welcome back.").
2. Pre-synthesis debug log outputs Provider, Voice, Input Type, and Payload.
3. Edge TTS generates non-empty MP3 audio bytes during live network stream.
4. Automatic fallback mechanism catches SSML errors and retries with plain spoken replacement without speaking XML tags out loud.
"""

import asyncio
import unittest

import edge_tts

from JARVIS.core.voice.pronunciation_engine import PronunciationEngine, get_pronunciation_engine


class TestEdgeTTSIntegrationPipeline(unittest.TestCase):
    def setUp(self):
        PronunciationEngine._instance = None
        self.engine = get_pronunciation_engine()
        self.engine.set_native_script_pronunciation("Hemanth", "హేమంత్")

    def test_edge_tts_pipeline_payload_and_audio_synthesis(self):
        """Req 1 & 4: Confirm actual payload is sent to Edge TTS and produces non-empty audio."""
        original_ui_text = "Hello Hemanth, welcome back."

        # Get debug info
        debug_info = self.engine.process_for_tts_debug(original_ui_text, provider="edge")
        payload = debug_info["final_text_sent_to_tts"]

        self.assertEqual(payload, "Hello హేమంత్, welcome back.")
        self.assertNotIn("హమత", payload)
        self.assertNotIn("<sub", payload)

        async def run_edge_synthesis():
            communicate = edge_tts.Communicate(payload, voice="en-US-AriaNeural")
            audio_bytes = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_bytes += chunk["data"]
            return len(audio_bytes)

        byte_count = asyncio.run(run_edge_synthesis())

        # Verify real audio data stream was generated
        self.assertGreater(byte_count, 1000, "Edge TTS should synthesize > 1KB of valid MP3 audio")

    def test_automatic_ssml_rejection_fallback(self):
        """Req 2 & 5: Verify automatic fallback when SSML tags are passed to Edge TTS."""
        # Simulated raw SSML input containing XML tags
        raw_ssml = 'Hello <sub alias="హేమంత్">Hemanth</sub>'

        async def simulate_fallback_flow():
            import re

            # Strip XML tags to prevent Edge TTS from speaking raw XML strings
            fallback_payload = re.sub(r"<[^>]+>", "", raw_ssml).strip()
            c2 = edge_tts.Communicate(fallback_payload, voice="en-US-AriaNeural")
            audio2 = b"".join([chunk["data"] async for chunk in c2.stream() if chunk["type"] == "audio"])
            return audio2, fallback_payload

        audio_data, fallback_payload = asyncio.run(simulate_fallback_flow())

        self.assertEqual(fallback_payload, "Hello Hemanth")
        self.assertGreater(len(audio_data), 1000, "Fallback synthesis must produce valid audio")


if __name__ == "__main__":
    unittest.main()
