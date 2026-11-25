"""Voice routes - speech-to-text and text-to-speech"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

from app.services.voice_service import voice_service

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


class STTResponse(BaseModel):
    text: str
    language: str
    confidence: float
    duration_ms: int
    provider: str
    error: Optional[str] = None


class TTSRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None
    format: str = "mp3"


class TTSResponse(BaseModel):
    audio_base64: str
    format: str
    duration_ms: int
    provider: str
    voice_id: str
    text_length: int
    error: Optional[str] = None


class VADResponse(BaseModel):
    has_voice: bool
    confidence: float
    method: str


@router.post("/speech-to-text", response_model=STTResponse)
async def speech_to_text(
    audio: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    """
    Convert uploaded audio to text.
    
    Accepts WAV, MP3, or other common audio formats.
    """
    audio_bytes = await audio.read()
    content_type = audio.content_type or "audio/wav"

    result = await voice_service.speech_to_text(
        audio_bytes=audio_bytes,
        content_type=content_type,
        language=language,
    )

    return STTResponse(
        text=result.get("text", ""),
        language=result.get("language", "en"),
        confidence=result.get("confidence", 0.0),
        duration_ms=result.get("duration_ms", 0),
        provider=result.get("provider", "unknown"),
        error=result.get("error"),
    )


@router.post("/text-to-speech", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """Convert text to speech audio (returns base64-encoded audio)."""
    result = await voice_service.text_to_speech(
        text=request.text,
        voice_id=request.voice_id,
        format=request.format,
    )

    return TTSResponse(
        audio_base64=result.get("audio_base64", ""),
        format=result.get("format", "mp3"),
        duration_ms=result.get("duration_ms", 0),
        provider=result.get("provider", "unknown"),
        voice_id=result.get("voice_id", "default"),
        text_length=result.get("text_length", 0),
        error=result.get("error"),
    )


@router.post("/voice-activity", response_model=VADResponse)
async def voice_activity_detection(
    audio: UploadFile = File(...),
):
    """Detect voice activity in uploaded audio."""
    audio_bytes = await audio.read()
    result = await voice_service.detect_voice_activity(audio_bytes)

    return VADResponse(
        has_voice=result.get("has_voice", False),
        confidence=result.get("confidence", 0.0),
        method=result.get("method", "unknown"),
    )
