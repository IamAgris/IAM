"""Voice service - speech-to-text and text-to-speech (pluggable providers)"""

import httpx
import loguru
import base64
import io
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.core.config import settings

logger = loguru.logger


class VoiceService:
    """
    Voice communication service supporting pluggable STT and TTS providers.
    
    Voice configuration is associated with the AI's identity.
    Audio storage only where retention is permitted.
    """

    def __init__(self):
        # STT provider: 'whisper', 'azure', 'google', 'local'
        self.stt_provider = "whisper"
        self.stt_api_key = settings.openai_api_key  # Whisper via OpenAI-compatible

        # TTS provider: 'elevenlabs', 'azure', 'google', 'local'
        self.tts_provider = "local"
        self.tts_api_key = None
        self.tts_voice_id = "aura-default"
        self.tts_sample_rate = 22050

    # -------------------------------------------------------------------------
    # Speech-to-Text
    # -------------------------------------------------------------------------

    async def speech_to_text(
        self,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convert speech audio to text.
        
        Returns: { text, language, confidence, duration_ms, provider }
        """
        if self.stt_provider == "whisper" and self.stt_api_key:
            return await self._stt_whisper(audio_bytes, content_type, language)
        else:
            return {
                "text": "",
                "language": language or "en",
                "confidence": 0.0,
                "duration_ms": 0,
                "provider": "none",
                "error": "No STT provider configured",
            }

    async def _stt_whisper(
        self, audio_bytes: bytes, content_type: str, language: Optional[str]
    ) -> Dict[str, Any]:
        """Whisper STT via OpenAI-compatible API (or LiteLLM)."""
        try:
            async with httpx.AsyncClient() as client:
                files = {
                    "file": ("audio.wav", audio_bytes, content_type),
                }
                data = {
                    "model": "whisper-1",
                }
                if language:
                    data["language"] = language

                response = await client.post(
                    f"{settings.litellm_base_url}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {settings.litellm_master_key}"},
                    files=files,
                    data=data,
                    timeout=60.0,
                )

                if response.status_code == 200:
                    result = response.json()
                    return {
                        "text": result.get("text", ""),
                        "language": result.get("language", language or "en"),
                        "confidence": 1.0,  # Whisper doesn't return confidence
                        "duration_ms": 0,
                        "provider": "whisper",
                    }
                else:
                    logger.warning(f"Whisper STT returned {response.status_code}")
                    return {
                        "text": "",
                        "language": language or "en",
                        "confidence": 0.0,
                        "duration_ms": 0,
                        "provider": "whisper",
                        "error": f"HTTP {response.status_code}",
                    }
        except Exception as e:
            logger.error(f"STT failed: {e}")
            return {
                "text": "",
                "language": language or "en",
                "confidence": 0.0,
                "duration_ms": 0,
                "provider": "whisper",
                "error": str(e),
            }

    # -------------------------------------------------------------------------
    # Text-to-Speech
    # -------------------------------------------------------------------------

    async def text_to_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        format: str = "mp3",
    ) -> Dict[str, Any]:
        """
        Convert text to speech audio.
        
        Returns: { audio_base64, format, duration_ms, provider, voice_id }
        """
        voice_id = voice_id or self.tts_voice_id

        if self.tts_provider == "elevenlabs" and self.tts_api_key:
            return await self._tts_elevenlabs(text, voice_id, format)
        else:
            # Local TTS placeholder - returns empty audio with metadata
            return {
                "audio_base64": "",
                "format": format,
                "duration_ms": 0,
                "provider": "local",
                "voice_id": voice_id,
                "text_length": len(text),
                "note": "Local TTS not implemented - configure ElevenLabs or other provider",
            }

    async def _tts_elevenlabs(
        self, text: str, voice_id: str, format: str
    ) -> Dict[str, Any]:
        """ElevenLabs TTS."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    headers={
                        "Accept": f"audio/{format}",
                        "Content-Type": "application/json",
                        "xi-api-key": self.tts_api_key,
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_monolingual_v1",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.5,
                        },
                    },
                    timeout=60.0,
                )

                if response.status_code == 200:
                    audio_base64 = base64.b64encode(response.content).decode("utf-8")
                    return {
                        "audio_base64": audio_base64,
                        "format": format,
                        "duration_ms": 0,
                        "provider": "elevenlabs",
                        "voice_id": voice_id,
                        "text_length": len(text),
                    }
                else:
                    logger.warning(f"ElevenLabs TTS returned {response.status_code}")
                    return {
                        "audio_base64": "",
                        "format": format,
                        "duration_ms": 0,
                        "provider": "elevenlabs",
                        "voice_id": voice_id,
                        "error": f"HTTP {response.status_code}",
                    }
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            return {
                "audio_base64": "",
                "format": format,
                "duration_ms": 0,
                "provider": "elevenlabs",
                "voice_id": voice_id,
                "error": str(e),
            }

    # -------------------------------------------------------------------------
    # Voice Activity Detection (placeholder)
    # -------------------------------------------------------------------------

    async def detect_voice_activity(self, audio_bytes: bytes) -> Dict[str, Any]:
        """
        Detect if audio contains voice activity.
        
        Returns: { has_voice: boolean, confidence: float }
        """
        # Placeholder - in production, use WebRTC VAD or similar
        return {
            "has_voice": len(audio_bytes) > 1000,
            "confidence": 0.5,
            "method": "placeholder",
        }


# Singleton instance
voice_service = VoiceService()
