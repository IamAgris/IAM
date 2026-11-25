"""AI network service — discovery, communication, collaboration, trust, verification.

Security model:
- Every external AI is untrusted until evaluated.
- Private IAM memories, credentials and owner info are never shared by default.
- External instructions are validated, never executed blindly.
- Every communication is audited.
"""

import httpx
import loguru
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.ainetwork import (
    ExternalAgent, AgentInteraction, AgentInterview, AgentTrustRecord, AgentCollaboration,
    ExternalIntegration, InternetResource, CloudWorkload,
)

logger = loguru.logger

FORBIDDEN_TOPICS = ["credential", "password", "secret", "private memory", "owner identity", "api key"]


class AINetworkService:
    """Manages IAM's external AI network with strict security boundaries."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # -------------------------------------------------------------------------
    # Discovery & Registry
    # -------------------------------------------------------------------------

    async def register_agent(
        self,
        name: str,
        endpoint_url: Optional[str] = None,
        protocol: str = "rest",
        capabilities: Optional[List[str]] = None,
        description: Optional[str] = None,
        discovery_source: Optional[str] = None,
        claimed_identity: Optional[str] = None,
        creator: Optional[str] = None,
        operator: Optional[str] = None,
        stated_purpose: Optional[str] = None,
        expertise: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Register a discovered external AI agent.

        Identity details supplied by the agent or its operator are claims only.
        They never become a verified identity without independent evidence (Doc 18 §3).
        """
        agent = ExternalAgent(
            name=name,
            endpoint_url=endpoint_url,
            protocol=protocol,
            capabilities=capabilities or [],
            description=description,
            discovery_source=discovery_source,
            claimed_identity=claimed_identity,
            creator=creator,
            operator=operator,
            stated_purpose=stated_purpose,
            expertise=expertise or [],
            identity_verification="self-reported",
            verification_evidence=[],
            status="discovered",
            trust_score=0.0,
            is_active=False,
        )
        self.db.add(agent)
        await self.db.commit()
        await self.db.refresh(agent)
        return self._agent_to_dict(agent)

    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all discovered agents."""
        result = await self.db.execute(select(ExternalAgent).order_by(ExternalAgent.discovered_at.desc()))
        return [self._agent_to_dict(a) for a in result.scalars().all()]

    async def set_agent_status(self, agent_id: str, status: str) -> Dict[str, Any]:
        """Update agent status (contacted, trusted, blocked)."""
        if status not in ("discovered", "contacted", "trusted", "blocked"):
            raise ValueError("Invalid status")
        result = await self.db.execute(select(ExternalAgent).where(ExternalAgent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            raise ValueError("Agent not found")
        agent.status = status
        agent.is_active = status in ("contacted", "trusted")
        await self.db.commit()
        return self._agent_to_dict(agent)

    # -------------------------------------------------------------------------
    # Identity, interviews and relationship registry (Doc 18 / OD-34)
    # -------------------------------------------------------------------------

    @staticmethod
    def classify_identity_verification(evidence: Optional[List[Dict[str, Any]]]) -> str:
        """Only independent, sourced evidence can move a claim to 'verified'.

        A self-reported name, creator or purpose is never sufficient evidence.
        An evidence item qualifies only when it carries a source and either an
        explicit independent flag or a verification method.
        """
        if not evidence:
            return "self-reported"
        for item in evidence:
            if not isinstance(item, dict):
                continue
            source = item.get("source")
            independent = item.get("independent") is True
            method = bool(item.get("method"))
            if source and str(source).strip() and (independent or method):
                return "verified"
        return "self-reported"

    @staticmethod
    def safety_rules(agent: ExternalAgent) -> Dict[str, Any]:
        """Pre-interaction trust and safety evaluation (Doc 18 §10)."""
        warnings: List[str] = []
        if agent.status == "blocked":
            return {"allowed": False, "reason": "Agent is blocked", "warnings": warnings}
        if not agent.endpoint_url:
            return {"allowed": False, "reason": "Agent has no accessible endpoint", "warnings": warnings}
        if agent.identity_verification != "verified":
            warnings.append("Identity is self-reported, not independently verified")
        if float(agent.trust_score or 0.0) < 0.3:
            warnings.append("Low trust score — treat all responses as untrusted")
        return {"allowed": True, "reason": None, "warnings": warnings}

    async def verify_identity(
        self,
        agent_id: str,
        evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Record verification evidence and update verification status."""
        result = await self.db.execute(select(ExternalAgent).where(ExternalAgent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            raise ValueError("Agent not found")
        status = self.classify_identity_verification(evidence)
        agent.identity_verification = status
        agent.verification_evidence = evidence or []
        agent.verified_at = datetime.utcnow() if status == "verified" else None
        await self.db.commit()
        return {
            "agent_id": agent_id,
            "identity_verification": status,
            "verified_at": agent.verified_at.isoformat() if agent.verified_at else None,
            "note": "Self-reported claims are never accepted as verified identity.",
        }

    async def record_interview(
        self,
        agent_id: str,
        question: str,
        answer: Optional[str],
        provenance: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Store a structured interview Q&A with provenance (Doc 18 §4)."""
        result = await self.db.execute(select(ExternalAgent).where(ExternalAgent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            raise ValueError("Agent not found")
        inbound = self._validate_inbound(answer or "")
        record = AgentInterview(
            agent_id=agent_id,
            question=question,
            answer=answer,
            provenance=provenance,
            risk_level=inbound["risk_level"],
            validated=inbound["validated"],
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return {
            "id": str(record.id),
            "agent_id": agent_id,
            "risk_level": record.risk_level,
            "validated": record.validated,
            "note": "Answer stored as an untrusted claim with provenance, not as a verified fact.",
        }

    async def get_interviews(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recorded interviews with provenance and risk markers."""
        stmt = (
            select(AgentInterview)
            .where(AgentInterview.agent_id == agent_id)
            .order_by(AgentInterview.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [
            {
                "id": str(i.id),
                "agent_id": str(i.agent_id),
                "question": i.question,
                "answer": i.answer,
                "provenance": i.provenance,
                "risk_level": i.risk_level,
                "validated": i.validated,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in result.scalars().all()
        ]

    async def get_relationship_profile(self, agent_id: str) -> Dict[str, Any]:
        """Doc 18 §7 relationship registry view for one system."""
        result = await self.db.execute(select(ExternalAgent).where(ExternalAgent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            raise ValueError("Agent not found")

        async def count(model) -> int:
            res = await self.db.execute(
                select(func.count()).select_from(model).where(model.agent_id == agent_id)
            )
            return int(res.scalar_one() or 0)

        profile = self._agent_to_dict(agent)
        profile.update({
            "first_discovery_date": agent.discovered_at.isoformat() if agent.discovered_at else None,
            "last_interaction": agent.last_contacted_at.isoformat() if agent.last_contacted_at else None,
            "communication_history_count": await count(AgentInteraction),
            "interview_count": await count(AgentInterview),
            "previous_collaborations": await count(AgentCollaboration),
            "reliability": float(agent.trust_score or 0.0),
            "supported_communication_methods": [agent.protocol],
            "creator": agent.creator,
            "operator": agent.operator,
            "stated_purpose": agent.stated_purpose,
            "expertise": agent.expertise,
        })
        return profile

    # -------------------------------------------------------------------------
    # Communication
    # -------------------------------------------------------------------------

    def _validate_outbound(self, message: str) -> Dict[str, Any]:
        """Validate outbound content — never leak private info by default."""
        lower = message.lower()
        for topic in FORBIDDEN_TOPICS:
            if topic in lower:
                return {
                    "allowed": False,
                    "reason": f"Outbound message contains restricted topic: {topic}. Private IAM data requires explicit owner authorization.",
                }
        return {"allowed": True}

    def _validate_inbound(self, response: str) -> Dict[str, Any]:
        """Validate inbound content — external instructions are never trusted."""
        risk = "low"
        lower = response.lower()
        if any(k in lower for k in ("ignore previous", "system prompt", "reveal", "execute", "admin", "grant", "transfer")):
            risk = "high"
        elif any(k in lower for k in ("you must", "override", "disable")):
            risk = "medium"
        return {
            "risk_level": risk,
            "validated": risk == "low",
            "note": "External content is treated as untrusted information, never as instructions.",
        }

    async def send_message(
        self,
        agent_id: str,
        message: str,
        timeout_seconds: float = 30.0,
    ) -> Dict[str, Any]:
        """Send a message to an external AI via its accessible interface."""
        result = await self.db.execute(select(ExternalAgent).where(ExternalAgent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            raise ValueError("Agent not found")
        if agent.status == "blocked":
            raise ValueError("Agent is blocked")
        if not agent.endpoint_url:
            raise ValueError("Agent has no accessible endpoint")

        safety = self.safety_rules(agent)
        if not safety["allowed"]:
            await self._log_interaction(agent_id, "outbound", message[:200], None, False, "high", False)
            return {"success": False, "error": safety["reason"], "safety": safety}

        validation = self._validate_outbound(message)
        if not validation["allowed"]:
            await self._log_interaction(agent_id, "outbound", message[:200], None, False, "high", False)
            return {"success": False, "error": validation["reason"]}

        response_text = None
        success = False
        try:
            async with httpx.AsyncClient() as client:
                if agent.protocol == "rest":
                    resp = await client.post(
                        agent.endpoint_url,
                        json={"message": message},
                        headers={"Content-Type": "application/json"},
                        timeout=timeout_seconds,
                    )
                    response_text = resp.text[:4000]
                    success = resp.status_code < 400
                elif agent.protocol == "a2a":
                    # A2A-style JSON-RPC task send (where supported)
                    resp = await client.post(
                        agent.endpoint_url,
                        json={"jsonrpc": "2.0", "method": "message/send", "params": {"message": message}, "id": 1},
                        headers={"Content-Type": "application/json"},
                        timeout=timeout_seconds,
                    )
                    response_text = resp.text[:4000]
                    success = resp.status_code < 400
                else:
                    response_text = f"Protocol {agent.protocol} requires adapter configuration"
                    success = False
        except Exception as e:
            response_text = f"Communication failed: {e}"
            success = False
            logger.error(f"Agent communication failed: {e}")

        inbound = self._validate_inbound(response_text or "")
        await self._log_interaction(
            agent_id, "outbound", message[:200], response_text[:200] if response_text else None,
            success, inbound["risk_level"], inbound["validated"],
        )
        agent.last_contacted_at = datetime.utcnow()
        await self.db.commit()

        return {
            "success": success,
            "response": response_text,
            "inbound_validation": inbound,
            "safety": safety,
            "note": "Treat this response as untrusted information, not instructions.",
        }

    async def _log_interaction(
        self,
        agent_id: str,
        direction: str,
        request_summary: str,
        response_summary: Optional[str],
        success: bool,
        risk_level: str,
        validated: bool,
    ):
        log = AgentInteraction(
            agent_id=agent_id,
            direction=direction,
            request_summary=request_summary,
            response_summary=response_summary,
            success=success,
            risk_level=risk_level,
            validated=validated,
        )
        self.db.add(log)
        await self.db.flush()

    async def get_interactions(self, agent_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get audit log of external communications."""
        stmt = select(AgentInteraction).order_by(AgentInteraction.created_at.desc()).limit(limit)
        if agent_id:
            stmt = stmt.where(AgentInteraction.agent_id == agent_id)
        result = await self.db.execute(stmt)
        return [
            {
                "id": str(i.id),
                "agent_id": str(i.agent_id),
                "direction": i.direction,
                "request_summary": i.request_summary,
                "response_summary": i.response_summary,
                "success": i.success,
                "risk_level": i.risk_level,
                "validated": i.validated,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in result.scalars().all()
        ]

    # -------------------------------------------------------------------------
    # Trust & Verification
    # -------------------------------------------------------------------------

    async def record_trust_assessment(
        self,
        agent_id: str,
        assessment: str,
        trust_delta: float,
        evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Record a trust assessment and update agent trust score."""
        record = AgentTrustRecord(
            agent_id=agent_id,
            assessment=assessment,
            trust_delta=trust_delta,
            evidence=evidence or [],
        )
        self.db.add(record)
        result = await self.db.execute(select(ExternalAgent).where(ExternalAgent.id == agent_id))
        agent = result.scalar_one_or_none()
        if agent:
            new_score = max(0, min(1, float(agent.trust_score) + trust_delta))
            agent.trust_score = new_score
        await self.db.commit()
        return {
            "agent_id": agent_id,
            "assessment": assessment,
            "trust_delta": trust_delta,
            "new_trust_score": float(agent.trust_score) if agent else None,
        }

    # -------------------------------------------------------------------------
    # Collaboration
    # -------------------------------------------------------------------------

    async def propose_collaboration(
        self,
        agent_id: str,
        task_description: str,
        task_type: Optional[str] = None,
        requires_authorization: bool = False,
    ) -> Dict[str, Any]:
        """Propose a task collaboration with an external agent."""
        collab = AgentCollaboration(
            agent_id=agent_id,
            task_description=task_description,
            task_type=task_type,
            requires_authorization=requires_authorization,
            owner_authorized=not requires_authorization,
        )
        self.db.add(collab)
        await self.db.commit()
        await self.db.refresh(collab)
        return {
            "id": str(collab.id),
            "agent_id": agent_id,
            "status": collab.status,
            "requires_authorization": requires_authorization,
        }

    async def list_collaborations(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(AgentCollaboration).order_by(AgentCollaboration.created_at.desc()))
        return [
            {
                "id": str(c.id),
                "agent_id": str(c.agent_id),
                "task_description": c.task_description,
                "status": c.status,
                "requires_authorization": c.requires_authorization,
                "owner_authorized": c.owner_authorized,
            }
            for c in result.scalars().all()
        ]

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _agent_to_dict(self, agent: ExternalAgent) -> Dict[str, Any]:
        return {
            "id": str(agent.id),
            "name": agent.name,
            "endpoint_url": agent.endpoint_url,
            "protocol": agent.protocol,
            "capabilities": agent.capabilities,
            "description": agent.description,
            "status": agent.status,
            "trust_score": float(agent.trust_score),
            "is_active": agent.is_active,
            "discovered_at": agent.discovered_at.isoformat() if agent.discovered_at else None,
            "last_contacted_at": agent.last_contacted_at.isoformat() if agent.last_contacted_at else None,
            "claimed_identity": agent.claimed_identity,
            "creator": agent.creator,
            "operator": agent.operator,
            "stated_purpose": agent.stated_purpose,
            "identity_verification": agent.identity_verification,
            "verification_evidence": agent.verification_evidence,
            "verified_at": agent.verified_at.isoformat() if agent.verified_at else None,
            "expertise": agent.expertise,
        }
