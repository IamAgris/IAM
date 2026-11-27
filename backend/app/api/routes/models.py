"""Model gateway routes - LiteLLM integration"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, AsyncGenerator
import json
import httpx
import loguru
import uuid

from app.api.middleware.conversation_owner import conversation_owner
from app.core.config import settings
from app.core.database import get_db_session
from app.services import delegation as delegation_service
from app.services import delegation_orchestrator
from app.services import serving_model
from app.services.iam_context import assemble_context, with_context
from app.services.live_information_policy import (
    SearchTriggerClassifier,
    collect_live_evidence,
    with_live_policy,
)
from app.services.model_inference import InferenceUnavailable, inference_service
from app.services.model_policy import (
    PAID_ACTION,
    SKILL_ACTION,
    ModelPolicyDenied,
    require_authorization,
    require_paid_authorization,
)
from app.services.conversation_service import ConversationService
from app.services.skillruntime.service import SkillRuntimeService
from sqlalchemy.ext.asyncio import AsyncSession

logger = loguru.logger

router = APIRouter(prefix="/api/v1/models", tags=["models"])


class ChatMessage(BaseModel):
    role: str  # user, assistant, system, tool
    content: str


class DelegationTaskRequest(BaseModel):
    task: str
    model: Optional[str] = None
    role: str = "specialist"


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
    # OD-51 §4.4: bounded parallel specialist tasks. Each still needs its own
    # signed authorization inside delegation.run.
    delegation_tasks: List[DelegationTaskRequest] = Field(default_factory=list)
    # Paid inference and skill execution need a signed authorization too.
    allow_paid: bool = False
    skill: Optional[str] = None
    skill_permission: str = "execute"
    skill_arguments: Dict[str, Any] = Field(default_factory=dict)
    # OD-39 priority: user chat may reclaim the single residency slot from
    # internal background work. Internal callers must set this explicitly.
    priority: str = "user"
    # Conversation ID for persistent chat history. If not provided, a new
    # conversation is created automatically.
    conversation_id: Optional[str] = None
    # Optional client-supplied key; a retried turn with the same key is not
    # stored twice. Clients that cannot send one get a fresh random key.
    idempotency_key: Optional[str] = None


def _plain_messages(request: ChatRequest) -> List[Dict[str, str]]:
    return [{"role": m.role, "content": m.content} for m in request.messages]


async def _store_user_turn(
    db: AsyncSession,
    conversation_id: str,
    message: ChatMessage,
    owner: Optional[str],
    key: str,
) -> bool:
    """Store one new user turn, deduplicated by ``key``."""
    service = ConversationService(db)
    if await service.has_turn_key(conversation_id, key):
        return False
    await service.add_message(
        conversation_id=conversation_id,
        role=message.role,
        content=message.content,
        metadata_={"source": "chat", "turn_key": key},
    )
    if message.role == "user":
        await service.refine_title(
            conversation_id, message.content[:60], owner=owner
        )
    return True


def _append_delta(full_response: str, data: Dict[str, Any]) -> str:
    """Accumulate a streamed delta using the payload key inference emits."""
    text = data.get("text")
    return full_response + str(text) if text else full_response


def _new_turn_message(request: ChatRequest) -> Optional[ChatMessage]:
    """The single message this request contributes to stored history.

    Clients may resend a client-side transcript for context; persisting every
    resent message would duplicate the whole history on every turn.
    """
    for message in reversed(request.messages):
        if message.role in ("user", "tool"):
            return message
    return None


async def _prepare_messages(
    request: ChatRequest,
    db: AsyncSession,
    status,
    owner: Optional[str] = None,
) -> tuple[List[Dict[str, str]], Optional[Dict[str, Any]], Optional[Dict[str, Any]], str]:
    """Add IAM context, live web evidence, specialist findings and gated skill output.

    Returns (messages, action, delegation_result, conversation_id).
    """
    # Standing behaviour: the live-information policy is present on every chat
    # request, regardless of whether a search is needed (proposed Doc 32 §2).
    messages = with_live_policy(_plain_messages(request))
    query = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    if request.allow_paid:
        await require_authorization(db, PAID_ACTION)
    # An explicit paid model or a paid hosted fallback must be authorized even
    # when the caller did not set allow_paid.
    for candidate in (request.model, status.model):
        if candidate:
            await require_paid_authorization(db, candidate)

    # Load conversation history and prepend as context. Ownership is enforced
    # here as well as in the conversation routes so chat cannot cross scopes.
    conversation_id = request.conversation_id
    conversation_service = ConversationService(db)
    if conversation_id is not None:
        try:
            conversation_id = str(uuid.UUID(conversation_id))
        except (ValueError, AttributeError, TypeError):
            raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation_id is None:
        conv = await conversation_service.create_conversation(
            title=request.messages[0].content[:60] if request.messages else None,
            owner=owner,
        )
        conversation_id = conv["id"]
    else:
        existing = await conversation_service.get_conversation(
            conversation_id, owner=owner
        )
        if existing is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        # Prepend previous messages as context (excluding the current user message)
        existing_messages = await conversation_service.get_recent_messages(
            conversation_id, limit=20
        )
        if existing_messages:
            history_messages = [
                {"role": m["role"], "content": m["content"]}
                for m in existing_messages
            ]
            messages = history_messages + messages

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

    bundle = await assemble_context(
        db,
        query,
        local=status.mode == "ollama",
        include_memory=request.include_memory,
    )
    messages = with_context(messages, bundle.as_system_message())

    # Automatic search: the deterministic classifier decides that live
    # information is needed; the Web Intelligence Engine performs retrieval
    # through the existing free-provider search stack. Qwen analyses the result.
    if settings.iam_live_info_enabled:
        trigger = SearchTriggerClassifier().classify(query)
        if trigger.needs_search:
            evidence = await collect_live_evidence(query, trigger=trigger, db=db)
            messages = evidence.inject(messages)

    if request.delegation_tasks:
        # Bounded OD-51 fan-out. No private memory is passed to any specialist;
        # only IAM-accepted findings return as labelled, unverified context.
        orchestration = await delegation_orchestrator.run_parallel(
            db,
            [
                delegation_orchestrator.DelegationTask(
                    task=item.task, model=item.model, role=item.role
                )
                for item in request.delegation_tasks
            ],
            actor="chat",
        )
        context = orchestration.context_message()
        if context:
            messages = with_context(messages, context)
        return messages, orchestration.as_dict(), action, conversation_id

    if not query:
        return messages, None, action, conversation_id
    if not request.delegate:
        return messages, None, action, conversation_id

    result = await delegation_service.run(
        db,
        query,
        model=request.delegate_model,
        context=bundle.knowledge_message(),
        actor="chat",
    )
    return with_context(messages, result.context_message()), result.as_dict(), action, conversation_id


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
    request: ChatRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Chat completion with IAM context through the resolved provider."""
    status = await inference_service.resolve()
    owner = conversation_owner(http_request)
    try:
        messages, delegation, action, conversation_id = await _prepare_messages(
            request, db, status, owner=owner
        )
    except ModelPolicyDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    # Store only this turn's message; resent client history is context, not new data.
    new_turn = _new_turn_message(request)
    turn_key = (
        request.idempotency_key
        or http_request.headers.get("idempotency-key")
        or str(uuid.uuid4())
    )
    turn_stored = True
    if new_turn is not None:
        turn_stored = await _store_user_turn(
            db, conversation_id, new_turn, owner, turn_key
        )
    conv_service = ConversationService(db)

    try:
        result = await inference_service.chat(
            messages,
            model=request.model,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens,
            db=db,
            purpose=request.priority,
        )
        if delegation is not None:
            result["iam_delegation"] = delegation
        if action is not None:
            result["iam_action"] = action
        # Let the client continue this conversation on the next turn.
        result["conversation_id"] = conversation_id
        # Store assistant response in conversation
        assistant_content = ""
        if result.get("choices"):
            assistant_content = str(result["choices"][0]["message"].get("content", ""))
        if assistant_content and turn_stored:
            await conv_service.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_content,
                metadata_={"source": "chat"},
            )
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
    request: ChatRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Streaming chat via Server-Sent Events (SSE).

    Event schema (see IAM_API_CONTRACTS.md):
      event: start  -> {request_id, model}
      event: delta  -> {text}
      event: done   -> {finish_reason}
      event: error  -> {code, message}
    """
    request_id = str(uuid.uuid4())
    status = await inference_service.resolve()
    owner = conversation_owner(http_request)
    try:
        messages, delegation, action, conversation_id = await _prepare_messages(
            request, db, status, owner=owner
        )
    except ModelPolicyDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    # Store only this turn's message; resent client history is context, not new data.
    new_turn = _new_turn_message(request)
    turn_key = (
        request.idempotency_key
        or http_request.headers.get("idempotency-key")
        or request_id
    )
    turn_stored = True
    if new_turn is not None:
        turn_stored = await _store_user_turn(
            db, conversation_id, new_turn, owner, turn_key
        )
    conv_service = ConversationService(db)

    async def generate() -> AsyncGenerator[str, None]:
        def evt(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        if not status.available:
            yield evt("start", {
                "request_id": request_id,
                "model": "offline",
                "conversation_id": conversation_id,
            })
            msg = (
                "I am IAM. Live language generation is not configured: "
                f"{status.reason}. Memory, research and decision systems remain active."
            )
            for word in msg.split(" "):
                yield evt("delta", {"text": word + " "})
            # Keep offline responses in the same conversation history.
            if turn_stored:
                await conv_service.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=msg,
                    metadata_={"source": "chat", "offline": True},
                )
            yield evt("done", {"finish_reason": "stop", "offline": True})
            return

        try:
            full_response = ""
            async for item in inference_service.stream(
                messages,
                model=request.model,
                temperature=request.temperature or 0.7,
                max_tokens=request.max_tokens,
                db=db,
                purpose=request.priority,
                allow_tools=(request.priority == "user"),
            ):
                data = dict(item["data"])
                if item["event"] == "start":
                    data["request_id"] = request_id
                    data["conversation_id"] = conversation_id
                    if delegation is not None:
                        data["delegation"] = delegation
                    if action is not None:
                        data["action"] = action
                yield evt(item["event"], data)
                if item["event"] == "delta":
                    full_response = _append_delta(full_response, data)
        except Exception as exc:
            logger.error(f"Stream error: {exc}")
            yield evt("error", {"code": "stream_error", "message": str(exc)[:300]})
            yield evt("done", {"finish_reason": "error"})

        # Store assistant response in conversation
        if full_response and turn_stored:
            await conv_service.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_response,
                metadata_={"source": "chat"},
            )

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
