"""Deterministic executor for IAM's callable tool subset.

Every call passes through the existing ``ToolRegistry``/``ToolPermission`` gate
before a service is touched. Arguments are data, never instructions. Results are
small, bounded evidence dicts and are returned to the model as untrusted data.
Consequential or approval-bearing actions are not in this executor; they remain
on their governed HTTP routes.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

from app.services.iam_tool_manifest import executable_tool_names


def _text(args: Mapping[str, Any], key: str, limit: int) -> str:
    return str(args.get(key) or "").strip()[:limit]


def _int(args: Mapping[str, Any], key: str, default: int, low: int, high: int) -> int:
    try:
        value = int(args.get(key) or default)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, value))


async def execute_registered_tool(
    db: Any, name: str, args: Mapping[str, Any]
) -> Dict[str, Any]:
    """Execute one allowlisted tool after deterministic permission checks."""
    if name not in executable_tool_names():
        return {"error": f"tool not permitted: {name[:60]}"}
    if db is None:
        return {"error": "tool authorization unavailable: no database session"}

    from app.services.tool_authorization import ToolAuthorizationError, authorize_tool_call

    try:
        await authorize_tool_call(db, name)
    except ToolAuthorizationError as exc:
        return {"error": "tool authorization refused", "code": exc.code}

    try:
        if name == "tone.analyze":
            from app.services.tone_service import ToneService

            result = ToneService(db).analyse_text(_text(args, "text", 4000))
            return {
                "status": "analysed",
                "tone": result.get("tone"),
                "register": result.get("register"),
                "sentiment": result.get("sentiment"),
                "confidence": result.get("confidence"),
                "manipulation_indicators": list(result.get("manipulation_indicators") or [])[:10],
                "caveat": str(result.get("caveat") or "")[:300],
            }

        if name == "network.inspect":
            from app.services.ainetwork_service import AINetworkService

            agents = await AINetworkService(db).list_agents()
            return {
                "status": "ok",
                "count": len(agents),
                "agents": [
                    {
                        "id": str(item.get("id") or ""),
                        "name": str(item.get("name") or "")[:120],
                        "status": str(item.get("status") or "")[:40],
                    }
                    for item in agents[:10]
                ],
            }

        if name == "sandbox.status":
            from app.services.free_sandboxes.service import FreeSandboxService

            policy = FreeSandboxService(db).policy()
            return {
                "status": "ok",
                "enabled": bool(policy.get("enabled")),
                "providers": [str(p)[:80] for p in (policy.get("providers") or [])[:10]],
                "credential_status_count": len(policy.get("credential_status") or []),
                "paid_fallback": bool(policy.get("paid_fallback")),
            }

        if name == "finance.research.read":
            from app.services.investment_intelligence.service import (
                InvestmentIntelligenceService,
            )
            from app.services.prediction_markets.service import PredictionMarketService

            limit = _int(args, "limit", 5, 1, 10)
            markets = await PredictionMarketService(db).markets()
            theses = await InvestmentIntelligenceService(db).records()
            return {
                "status": "ok",
                "mode": "research_only",
                "market_count": len(markets),
                "markets": [
                    str(item.get("question") or item.get("title") or "")[:160]
                    for item in markets[:limit]
                ],
                "thesis_count": len(theses),
                "theses": [
                    str(item.get("title") or item.get("summary") or "")[:160]
                    for item in theses[:limit]
                ],
                "note": "read-only research; no order, spend or value movement performed",
            }

        if name == "iics.egress.check":
            from app.services.iics.egress import EgressGateway

            egress_decision = EgressGateway().assess(_text(args, "url", 500))
            return {"status": "ok", "decision": egress_decision.as_dict()}

        if name == "iics.research.strategy":
            from app.services.iics.search_strategy import StrategySelector

            domains = args.get("known_domains")
            known = [str(d)[:120] for d in domains[:10]] if isinstance(domains, list) else []
            prior = args.get("prior_confidence")
            try:
                confidence = float(prior) if prior is not None else None
            except (TypeError, ValueError):
                confidence = None
            strategy_decision = StrategySelector().select(
                _text(args, "question", 500),
                known_domains=known,
                prior_confidence=confidence,
            )
            return {"status": "ok", "strategy": strategy_decision.as_dict()}

        if name == "iics.source.register":
            from app.services.iics.source_registry import SourceRegistry

            rights_raw = args.get("rights")
            rights = (
                {str(k): bool(v) for k, v in rights_raw.items() if len(str(k)) < 80}
                if isinstance(rights_raw, dict)
                else None
            )
            record = await SourceRegistry(db).register(
                _text(args, "url", 500),
                licence=_text(args, "licence", 120) or None,
                rights=rights,
            )
            return {
                "status": "ok",
                "source_id": str(record.get("id") or record.get("source_id") or "")[:80],
                "duplicate": bool(record.get("duplicate")),
                "licence": str(record.get("licence") or "")[:120],
            }

        if name == "iics.schedule.create":
            from app.services.iics.scheduler import ScheduledResearchService

            record = await ScheduledResearchService(db).create(
                _text(args, "goal", 300),
                _text(args, "query", 500),
                cadence_minutes=_int(args, "cadence_minutes", 1440, 5, 10080),
            )
            return {
                "status": "ok",
                "task_id": str(record.get("task_id") or "")[:80],
                "duplicate": bool(record.get("duplicate")),
                "cadence_minutes": record.get("cadence_minutes"),
            }

        # iics.creator.notify — informational only, never authority-bearing.
        from app.services.iics.creator_email import CreatorEmailBridge

        outcome = await CreatorEmailBridge(db).notify(
            _text(args, "update", 2000), context=_text(args, "context", 1000) or None
        )
        return {
            "status": str(outcome.get("status") or "ok")[:40],
            "delivered": bool(outcome.get("delivered")),
            "error": str(outcome.get("reason") or "")[:120] or None,
        }
    except Exception as exc:  # fail closed; never turn a service failure into success
        return {"error": f"tool execution failed: {type(exc).__name__}"}
