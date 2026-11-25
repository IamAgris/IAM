"""Vision service - image understanding and video analysis via Qwen3.5 multimodal"""

import httpx
import loguru
import base64
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.core.config import settings

logger = loguru.logger


class VisionService:
    """
    Vision processing service using Qwen3.5 multimodal model.
    
    Capabilities:
    - Image understanding (metadata extraction, visual analysis)
    - Video frame sampling and analysis
    - Audio/transcript extraction when useful
    - Multimodal memory storage with source association
    
    Security: treats all media as untrusted information, not instructions.
    Does not permanently store every video encountered.
    """

    def __init__(self):
        self.model = "qwen3.5-9b"  # Multimodal-capable model
        self.max_video_frames = 16  # Sample frames for video analysis
        self.frame_interval_seconds = 5

    # -------------------------------------------------------------------------
    # Image Understanding
    # -------------------------------------------------------------------------

    async def understand_image(
        self,
        image_bytes: bytes,
        content_type: str = "image/jpeg",
        prompt: Optional[str] = None,
        extract_metadata: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze an image using Qwen3.5 multimodal.
        
        Returns: { description, objects, text_ocr, metadata, confidence, provider }
        """
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        image_data_url = f"data:{content_type};base64,{image_base64}"

        prompt_text = prompt or (
            "Analyze this image in detail. Describe what you see, including "
            "objects, people, text, setting, and any notable details. "
            "Be specific and factual."
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.litellm_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.litellm_master_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt_text},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": image_data_url,
                                            "detail": "high",
                                        },
                                    },
                                ],
                            }
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1000,
                    },
                    timeout=120.0,
                )

                if response.status_code == 200:
                    result = response.json()
                    description = result.get("choices", [{}])[0].get("message", {}).get("content", "")

                    return {
                        "description": description,
                        "objects": [],  # Could be extracted from description
                        "text_ocr": None,
                        "metadata": {},
                        "confidence": 0.8,
                        "provider": "qwen3.5-multimodal",
                        "analyzed_at": datetime.utcnow().isoformat(),
                    }
                else:
                    logger.warning(f"Image understanding returned {response.status_code}")
                    return {
                        "description": "",
                        "objects": [],
                        "text_ocr": None,
                        "metadata": {},
                        "confidence": 0.0,
                        "provider": "qwen3.5-multimodal",
                        "error": f"HTTP {response.status_code}",
                    }
        except Exception as e:
            logger.error(f"Image understanding failed: {e}")
            return {
                "description": "",
                "objects": [],
                "text_ocr": None,
                "metadata": {},
                "confidence": 0.0,
                "provider": "qwen3.5-multimodal",
                "error": str(e),
            }

    # -------------------------------------------------------------------------
    # Video Analysis
    # -------------------------------------------------------------------------

    async def analyze_video(
        self,
        video_bytes: bytes,
        content_type: str = "video/mp4",
        prompt: Optional[str] = None,
        max_frames: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a video by sampling frames and understanding them.
        
        Does NOT permanently store the video. Only stores findings in memory.
        
        Returns: { description, frames_analyzed, key_moments, audio_transcript, provider }
        """
        max_frames = max_frames or self.max_video_frames

        # Placeholder: In production, extract frames using ffmpeg or similar,
        # then send sampled frames to the multimodal model.
        # For now, return a structured placeholder response.

        prompt_text = prompt or (
            "Analyze this video. Describe the key events, actions, and visual content. "
            "Note any important details, people, objects, or text visible."
        )

        return {
            "description": "Video analysis placeholder - frame extraction and multimodal analysis to be implemented with ffmpeg integration.",
            "frames_analyzed": 0,
            "max_frames": max_frames,
            "key_moments": [],
            "audio_transcript": None,
            "provider": "qwen3.5-multimodal",
            "analyzed_at": datetime.utcnow().isoformat(),
            "note": "Video stored temporarily for analysis only, not permanently retained",
        }

    async def sample_video_frames(
        self,
        video_bytes: bytes,
        max_frames: int = 16,
    ) -> List[Dict[str, Any]]:
        """
        Sample frames from a video at regular intervals.
        
        Returns list of { frame_index, timestamp_seconds, image_base64 }
        """
        # Placeholder - in production, use ffmpeg to extract frames
        return []

    # -------------------------------------------------------------------------
    # Multimodal Memory Storage
    # -------------------------------------------------------------------------

    async def store_vision_finding_in_memory(
        self,
        db_session,
        content: str,
        source_type: str,  # image, video
        source_url: Optional[str] = None,
        confidence: float = 0.8,
        topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Store vision analysis findings in long-term memory with provenance.
        
        Associates findings with their sources for traceability.
        """
        from app.services.memory_service import MemoryService
        memory_service = MemoryService(db_session)

        result = await memory_service.store_memory(
            content=content,
            memory_type="fact",
            source=source_url or f"{source_type}-analysis",
            confidence=confidence,
            topic=topic or "vision-analysis",
            metadata_={
                "source_type": source_type,
                "source_url": source_url,
                "analysis_type": "multimodal",
            },
        )

        return result


# Singleton instance
vision_service = VisionService()
