"""Vision routes - image understanding and video analysis"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.database import get_db_session
from app.services.vision_service import vision_service

router = APIRouter(prefix="/api/v1/vision", tags=["vision"])


class ImageUnderstandResponse(BaseModel):
    description: str
    objects: List[str]
    text_ocr: Optional[str]
    metadata: Dict[str, Any]
    confidence: float
    provider: str
    analyzed_at: Optional[str]
    error: Optional[str] = None


class VideoAnalyzeResponse(BaseModel):
    description: str
    frames_analyzed: int
    key_moments: List[Dict[str, Any]]
    audio_transcript: Optional[str]
    provider: str
    analyzed_at: Optional[str]
    note: Optional[str] = None


class VisionMemoryRequest(BaseModel):
    content: str
    source_type: str  # image, video
    source_url: Optional[str] = None
    confidence: float = 0.8
    topic: Optional[str] = None


@router.post("/understand-image", response_model=ImageUnderstandResponse)
async def understand_image(
    image: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    store_in_memory: bool = Form(False),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Analyze an uploaded image using Qwen3.5 multimodal.
    
    Optionally store the findings in long-term memory with provenance.
    """
    image_bytes = await image.read()
    content_type = image.content_type or "image/jpeg"

    result = await vision_service.understand_image(
        image_bytes=image_bytes,
        content_type=content_type,
        prompt=prompt,
    )

    # Optionally store in memory
    if store_in_memory and result.get("description"):
        await vision_service.store_vision_finding_in_memory(
            db_session=db,
            content=result["description"],
            source_type="image",
            source_url=None,
            confidence=result.get("confidence", 0.8),
            topic=prompt or "image-analysis",
        )
        await db.commit()

    return ImageUnderstandResponse(
        description=result.get("description", ""),
        objects=result.get("objects", []),
        text_ocr=result.get("text_ocr"),
        metadata=result.get("metadata", {}),
        confidence=result.get("confidence", 0.0),
        provider=result.get("provider", "unknown"),
        analyzed_at=result.get("analyzed_at"),
        error=result.get("error"),
    )


@router.post("/analyze-video", response_model=VideoAnalyzeResponse)
async def analyze_video(
    video: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    max_frames: Optional[int] = Form(None),
    store_in_memory: bool = Form(False),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Analyze an uploaded video by sampling frames.
    
    Video is NOT permanently stored - only analysis findings are kept.
    """
    video_bytes = await video.read()
    content_type = video.content_type or "video/mp4"

    result = await vision_service.analyze_video(
        video_bytes=video_bytes,
        content_type=content_type,
        prompt=prompt,
        max_frames=max_frames,
    )

    # Optionally store findings in memory (not the video itself)
    if store_in_memory and result.get("description"):
        await vision_service.store_vision_finding_in_memory(
            db_session=db,
            content=result["description"],
            source_type="video",
            source_url=None,
            confidence=result.get("confidence", 0.8),
            topic=prompt or "video-analysis",
        )
        await db.commit()

    return VideoAnalyzeResponse(
        description=result.get("description", ""),
        frames_analyzed=result.get("frames_analyzed", 0),
        key_moments=result.get("key_moments", []),
        audio_transcript=result.get("audio_transcript"),
        provider=result.get("provider", "unknown"),
        analyzed_at=result.get("analyzed_at"),
        note=result.get("note"),
    )
