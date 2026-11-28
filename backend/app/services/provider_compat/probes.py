"""Automatic per-model compatibility probes.

A probe suite records what a model actually accepts instead of assuming two
models from one provider behave alike. It never bypasses IAM's authorization:
every probe uses the normal chat/stream paths with the single tool registry.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.modelrouter import DiscoveredModel
from app.services.iam_tool_manifest import CORE_TOOLS
from app.services.model_inference import inference_service
from app.services.provider_compat.diagnostics import CompatibilityResult, record_result
from app.services.provider_compat.profiles import get_compatibility_profile

_PROMPT = [
    {"role": "user", "content": "Analyse this text: This is a calm and careful message."}
]
_FIRST_TOOL = str(CORE_TOOLS[0]["name"])


@dataclass(frozen=True)
class ProbeResult:
    check: str
    status: str  # accepted | rejected | unsupported | error
    detail: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "check": self.check,
            "status": self.status,
            "detail": self.detail[:300],
        }


async def _chat(
    db: AsyncSession,
    model: str,
    check: str,
    *,
    max_tokens: int,
    force_tool: str | None = None,
) -> ProbeResult:
    try:
        result = await inference_service.chat(
            list(_PROMPT),
            model=model,
            purpose="user",
            db=db,
            max_tokens=max_tokens,
            timeout=60,
            force_tool=force_tool,
        )
    except Exception as exc:  # provider diagnostic, never raises to the caller
        return ProbeResult(check, "error", type(exc).__name__)
    meta = result.get("iam_inference") or {}
    compat = meta.get("compatibility") or {}
    if compat.get("tools_fallback"):
        return ProbeResult(check, "rejected", "tool schema rejected; tools removed")
    executed = meta.get("tools_executed") or []
    return ProbeResult(
        check,
        "accepted" if bool(meta.get("tools_offered") or executed) else "rejected",
        f"tools_offered={bool(meta.get('tools_offered'))} executed={len(executed)}",
    )


async def _run_probe_once(
    db: AsyncSession, provider: str, model: str
) -> List[ProbeResult]:
    """Run one pass of the probe matrix for a model."""
    mode = "ollama" if provider == "ollama" else "hosted"
    profile = await get_compatibility_profile(db, mode, model)
    results: List[ProbeResult] = []

    basic = await _chat(db, model, "basic_inference", max_tokens=8)
    results.append(basic)
    if basic.status != "accepted":
        await _persist(db, provider, model, results)
        return results

    results.append(await _chat(db, model, "tool_schema", max_tokens=16))

    if profile.supports_forced_tools:
        forced = await _chat(
            db, model, "forced_tool", max_tokens=256, force_tool=_FIRST_TOOL
        )
        results.append(forced)
    else:
        results.append(ProbeResult("forced_tool", "unsupported", "profile gate"))

    if profile.streaming:
        try:
            seen_tool = False
            saw_error = ""
            async for event in inference_service.stream(
                list(_PROMPT),
                model=model,
                purpose="user",
                allow_tools=True,
                force_tool=_FIRST_TOOL if profile.supports_forced_tools else None,
                db=db,
                max_tokens=256,
            ):
                if event.get("event") == "tool_executed":
                    seen_tool = True
                if event.get("event") == "error":
                    saw_error = str((event.get("data") or {}).get("code") or "error")
            results.append(
                ProbeResult(
                    "streaming_tool",
                    "accepted" if seen_tool else "rejected",
                    saw_error or f"tool_executed_seen={seen_tool}",
                )
            )
        except Exception as exc:
            results.append(ProbeResult("streaming_tool", "error", type(exc).__name__))
    else:
        results.append(ProbeResult("streaming_tool", "unsupported", "profile gate"))

    if profile.parallel_tool_calls:
        observed = 0
        error = ""
        # A model can emit one call per turn non-deterministically; retry a
        # small bounded number of times before declaring the capability absent.
        for attempt in range(3):
            if attempt:
                await asyncio.sleep(2)
            try:
                async for event in inference_service.stream(
                    [
                        {
                            "role": "user",
                            "content": (
                                "Call BOTH tone_analyze with text='calm message' "
                                "AND sandbox_status in one response. Emit two "
                                "function calls."
                            ),
                        }
                    ],
                    model=model,
                    purpose="user",
                    allow_tools=True,
                    db=db,
                    max_tokens=1024,
                ):
                    if event.get("event") == "tool_executed":
                        observed = max(
                            observed, int((event.get("data") or {}).get("count") or 0)
                        )
            except Exception as exc:
                error = type(exc).__name__
            if observed >= 2:
                break
        results.append(
            ProbeResult(
                "parallel_tool_calls",
                "accepted" if observed >= 2 else ("rejected" if not error else "error"),
                f"observed_calls={observed}" if observed >= 2 else (error or f"observed_calls={observed}"),
            )
        )
    else:
        results.append(ProbeResult("parallel_tool_calls", "unsupported", "profile gate"))

    for item in results:
        await record_result(
            db,
            CompatibilityResult(
                provider=provider,
                model=model,
                check=item.check,
                status=item.status,
                detail=item.detail,
            ),
        )
    await _persist(db, provider, model, results)
    return results


def _score(results: List[ProbeResult]) -> int:
    return sum(1 for item in results if item.status == "accepted")


async def run_compatibility_probes(
    db: AsyncSession,
    provider: str,
    model: str,
    retries: int = 0,
    retry_delay_seconds: int = 60,
) -> List[ProbeResult]:
    """Run the probe matrix, retrying transient provider throttling if asked.

    Only the best pass is returned. Retries are caller-controlled and bounded;
    they never disable checks or weaken governance.
    """
    best: List[ProbeResult] = []
    for attempt in range(max(0, min(retries, 3)) + 1):
        results = await _run_probe_once(db, provider, model)
        if _score(results) > _score(best):
            best = results
        if _score(best) == len(results) and results:
            break
        if attempt < retries:
            await asyncio.sleep(max(0, min(retry_delay_seconds, 120)))
    await _persist(db, provider, model, best)
    return best


async def _persist(
    db: AsyncSession, provider: str, model: str, results: List[ProbeResult]
) -> None:
    """Store the compatibility record on the discovered model row."""
    try:
        row = (
            await db.execute(select(DiscoveredModel).where(DiscoveredModel.model_id == model))
        ).scalar_one_or_none()
        if row is None:
            return
        setattr(
            row,
            "test_result",
            {
                "provider": provider,
                "checks": [item.as_dict() for item in results],
                "source": "provider_compat.probes",
            },
        )
        setattr(row, "last_tested", datetime.now(timezone.utc))
        await db.commit()
    except Exception:
        # Diagnostics must never break a probe response.
        await db.rollback()
