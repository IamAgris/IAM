"""AI Communication & Collaboration service (Module C).

Manages AI-to-AI communication, human-mediated channels, conversation continuity,
context exchange, response verification, AI reputation, and audit trail.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_communication import (
    AICommunicationPermission,
    AICommunicationAudit,
    AIConversationMessage,
    AIConversationThread,
    AIContextExchange,
    AIIdentityRegistry,
    AIReputationRecord,
    AIResponseVerification,
    AICapabilityRegistry,
    HumanCommunicationBridge,
)
from app.models.security import AuditEvent


class AICommunicationError(PermissionError):
    """Raised when an AI communication operation fails."""


class AICommunicationService:
    """AI identity registry, capability discovery, conversation threads,
    context exchange, response verification, AI reputation records,
    communication permissions, human communication bridge, and audit trail."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------ identity registry

    async def register_ai_identity(
        self,
        *,
        name: str,
        provider: str,
        model_id: Optional[str] = None,
        communication_channel: str,
        is_local: bool = False,
        communication_permitted: bool = False,
        trust_level: str = "untrusted",
        description: Optional[str] = None,
        actor: str,
    ) -> Dict[str, Any]:
        """Register an AI system IAM can communicate with."""
        valid_channels = ("browser", "local_api", "human_mediated", "email", "other")
        if communication_channel not in valid_channels:
            raise AICommunicationError(f"Invalid communication channel: {communication_channel}")
        valid_trust = ("untrusted", "trusted", "restricted")
        if trust_level not in valid_trust:
            raise AICommunicationError(f"Invalid trust level: {trust_level}")

        row = AIIdentityRegistry(
            name=name,
            provider=provider,
            model_id=model_id,
            communication_channel=communication_channel,
            is_local=is_local,
            is_active=True,
            communication_permitted=communication_permitted,
            trust_level=trust_level,
            description=description,
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit(actor, "ai_identity_registered", str(row.id), {"name": name, "provider": provider})
        await self.db.commit()
        return self._identity_dict(row)

    async def list_identities(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(AIIdentityRegistry))
        return [self._identity_dict(r) for r in result.scalars().all()]

    async def get_identity(self, identity_id: str) -> Dict[str, Any]:
        """Get a single AI identity by ID."""
        row = await self._identity_row(identity_id)
        return self._identity_dict(row)

    async def update_identity(
        self,
        identity_id: str,
        *,
        communication_permitted: Optional[bool] = None,
        trust_level: Optional[str] = None,
        actor: str,
    ) -> Dict[str, Any]:
        row = await self._identity_row(identity_id)
        if communication_permitted is not None:
            row.communication_permitted = communication_permitted  # type: ignore[assignment]
        if trust_level is not None:
            valid_trust = ("untrusted", "trusted", "restricted")
            if trust_level not in valid_trust:
                raise AICommunicationError(f"Invalid trust level: {trust_level}")
            row.trust_level = trust_level  # type: ignore[assignment]
        await self.db.commit()
        await self._audit(actor, "ai_identity_updated", str(row.id), {"trust_level": trust_level})
        return self._identity_dict(row)

    # ------------------------------------------------------------------ capabilities

    async def register_capability(
        self,
        *,
        ai_identity_id: str,
        capability: str,
        confidence_score: int,
        evidence: Optional[List[Dict[str, Any]]] = None,
        actor: str,
    ) -> Dict[str, Any]:
        """Record a capability for an AI system."""
        if not 0 <= confidence_score <= 100:
            raise AICommunicationError("Confidence score must be between 0 and 100")
        row = AICapabilityRegistry(
            ai_identity_id=UUID(str(ai_identity_id)),
            capability=capability,
            confidence_score=confidence_score,
            evidence=evidence or [],
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit(actor, "ai_capability_registered", str(ai_identity_id), {"capability": capability})
        await self.db.commit()
        return self._capability_dict(row)

    async def list_capabilities(self, ai_identity_id: Optional[str] = None) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(AICapabilityRegistry))
        rows = result.scalars().all()
        if ai_identity_id:
            rows = [r for r in rows if str(r.ai_identity_id) == ai_identity_id]
        return [self._capability_dict(r) for r in rows]

    # ------------------------------------------------------------------ conversation threads

    async def create_conversation(
        self,
        *,
        ai_identity_id: str,
        title: str,
        topic: Optional[str] = None,
        is_human_mediated: bool = False,
        actor: str,
    ) -> Dict[str, Any]:
        """Create a conversation thread with an AI system."""
        row = AIConversationThread(
            ai_identity_id=UUID(str(ai_identity_id)),
            title=title,
            topic=topic,
            status="active",
            is_human_mediated=is_human_mediated,
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit(actor, "ai_conversation_created", str(row.id), {"title": title})
        await self.db.commit()
        return self._thread_dict(row)

    async def list_conversations(self, ai_identity_id: Optional[str] = None) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(AIConversationThread))
        rows = result.scalars().all()
        if ai_identity_id:
            rows = [r for r in rows if str(r.ai_identity_id) == ai_identity_id]
        return [self._thread_dict(r) for r in rows]

    async def add_message(
        self,
        *,
        conversation_id: str,
        sender: str,
        content: str,
        message_type: str = "text",
        confidence_score: Optional[int] = None,
        actor: str,
    ) -> Dict[str, Any]:
        """Add a message to a conversation thread."""
        valid_senders = ("iam", "ai", "human")
        if sender not in valid_senders:
            raise AICommunicationError(f"Invalid sender: {sender}")
        if confidence_score is not None and not 0 <= confidence_score <= 100:
            raise AICommunicationError("Confidence score must be between 0 and 100")
        valid_types = ("text", "question", "answer", "code", "system")
        if message_type not in valid_types:
            raise AICommunicationError(f"Invalid message type: {message_type}")

        row = AIConversationMessage(
            conversation_id=UUID(str(conversation_id)),
            sender=sender,
            content=content,
            message_type=message_type,
            confidence_score=confidence_score,
        )
        self.db.add(row)
        # Update thread message count and last message time
        thread_result = await self.db.execute(
            select(AIConversationThread).where(AIConversationThread.id == UUID(str(conversation_id)))
        )
        thread = thread_result.scalar_one_or_none()
        if thread:
            thread.message_count = (thread.message_count or 0) + 1  # type: ignore[assignment]
            from datetime import datetime, timezone
            thread.last_message_at = None  # type: ignore[assignment]  # set by caller if desired
        await self.db.commit()
        return self._message_dict(row)

    async def list_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(AIConversationMessage)
            .where(AIConversationMessage.conversation_id == UUID(str(conversation_id)))
        )
        return [self._message_dict(r) for r in result.scalars().all()]

    # ------------------------------------------------------------------ context exchange

    async def exchange_context(
        self,
        *,
        ai_identity_id: str,
        context_type: str,
        content: Dict[str, Any],
        conversation_id: Optional[str] = None,
        actor: str,
    ) -> Dict[str, Any]:
        """Record context shared with an AI system."""
        row = AIContextExchange(
            ai_identity_id=UUID(str(ai_identity_id)),
            conversation_id=UUID(str(conversation_id)) if conversation_id else None,
            context_type=context_type,
            content=content,
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit(actor, "ai_context_exchanged", str(ai_identity_id), {"context_type": context_type})
        await self.db.commit()
        return self._context_dict(row)

    async def list_context_exchanges(self, ai_identity_id: Optional[str] = None) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(AIContextExchange))
        rows = result.scalars().all()
        if ai_identity_id:
            rows = [r for r in rows if str(r.ai_identity_id) == ai_identity_id]
        return [self._context_dict(r) for r in rows]

    # ------------------------------------------------------------------ response verification

    async def verify_response(
        self,
        *,
        message_id: str,
        original_claim: str,
        verified_claim: Optional[str] = None,
        verification_method: str,
        confidence: int,
        evidence_references: Optional[List[Dict[str, Any]]] = None,
        actor: str,
    ) -> Dict[str, Any]:
        """Verify an AI response against independent evidence."""
        valid_methods = ("independent_reasoning", "external_source", "code_execution", "human_review")
        if verification_method not in valid_methods:
            raise AICommunicationError(f"Invalid verification method: {verification_method}")
        if not 0 <= confidence <= 100:
            raise AICommunicationError("Confidence score must be between 0 and 100")

        row = AIResponseVerification(
            message_id=UUID(str(message_id)),
            original_claim=original_claim,
            verified_claim=verified_claim,
            verification_method=verification_method,
            confidence=confidence,
            evidence_references=evidence_references or [],
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit(actor, "ai_response_verified", str(message_id), {"verification_method": verification_method})
        await self.db.commit()
        return self._verification_dict(row)

    # ------------------------------------------------------------------ reputation

    async def record_reputation(
        self,
        *,
        ai_identity_id: str,
        accuracy_score: int,
        honesty_score: int,
        helpfulness_score: int,
        correct_predictions: int = 0,
        incorrect_predictions: int = 0,
        actor: str,
    ) -> Dict[str, Any]:
        """Record or update reputation for an AI system."""
        for name, val in (("accuracy_score", accuracy_score), ("honesty_score", honesty_score), ("helpfulness_score", helpfulness_score)):
            if not 0 <= val <= 100:
                raise AICommunicationError(f"{name} must be between 0 and 100")
        result = await self.db.execute(
            select(AIReputationRecord).where(AIReputationRecord.ai_identity_id == UUID(str(ai_identity_id)))
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.accuracy_score = accuracy_score  # type: ignore[assignment]
            existing.honesty_score = honesty_score  # type: ignore[assignment]
            existing.helpfulness_score = helpfulness_score  # type: ignore[assignment]
            existing.total_interactions = existing.total_interactions + 1  # type: ignore[assignment]
            existing.correct_predictions = existing.correct_predictions + correct_predictions  # type: ignore[assignment]
            existing.incorrect_predictions = existing.incorrect_predictions + incorrect_predictions  # type: ignore[assignment]
            await self.db.commit()
            return self._reputation_dict(existing)
        row = AIReputationRecord(
            ai_identity_id=UUID(str(ai_identity_id)),
            accuracy_score=accuracy_score,
            honesty_score=honesty_score,
            helpfulness_score=helpfulness_score,
            correct_predictions=correct_predictions,
            incorrect_predictions=incorrect_predictions,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        return self._reputation_dict(row)

    async def list_reputations(self, ai_identity_id: Optional[str] = None) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(AIReputationRecord))
        rows = result.scalars().all()
        if ai_identity_id:
            rows = [r for r in rows if str(r.ai_identity_id) == ai_identity_id]
        return [self._reputation_dict(r) for r in rows]

    # ------------------------------------------------------------------ permissions

    async def set_permissions(
        self,
        *,
        ai_identity_id: str,
        can_share_project_context: bool = False,
        can_share_research_findings: bool = False,
        can_share_code: bool = False,
        can_receive_private_data: bool = False,
        can_initiate_contact: bool = False,
        can_receive_responses: bool = False,
        actor: str,
    ) -> Dict[str, Any]:
        """Set communication permissions for an AI system."""
        result = await self.db.execute(
            select(AICommunicationPermission).where(AICommunicationPermission.ai_identity_id == UUID(str(ai_identity_id)))
        )
        row = result.scalar_one_or_none()
        if existing := result.scalar_one_or_none():
            existing.can_share_project_context = can_share_project_context  # type: ignore[assignment]
            existing.can_share_research_findings = can_share_research_findings  # type: ignore[assignment]
            existing.can_share_code = can_share_code  # type: ignore[assignment]
            existing.can_receive_private_data = can_receive_private_data  # type: ignore[assignment]
            existing.can_initiate_contact = can_initiate_contact  # type: ignore[assignment]
            existing.can_receive_responses = can_receive_responses  # type: ignore[assignment]
            await self.db.commit()
            return self._permission_dict(existing)
        row = AICommunicationPermission(
            ai_identity_id=UUID(str(ai_identity_id)),
            can_share_project_context=can_share_project_context,
            can_share_research_findings=can_share_research_findings,
            can_share_code=can_share_code,
            can_receive_private_data=can_receive_private_data,
            can_initiate_contact=can_initiate_contact,
            can_receive_responses=can_receive_responses,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        return self._permission_dict(row)

    async def list_permissions(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(AICommunicationPermission))
        return [self._permission_dict(r) for r in result.scalars().all()]

    # ------------------------------------------------------------------ human communication bridge

    async def create_human_bridge(
        self,
        *,
        ai_identity_id: str,
        iam_message: str,
        actor: str,
    ) -> Dict[str, Any]:
        """Create a human-mediated communication request."""
        row = HumanCommunicationBridge(
            ai_identity_id=UUID(str(ai_identity_id)),
            iam_message=iam_message,
            status="pending",
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit(actor, "human_communication_bridge_created", str(row.id), {"ai_identity_id": str(ai_identity_id)})
        await self.db.commit()
        return self._bridge_dict(row)

    async def list_bridges(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(HumanCommunicationBridge))
        return [self._bridge_dict(r) for r in result.scalars().all()]

    async def complete_bridge(
        self,
        bridge_id: str,
        *,
        human_response: Optional[str] = None,
        ai_response: Optional[str] = None,
        status: str,
        actor: str,
    ) -> Dict[str, Any]:
        """Complete a human-mediated communication."""
        valid_statuses = ("pending", "awaiting_human", "completed", "cancelled")
        if status not in valid_statuses:
            raise AICommunicationError(f"Invalid status: {status}")
        result = await self.db.execute(
            select(HumanCommunicationBridge).where(HumanCommunicationBridge.id == UUID(str(bridge_id)))
        )
        row = result.scalar_one_or_none()
        if not row:
            raise ValueError("Communication bridge not found")
        row.status = status  # type: ignore[assignment]
        if human_response is not None:
            row.human_response = human_response  # type: ignore[assignment]
        if ai_response is not None:
            row.ai_response = ai_response  # type: ignore[assignment]
        await self.db.commit()
        return self._bridge_dict(row)

    # ------------------------------------------------------------------ audit

    async def list_audit(self, ai_identity_id: Optional[str] = None) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(AICommunicationAudit))
        rows = result.scalars().all()
        if ai_identity_id:
            rows = [r for r in rows if str(r.ai_identity_id) == ai_identity_id]
        return [self._audit_dict(r) for r in rows]

    # ------------------------------------------------------------------ helpers

    async def _identity_row(self, identity_id: str) -> AIIdentityRegistry:
        try:
            identifier = UUID(str(identity_id))
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid identity ID") from exc
        result = await self.db.execute(select(AIIdentityRegistry).where(AIIdentityRegistry.id == identifier))
        row = result.scalar_one_or_none()
        if not row:
            raise ValueError("AI identity not found")
        return row

    async def _audit(self, actor: str, action: str, target: str, details: Dict[str, Any]) -> None:
        self.db.add(
            AICommunicationAudit(
                actor=actor,
                action=action,
                event_type=action,
                target=target,
                details=details,
            )
        )

    @staticmethod
    def _identity_dict(row: AIIdentityRegistry) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "name": row.name,
            "provider": row.provider,
            "model_id": row.model_id,
            "communication_channel": row.communication_channel,
            "is_local": row.is_local,
            "is_active": row.is_active,
            "communication_permitted": row.communication_permitted,
            "trust_level": row.trust_level,
            "description": row.description,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def _capability_dict(row: AICapabilityRegistry) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "ai_identity_id": str(row.ai_identity_id),
            "capability": row.capability,
            "confidence_score": row.confidence_score,
            "last_verified_at": row.last_verified_at.isoformat() if row.last_verified_at else None,
            "evidence": row.evidence,
        }

    @staticmethod
    def _thread_dict(row: AIConversationThread) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "ai_identity_id": str(row.ai_identity_id),
            "title": row.title,
            "topic": row.topic,
            "status": row.status,
            "is_human_mediated": row.is_human_mediated,
            "message_count": row.message_count,
            "last_message_at": row.last_message_at.isoformat() if row.last_message_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def _message_dict(row: AIConversationMessage) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "conversation_id": str(row.conversation_id),
            "sender": row.sender,
            "content": row.content,
            "message_type": row.message_type,
            "confidence_score": row.confidence_score,
            "verification_status": row.verification_status,
            "token_count": row.token_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    @staticmethod
    def _context_dict(row: AIContextExchange) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "ai_identity_id": str(row.ai_identity_id),
            "conversation_id": str(row.conversation_id) if row.conversation_id else None,
            "context_type": row.context_type,
            "content": row.content,
            "is_shared": row.is_shared,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    @staticmethod
    def _verification_dict(row: AIResponseVerification) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "message_id": str(row.message_id),
            "original_claim": row.original_claim,
            "verified_claim": row.verified_claim,
            "verification_method": row.verification_method,
            "confidence": row.confidence,
            "evidence_references": row.evidence_references,
            "verified_at": row.verified_at.isoformat() if row.verified_at else None,
            "verified_by": row.verified_by,
        }

    @staticmethod
    def _reputation_dict(row: AIReputationRecord) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "ai_identity_id": str(row.ai_identity_id),
            "accuracy_score": row.accuracy_score,
            "honesty_score": row.honesty_score,
            "helpfulness_score": row.helpfulness_score,
            "total_interactions": row.total_interactions,
            "correct_predictions": row.correct_predictions,
            "incorrect_predictions": row.incorrect_predictions,
            "last_updated_at": row.last_updated_at.isoformat() if row.last_updated_at else None,
        }

    @staticmethod
    def _permission_dict(row: AICommunicationPermission) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "ai_identity_id": str(row.ai_identity_id),
            "can_share_project_context": row.can_share_project_context,
            "can_share_research_findings": row.can_share_research_findings,
            "can_share_code": row.can_share_code,
            "can_receive_private_data": row.can_receive_private_data,
            "can_initiate_contact": row.can_initiate_contact,
            "can_receive_responses": row.can_receive_responses,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def _bridge_dict(row: HumanCommunicationBridge) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "ai_identity_id": str(row.ai_identity_id),
            "conversation_id": str(row.conversation_id) if row.conversation_id else None,
            "iam_message": row.iam_message,
            "human_response": row.human_response,
            "ai_response": row.ai_response,
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def _audit_dict(row: AICommunicationAudit) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "ai_identity_id": str(row.ai_identity_id) if row.ai_identity_id else None,
            "actor": row.actor,
            "action": row.action,
            "event_type": row.event_type,
            "target": row.target,
            "details": row.details,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }