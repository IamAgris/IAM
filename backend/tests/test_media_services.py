"""Unit tests for voice VAD, TTS fallback and ffmpeg frame extraction."""

import array
import asyncio
import math
import unittest
from unittest.mock import patch

from app.core.config import settings
from app.services.voice_service import VoiceService
from app.services.vision_service import VisionService


class VoiceTests(unittest.TestCase):
    def setUp(self):
        self.service = VoiceService()

    def test_silence_has_no_voice(self):
        samples = array.array("h", [0] * 3200)
        result = asyncio.run(self.service.detect_voice_activity(samples.tobytes()))
        self.assertFalse(result["has_voice"])
        self.assertEqual(result["method"], "pcm_energy")

    def test_tone_has_voice(self):
        samples = array.array(
            "h", [int(12000 * math.sin(i / 8)) for i in range(3200)]
        )
        result = asyncio.run(self.service.detect_voice_activity(samples.tobytes()))
        self.assertTrue(result["has_voice"])
        self.assertGreater(result["confidence"], 0.2)

    def test_tts_without_provider_is_explicit(self):
        with (
            patch.object(settings, "voice_tts_url", ""),
            patch.object(self.service, "tts_provider", "local"),
            patch.object(self.service, "tts_api_key", None),
        ):
            result = asyncio.run(self.service.text_to_speech("hello"))
        self.assertEqual(result["audio_base64"], "")
        self.assertIn("No TTS provider configured", result["note"])


class VisionTests(unittest.TestCase):
    def test_missing_ffmpeg_returns_no_frames(self):
        service = VisionService()
        with patch.object(settings, "vision_ffmpeg_path", "definitely-missing-ffmpeg"):
            frames = asyncio.run(service.sample_video_frames(b"not a real video", 4))
        self.assertEqual(frames, [])


if __name__ == "__main__":
    unittest.main()
