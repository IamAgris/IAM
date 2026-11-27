"""Model gateway routes - LiteLLM integration"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, AsyncGenerator
import json
import httpx
import loguru

from app.core.config import settings
from app.core.database import get_db_session
from app.services import delegation as delegation_service
from app.services import serving_model
from app.services.iam_context import assemble_context, with_context
from app.services.model_inference import InferenceUnavailable, inference_service
from app.services.model_policy import (
    PAID_ACTION,
    SKILL_ACTION,
    ModelPolicyDenied,
    require_authorization,
)
from app.services.skillruntime.service import SkillRuntimeService
from sqlalchemy.ext.asyncio import AsyncSession

logger = loguru.logger

router = APIRouter(prefix="/api/v1/models", tags=["models"])


class ChatMessage(BaseModel):
    role: str  # user, assistant, system, tool
    content: str


class ChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    # Private memory is never injected by default: the chat routes are public.
    include_memory: bool = False
    # Optional hosted specialist: explicit opt-in, signed authorization required.
    delegate: bool = False
    delegate_model: Optional[str] = None
    # Paid inference and skill execution need a signed authorization too.
    allow_paid: bool = False
    skill: Optional[str] = None
    skill_permission: str = "execute"
    skill_arguments: Dict[str, Any] = Field(default_factory=dict)


def _plain_messages(request: ChatRequest) -> List[Dict[str, str]]:
    return [{"role": m.role, "content": m.content} for m in request.messages]


async def _prepare_messages(
    request: ChatRequest, db: AsyncSession, status
) -> tuple[List[Dict[str, str]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Add IAM context, an authorized specialist's findings and gated skill output."""
    messages = _plain_messages(request)
    query = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    if request.allow_paid:
        await require_authorization(db, PAID_ACTION)

    action: Optional[Dict[str, Any]] = None
    if request.skill:
        try:
            authority = await require_authorization(
                db, SKILL_ACTION, target_ref=request.skill
            )
            outcome = await SkillRuntimeService(db).invoke(
                request.skill,
                permission=request.skill_permission,
                arguments=request.skill_arguments,
                caller="chat",
            )
            summary = json.dumps(outcome, default=str)[:600]
            action = {
                "status": "executed",
                "skill": request.skill,
                "authorization_id": str(authority.get("authorization_id")),
                "summary": summary,
            }
            messages = with_context(
                messages, f"IAM skill result ({request.skill}): {summary}"
            )
        except ModelPolicyDenied as exc:
            action = {"status": "denied", "skill": request.skill, "reason": str(exc)}
        except Exception as exc:  # pragma: no cover - defensive
            action = {
                "status": "error",
                "skill": request.skill,
                "reason": str(exc)[:200],
            }

    if not query:
        return messages, None, action
    bundle = await assemble_context(
        db,
        query,
        local=status.mode == "ollama",
        include_memory=request.include_memory,
    )
    messages = with_context(messages, bundle.as_system_message())
    if not request.delegate:
        return messages, None, action

    result = await delegation_service.run(
        db,
        query,
        model=request.delegate_model,
        context=bundle.knowledge_message(),
        actor="chat",
    )
    return with_context(messages, result.context_message()), result.as_dict(), action


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


@router.get("/readiness")
async def model_readiness():
    """Report whether real inference is available. Never exposes provider keys."""
    return (await inference_service.resolve()).as_dict()


@router.get("/primary")
async def primary_model():
    """The single primary model IAM uses for frontend and backend intelligence.

    Hosted models are listed as optional delegates/specialists. Callers should
    omit the ``model`` field in chat requests to use this shared primary.
    """
    active = serving_model.current()
    status = await inference_service.resolve()
    return {
        "primary": active.model,
        "source": active.source,
        "version": active.version,
        "resolved_model": status.model,
        "mode": status.mode,
        "available": status.available,
        "reason": status.reason,
        "local_alias": settings.iam_primary_model,
        "local_tag": settings.iam_primary_local_tag,
        "delegates": [settings.adaptive_delegate_model],
    }


@router.post("/chat")
async def chat_completion(
    request: ChatRequest, db: AsyncSession = Depends(get_db_session)
):
    """Chat completion with IAM context through the resolved provider."""
    status = await inference_service.resolve()
    messages, delegation = await _prepare_messages(request, db, status)
    try:
        result = await inference_service.chat(
            messages,
            model=request.model,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens,
        )
        if delegation is not None:
            result["iam_delegation"] = delegation
        return result
    except InferenceUnavailable as exc:
        logger.warning(f"Inference unavailable: {exc}")
        raise HTTPException(status_code=503, detail=str(exc))
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Model inference timed out")
    except Exception as exc:
        logger.error(f"Model inference failed: {exc}")
        raise HTTPException(status_code=502, detail=f"Model inference failed: {exc}")


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest, db: AsyncSession = Depends(get_db_session)
):
    """Streaming chat via Server-Sent Events (SSE).

    Event schema (see IAM_API_CONTRACTS.md):
      event: start  -> {request_id, model}
      event: delta  -> {text}
      event: done   -> {finish_reason}
      event: error  -> {code, message}
    """
    request_id = str(__import__("uuid").uuid4())
    status = await inference_service.resolve()
    messages, delegation = await _prepare_messages(request, db, status)

    async def generate() -> AsyncGenerator[str, None]:
        def evt(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        if not status.available:
            yield evt("start", {"request_id": request_id, "model": "offline"})
            msg = (
                "I am IAM. Live language generation is not configured: "
                f"{status.reason}. Memory, research and decision systems remain active."
            )
            for word in msg.split(" "):
                yield evt("delta", {"text": word + " "})
            yield evt("done", {"finish_reason": "stop", "offline": True})
            return

        try:
            async for item in inference_service.stream(
                messages,
                model=request.model,
                temperature=request.temperature or 0.7,
                max_tokens=request.max_tokens,
            ):
                data = dict(item["data"])
                if item["event"] == "start":
                    data["request_id"] = request_id
                    if delegation is not None:
                        data["delegation"] = delegation
                yield evt(item["event"], data)
        except Exception as exc:
            logger.error(f"Stream error: {exc}")
            yield evt("error", {"code": "stream_error", "message": str(exc)[:300]})
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
