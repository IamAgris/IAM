"""Model gateway routes - LiteLLM integration"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import loguru

from app.core.config import settings
from app.core.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

logger = loguru.logger

router = APIRouter(prefix="/api/v1/models", tags=["models"])


class ChatMessage(BaseModel):
    role: str  # user, assistant, system, tool
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str


@router.get("/")
async def list_models():
    """List available models from LiteLLM gateway."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.litellm_base_url}/models",
                headers={"Authorization": f"Bearer {settings.litellm_master_key}"},
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"LiteLLM returned {response.status_code}")
                return {"data": [], "error": f"LiteLLM returned {response.status_code}"}
    except Exception as e:
        logger.error(f"LiteLLM unavailable: {e}")
        raise HTTPException(status_code=502, detail=f"LiteLLM unavailable: {str(e)}")


@router.post("/chat")
async def chat_completion(request: ChatRequest, db: AsyncSession = Depends(get_db_session)):
    """Proxy chat completion through LiteLLM gateway with routing and logging."""
    try:
        # Convert Pydantic models to dicts for LiteLLM
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.litellm_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.litellm_master_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": request.model,
                    "messages": messages,
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                },
                timeout=120.0,
            )

            if response.status_code != 200:
                logger.error(f"LiteLLM error: {response.status_code} {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Model inference failed: {response.text}",
                )

            return response.json()

    except httpx.TimeoutException:
        logger.error("LiteLLM request timed out")
        raise HTTPException(status_code=504, detail="Model inference timed out")
    except Exception as e:
        logger.error(f"Model inference failed: {e}")
        raise HTTPException(status_code=502, detail=f"Model inference failed: {str(e)}")


@router.get("/{model_name}")
async def get_model(model_name: str):
    """Get details for a specific model."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.litellm_base_url}/models/{model_name}",
                headers={"Authorization": f"Bearer {settings.litellm_master_key}"},
                timeout=10.0,
            )
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to get model: {str(e)}")
