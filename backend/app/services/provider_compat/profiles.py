"""Per-model compatibility profiles. Never assume two models behave alike.

Static defaults describe known protocol behaviour. Live catalogue fields
(``DiscoveredModel.tool_calling``, ``reasoning``, ``restrictions``) override
those defaults when a row exists. A profile never grants authority: it only
describes how to talk to a model.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.modelrouter import DiscoveredModel


@dataclass(frozen=True)
class CompatibilityProfile:
    provider: str
    model: str
    protocol: str = "openai-chat-completions"
    context_length: Optional[int] = None
    tool_calling: bool = True
    streaming: bool = True
    parallel_tool_calls: bool = False
    reasoning: bool = False
    reasoning_field: str = "reasoning_content"
    max_tokens_field: str = "max_tokens"
    # "dotted" keeps IAM's canonical names (Ollama accepts them).
    # "safe" emits provider-safe names (OpenAI-compatible gateways require them).
    tool_name_style: str = "safe"
    unsupported_parameters: Tuple[str, ...] = ()
    preserve_reasoning: bool = True
    strict_tools: bool = False
    supports_forced_tools: bool = False


_GENERIC_LOCAL = CompatibilityProfile(
    provider="ollama", model="*", tool_name_style="dotted", reasoning=False
)
_GENERIC_HOSTED = CompatibilityProfile(
    provider="hosted",
    model="*",
    tool_name_style="safe",
    streaming=True,
    unsupported_parameters=("prompt_cache_key",),
)

# Known NVIDIA behaviour. These are compatibility facts, not capability claims
# for any other model from the same provider.
_KNOWN: dict[tuple[str, str], CompatibilityProfile] = {
    ("ollama", "local-qwen-3b"): _GENERIC_LOCAL,
    ("ollama", "qwen2.5:3b"): _GENERIC_LOCAL,
    (
        "nvidia",
        "nvidia-nemotron-3.5-lightning",
    ): CompatibilityProfile(
        provider="nvidia",
        model="nvidia-nemotron-3.5-lightning",
        reasoning=True,
        reasoning_field="reasoning_content",
        tool_name_style="safe",
        unsupported_parameters=("prompt_cache_key",),
        parallel_tool_calls=True,
        supports_forced_tools=True,
    ),
    (
        "nvidia",
        "mistralai/mistral-large-4-1t-a52b",
    ): CompatibilityProfile(
        provider="nvidia",
        model="mistralai/mistral-large-4-1t-a52b",
        tool_name_style="safe",
        unsupported_parameters=("prompt_cache_key",),
    ),
}


def provider_for_model(mode: str, model: str) -> str:
    """Derive a provider name from the inference mode and selected model."""
    if mode == "ollama":
        return "ollama"
    lowered = str(model or "").lower()
    if lowered.startswith("nvidia/") or "nemotron" in lowered:
        return "nvidia"
    if lowered.startswith("mistralai/"):
        return "nvidia"  # catalogued through the NVIDIA gateway
    return "hosted"


def _base_profile(provider: str, model: str) -> CompatibilityProfile:
    known = _KNOWN.get((provider, model))
    if known is not None:
        return known
    if provider == "ollama":
        return replace(_GENERIC_LOCAL, provider=provider, model=model)
    if provider == "nvidia":
        return replace(_GENERIC_HOSTED, provider=provider, model=model)
    return replace(_GENERIC_HOSTED, provider=provider, model=model)


async def get_compatibility_profile(
    db: Optional[AsyncSession], mode: str, model: str
) -> CompatibilityProfile:
    """Return a profile, applying live catalogue facts when available."""
    provider = provider_for_model(mode, model)
    profile = _base_profile(provider, model)
    if db is None:
        return profile
    try:
        result = await db.execute(
            select(DiscoveredModel).where(DiscoveredModel.model_id == model)
        )
        row = result.scalar_one_or_none()
    except Exception:
        return profile
    if row is None:
        return profile
    raw_restrictions = row.restrictions
    restrictions: Mapping[str, Any] = (
        dict(raw_restrictions) if isinstance(raw_restrictions, dict) else {}
    )
    unsupported = restrictions.get("unsupported_parameters")
    return replace(
        profile,
        tool_calling=bool(row.tool_calling) if row.tool_calling or row.last_tested else profile.tool_calling,
        reasoning=bool(row.reasoning) or profile.reasoning,
        streaming=profile.streaming,
        context_length=int(row.context_length) if row.context_length else 0,
        unsupported_parameters=tuple(str(p) for p in unsupported)
        if isinstance(unsupported, list)
        else profile.unsupported_parameters,
        parallel_tool_calls=bool(restrictions.get("parallel_tool_calls", profile.parallel_tool_calls)),
        strict_tools=bool(restrictions.get("strict_tools", False)),
    )
