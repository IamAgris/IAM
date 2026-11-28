"""Voice service - speech-to-text and text-to-speech (pluggable providers)"""

import array
import asyncio
import base64
import io
import math
import os

import httpx
import loguru
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

    def __init__(self):  # type: ignore[no-untyped-def]
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
        if settings.voice_tts_url:
            return await self._tts_http(text, voice_id, format)
        return {
            "audio_base64": "",
            "format": format,
            "duration_ms": 0,
            "provider": "local",
            "voice_id": voice_id,
            "text_length": len(text),
            "note": "No TTS provider configured; set VOICE_TTS_URL or an ElevenLabs key",
        }

    async def _tts_http(
        self, text: str, voice_id: str, format: str
    ) -> Dict[str, Any]:
        """Generic HTTP TTS endpoint (self-hosted or provider-compatible)."""
        token = os.environ.get(settings.voice_tts_api_key_env, "")
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    settings.voice_tts_url,
                    headers=headers,
                    json={"text": text, "voice": voice_id, "format": format},
                )
            if response.status_code >= 300:
                return {
                    "audio_base64": "",
                    "format": format,
                    "duration_ms": 0,
                    "provider": "http",
                    "voice_id": voice_id,
                    "error": f"HTTP {response.status_code}",
                }
            payload = response.json() if "json" in response.headers.get("content-type", "") else {}
            audio = payload.get("audio_base64") if isinstance(payload, dict) else None
            if not audio:
                audio = base64.b64encode(response.content).decode("utf-8")
            duration = payload.get("duration_ms", 0) if isinstance(payload, dict) else 0
            return {
                "audio_base64": audio,
                "format": format,
                "duration_ms": duration,
                "provider": "http",
                "voice_id": voice_id,
                "text_length": len(text),
            }
        except Exception as exc:
            logger.error(f"HTTP TTS failed: {exc}")
            return {
                "audio_base64": "",
                "format": format,
                "duration_ms": 0,
                "provider": "http",
                "voice_id": voice_id,
                "error": str(exc),
            }

    async def _tts_elevenlabs(
        self, text: str, voice_id: str, format: str
    ) -> Dict[str, Any]:
        """ElevenLabs TTS."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    headers={  # type: ignore[arg-type]
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
    # Voice Activity Detection (energy-based PCM)
    # -------------------------------------------------------------------------

    async def detect_voice_activity(self, audio_bytes: bytes) -> Dict[str, Any]:
        """
        Detect if audio contains voice activity.
        
        Returns: { has_voice: boolean, confidence: float }
        """
        # Energy-based VAD on 16-bit little-endian PCM. Compressed audio must be
        # decoded by the caller first; this never claims to understand codecs.
        frame_samples = int(settings.voice_vad_sample_rate * 0.02)  # 20 ms
        usable = len(audio_bytes) - (len(audio_bytes) % 2)
        samples = array.array("h")
        samples.frombytes(audio_bytes[:usable])
        if len(samples) < frame_samples:
            return {
                "has_voice": False,
                "confidence": 0.0,
                "method": "pcm_energy",
                "frames_analyzed": 0,
                "note": "audio shorter than one 20 ms frame",
            }

        threshold = settings.voice_vad_threshold * 32768
        voiced = 0
        frames = 0
        for start in range(0, len(samples) - frame_samples + 1, frame_samples):
            frame = samples[start : start + frame_samples]
            rms = math.sqrt(sum(s * s for s in frame) / frame_samples)
            frames += 1
            if rms >= threshold:
                voiced += 1

        fraction = voiced / frames if frames else 0.0
        duration_ms = frames * 20
        has_voice = fraction >= 0.2
        return {
            "has_voice": bool(has_voice),
            "confidence": round(fraction, 3),
            "method": "pcm_energy",
            "frames_analyzed": frames,
            "sample_rate": settings.voice_vad_sample_rate,
            "duration_ms": duration_ms,
        }


# Singleton instance
voice_service = VoiceService()  # type: ignore[no-untyped-call]
