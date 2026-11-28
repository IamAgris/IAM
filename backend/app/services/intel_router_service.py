"""Model Provider and Intelligence Router.

NVIDIA is one provider among many — never IAM's permanent or exclusive intelligence.
Selects models by task, capability, quality, cost and availability, with failover.
Free-only mode prevents unexpected charges.
"""

import httpx
import loguru
from typing import Optional, Dict, Any, List, Set
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.modelrouter import AIProvider, DiscoveredModel, RoutingDecision, ProviderUsage
from app.services.adaptive_model_selector import AdaptiveModelSelector

logger = loguru.logger


class IntelligenceRouter:
    """Discovers models, selects by capability, routes with failover, tracks usage."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def initialize_providers(self):  # type: ignore[no-untyped-def]
        """Register known providers. NVIDIA is one of several, not exclusive."""
        providers = [
            ("nvidia", "nvidia", settings.nvidia_base_url, settings.nvidia_free_only),
            ("alibaba-dashscope", "hosted", "https://dashscope.aliyuncs.com/compatible-mode/v1", False),
            ("openai", "hosted", "https://api.openai.com/v1", True),
            ("anthropic", "hosted", "https://api.anthropic.com/v1", True),
            ("ollama", "local", settings.ollama_base_url, True),
        ]
        for name, ptype, base_url, free_only in providers:
            result = await self.db.execute(select(AIProvider).where(AIProvider.name == name))
            if not result.scalar_one_or_none():
                self.db.add(AIProvider(
                    name=name,
                    provider_type=ptype,
                    base_url=base_url,
                    is_active=True,
                    free_only=free_only,
                ))
        await self.db.commit()

    async def discover_nvidia_models(self) -> List[Dict[str, Any]]:
        """
        Discover available models from NVIDIA's catalogue via the OpenAI-compatible
        /models endpoint. Actual choices come from the catalogue, not a hardcoded list.
        """
        if not settings.nvidia_api_key:
            return []

        result = await self.db.execute(select(AIProvider).where(AIProvider.name == "nvidia"))
        provider = result.scalar_one_or_none()
        if not provider:
            return []

        models: List[Dict[str, Any]] = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{settings.nvidia_base_url}/models",
                    headers={"Authorization": f"Bearer {settings.nvidia_api_key}"},
                    timeout=20.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get("data", []):
                        model_id = m.get("id", "")
                        if not model_id:
                            continue
                        is_free = self._is_free_endpoint(model_id)
                        # Skip paid models in free-only mode
                        if provider.free_only and not is_free:
                            continue
                        caps = self._infer_capabilities(model_id)
                        models.append({
                            "model_id": model_id,
                            "display_name": m.get("id", model_id),
                            "capabilities": caps,
                            "is_free": is_free,
                            "context_length": m.get("context_length"),
                        })
        except Exception as e:
            logger.error(f"NVIDIA model discovery failed: {e}")

        # Persist discovered models
        for model in models:
            existing = await self.db.execute(
                select(DiscoveredModel).where(
                    DiscoveredModel.provider_id == provider.id,
                    DiscoveredModel.model_id == model["model_id"],
                )
            )
            dm = existing.scalar_one_or_none()
            if not dm:
                dm = DiscoveredModel(
                    provider_id=provider.id,
                    model_id=model["model_id"],
                    display_name=model["display_name"],
                )
                self.db.add(dm)
            dm.capabilities = model["capabilities"]
            dm.is_free = model["is_free"]
            dm.is_available = True  # type: ignore[assignment]
            dm.last_checked_at = datetime.utcnow()  # type: ignore[assignment]
        await self.db.commit()
        return models

    def _is_free_endpoint(self, model_id: str) -> bool:
        """Heuristic: known free NVIDIA endpoints. Catalogue status is authoritative
        if exposed; otherwise favour open models likely to have free endpoints."""
        lower = model_id.lower()
        free_indicators = ["llama", "qwen", "deepseek", "nemotron", "mistral", "gemma", "phi", "embedding"]
        return any(ind in lower for ind in free_indicators)

    def _infer_capabilities(self, model_id: str) -> List[str]:
        lower = model_id.lower()
        caps = ["reasoning"]
        if any(k in lower for k in ("code", "coder", "deepseek", "starcoder")):
            caps.append("coding")
        if any(k in lower for k in ("vision", "vl", "multimodal", "llava", "nemotron")):
            caps.append("vision")
        if "embed" in lower:
            caps = ["embeddings"]
        if "r1" in lower or "reason" in lower:
            caps.append("reasoning")
        return caps

    async def select_model(
        self,
        task_type: str,
        required_capabilities: Optional[List[str]] = None,
        prefer_provider: Optional[str] = None,
        allow_paid: bool = False,
        task_complexity: Optional[int] = None,
        available_aliases: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """Select the best available model for a task with failover.

        When `available_aliases` is supplied and adaptive selection is enabled,
        hardware-aware local model choice (OD-39) runs first; the caller can
        delegate to a hosted specialist or trusted node when no local model fits.
        """
        required_capabilities = required_capabilities or []
        if settings.adaptive_model_enabled and available_aliases is not None:
            decision = AdaptiveModelSelector().select(
                task_complexity or 3, set(available_aliases), task_type
            )
            if decision.get("delegate"):
                from app.services.model_policy import require_paid_authorization

                await require_paid_authorization(self.db, decision.get("model"))
            self.db.add(RoutingDecision(
                task_type=task_type,
                required_capabilities=required_capabilities,
                selected_provider="delegated" if decision["delegate"] else "ollama",
                selected_model=decision["model"],
                reason=decision["reason"],
                fallback_used=decision["delegate"],
            ))
            await self.db.commit()
            return decision
        result = await self.db.execute(
            select(DiscoveredModel).where(DiscoveredModel.is_available == True)
        )
        models = result.scalars().all()

        if not models:
            # Catalog unavailable — fall back to configured defaults
            return {
                "provider": "fallback",
                "model": "qwen3.5-9b",
                "reason": "No discovered models; using configured default",
                "fallback_used": True,
            }

        # Filter by capability and free-only policy
        candidates = []
        for m in models:
            caps: Any = m.capabilities or []
            if required_capabilities and not all(c in caps for c in required_capabilities):
                continue
            if not m.is_free and not allow_paid:
                continue
            provider_result = await self.db.execute(
                select(AIProvider).where(AIProvider.id == m.provider_id)
            )
            provider = provider_result.scalar_one_or_none()
            if not provider or not provider.is_active:
                continue
            if provider.free_only and not m.is_free:
                continue
            score = float(m.quality_score or 0.5)
            if prefer_provider and provider.name == prefer_provider:
                score += 0.3
            candidates.append((score, provider.name, m.model_id))

        if not candidates:
            return {
                "provider": "fallback",
                "model": "qwen3.5-9b",
                "reason": "No candidate matched requirements; using configured default",
                "fallback_used": True,
            }

        candidates.sort(reverse=True)
        score, provider_name, model_id = candidates[0]

        self.db.add(RoutingDecision(
            task_type=task_type,
            required_capabilities=required_capabilities,
            selected_provider=provider_name,
            selected_model=model_id,
            reason=f"Selected by capability match and quality score ({score:.3f})",
            fallback_used=False,
        ))
        await self.db.commit()

        return {
            "provider": provider_name,
            "model": model_id,
            "reason": f"Capability match; quality score {score:.3f}",
            "fallback_used": False,
        }

    async def list_providers(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(AIProvider))
        return [
            {
                "id": str(p.id),
                "name": p.name,
                "provider_type": p.provider_type,
                "is_active": p.is_active,
                "free_only": p.free_only,
            }
            for p in result.scalars().all()
        ]

    async def list_models(self, provider_name: Optional[str] = None) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(DiscoveredModel))
        models = result.scalars().all()
        if provider_name:
            provider_result = await self.db.execute(
                select(AIProvider).where(AIProvider.name == provider_name)
            )
            provider = provider_result.scalar_one_or_none()
            if provider:
                models = [m for m in models if m.provider_id == provider.id]
        return [
            {
                "id": str(m.id),
                "model_id": m.model_id,
                "display_name": m.display_name,
                "capabilities": m.capabilities,
                "is_free": m.is_free,
                "is_available": m.is_available,
                "context_length": m.context_length,
            }
            for m in models
        ]

    async def get_routing_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(RoutingDecision).order_by(RoutingDecision.created_at.desc()).limit(limit)
        )
        return [
            {
                "task_type": d.task_type,
                "selected_provider": d.selected_provider,
                "selected_model": d.selected_model,
                "reason": d.reason,
                "fallback_used": d.fallback_used,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in result.scalars().all()
        ]
