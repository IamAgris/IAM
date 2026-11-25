"""Model gateway routes - LiteLLM integration"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, AsyncGenerator
import json
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


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat via Server-Sent Events (SSE).

    Event schema (see IAM_API_CONTRACTS.md):
      event: start  -> {request_id, model}
      event: delta  -> {text}
      event: done   -> {finish_reason}
      event: error  -> {code, message}
    """
    request_id = str(__import__("uuid").uuid4())

    async def generate() -> AsyncGenerator[str, None]:
        import asyncio
        def evt(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        # If no provider keys configured, stream a graceful informational response
        has_key = any([
            settings.nvidia_api_key, settings.dashscope_api_key,
            settings.openai_api_key, settings.anthropic_api_key,
        ])
        if not has_key:
            yield evt("start", {"request_id": request_id, "model": "offline"})
            msg = (
                "I am IAM, and I am running without a model provider key. "
                "My memory, research and decision systems are active, but live language "
                "generation needs an API key (NVIDIA or Dashscope) in the environment. "
                "Everything else you see is real."
            )
            for word in msg.split(" "):
                yield evt("delta", {"text": word + " "})
                await asyncio.sleep(0.02)
            yield evt("done", {"finish_reason": "stop", "offline": True})
            return

        # Try real LiteLLM stream first
        try:
            messages = [{"role": m.role, "content": m.content} for m in request.messages]
            yield evt("start", {"request_id": request_id, "model": request.model})

            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
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
                        "stream": True,
                    },
                ) as resp:
                    if resp.status_code != 200:
                        body = ""
                        async for chunk in resp.aiter_text():
                            body += chunk
                        yield evt("error", {"code": "provider_error", "message": body[:400]})
                        yield evt("done", {"finish_reason": "error"})
                        return

                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        payload = line[5:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            obj = json.loads(payload)
                            delta = obj.get("choices", [{}])[0].get("delta", {})
                            text = delta.get("content")
                            if text:
                                yield evt("delta", {"text": text})
                        except Exception:
                            continue

            yield evt("done", {"finish_reason": "stop"})
            return

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield evt("error", {"code": "stream_error", "message": str(e)[:300]})
            yield evt("done", {"finish_reason": "error"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
