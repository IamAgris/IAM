"""AI Assistant Interoperability and Technology Learning Lab (OD-28).

Internal research only. Study public documentation, use official integration
interfaces, then reproduce capabilities independently. IAM must not access
private reasoning/models, copy vendor identities, or become dependent on them.
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assistantlab import (
    AssistantAdapter,
    AssistantResearchNote,
    AssistantSystem,
    CapabilityComparison,
    ReplicationExperiment,
)
from app.models.security import AuditEvent

TOPICS = {
    "speech_recognition", "natural_language_understanding", "wake_word",
    "speech_synthesis", "intent_execution", "context_dialogue", "device_discovery",
    "multimodal", "accessibility", "multilingual", "local_vs_cloud",
    "privacy_permissions", "error_handling", "interruption",
}
INTERFACE_TYPES = {
    "official_skill", "app_intents", "shortcuts", "automation_studio",
    "official_api", "documentation_only",
}
FORBIDDEN = re.compile(
    r"private.model|internal.reasoning|proprietary.weight|impersonat|api.key|"
    r"secret|password|credential.value|leaked|stolen|bypass",
    re.IGNORECASE,
)


class LabError(ValueError):
    pass


def _guard_public(payload: Dict[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, default=str)
    if FORBIDDEN.search(serialized):
        raise LabError(
            "only public research and officially permitted interfaces are allowed; "
            "private models, credentials and impersonation are rejected"
        )


class AssistantLabService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_system(self, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        _guard_public(payload)
        for field in ("name", "vendor", "official_docs_url"):
            if not payload.get(field):
                raise LabError(f"{field} is required")
        if not urlparse(payload["official_docs_url"]).netloc:
            raise LabError("official_docs_url must be a valid URL")
        existing = await self.db.execute(
            select(AssistantSystem).where(AssistantSystem.name == payload["name"])
        )
        if existing.scalar_one_or_none():
            raise LabError("assistant system already registered")
        system = AssistantSystem(
            name=payload["name"],
            vendor=payload["vendor"],
            official_docs_url=payload["official_docs_url"],
            integration_method=payload.get("integration_method", "official_interface_only"),
            public_capabilities=payload.get("public_capabilities") or [],
            terms_url=payload.get("terms_url"),
        )
        self.db.add(system)
        self.db.add(
            AuditEvent(
                event_type="assistant_system_registered",
                actor=actor,
                target=system.name,
                details={"vendor": system.vendor, "level": "study"},
            )
        )
        await self.db.commit()
        await self.db.refresh(system)
        return {**self.system_dict(system), "internal_feature": True}

    async def systems(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(AssistantSystem).order_by(AssistantSystem.name))
        return [self.system_dict(s) for s in result.scalars().all()]

    async def add_note(self, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        _guard_public(payload)
        system = await self._system(payload.get("assistant_id"))
        topic = payload.get("topic")
        if topic not in TOPICS:
            raise LabError("unsupported research topic")
        if not payload.get("observation") or not payload.get("source_url"):
            raise LabError("observation and source_url are required")
        status = payload.get("status", "observation")
        if status not in {"observation", "verified", "uncertain"}:
            raise LabError("invalid note status")
        if status == "verified":
            source_host = urlparse(payload["source_url"]).netloc.lower()
            docs_host = urlparse(system.official_docs_url).netloc.lower()
            if source_host != docs_host:
                raise LabError("verified notes require an official documentation source")
        note = AssistantResearchNote(
            assistant_id=system.id,
            topic=topic,
            observation=payload["observation"],
            source_url=payload["source_url"],
            source_date=payload.get("source_date"),
            confidence=float(payload.get("confidence", 0.5)),
            status=status,
        )
        if not 0 <= note.confidence <= 1:
            raise LabError("confidence must be between 0 and 1")
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        return self.note_dict(note)

    async def notes(self, assistant_id: str, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        query = select(AssistantResearchNote).where(AssistantResearchNote.assistant_id == assistant_id)
        if topic:
            query = query.where(AssistantResearchNote.topic == topic)
        result = await self.db.execute(query.order_by(AssistantResearchNote.created_at.desc()))
        return [self.note_dict(n) for n in result.scalars().all()]

    async def register_adapter(self, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        payload = dict(payload)
        # The field name is not a credential value; the adapter stores no secret.
        auth_method = payload.pop("auth_method", "operator_provided_credential")
        _guard_public(payload)
        system = await self._system(payload.get("assistant_id"))
        interface_type = payload.get("interface_type")
        if interface_type not in INTERFACE_TYPES:
            raise LabError("invalid interface type")
        if not payload.get("name"):
            raise LabError("adapter name is required")
        adapter = AssistantAdapter(
            assistant_id=system.id,
            name=payload["name"],
            interface_type=interface_type,
            endpoint_template=payload.get("endpoint_template"),
            auth_method=auth_method,
            requires_credential=bool(payload.get("requires_credential", True)),
            is_active=False,
            notes=payload.get("notes"),
        )
        self.db.add(adapter)
        self.db.add(
            AuditEvent(
                event_type="assistant_adapter_registered",
                actor=actor,
                target=adapter.name,
                details={"interface": interface_type, "active": False},
            )
        )
        await self.db.commit()
        await self.db.refresh(adapter)
        return {**self.adapter_dict(adapter), "credentials_stored": False}

    async def adapters(self, assistant_id: str) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(AssistantAdapter).where(AssistantAdapter.assistant_id == assistant_id)
        )
        return [self.adapter_dict(a) for a in result.scalars().all()]

    async def start_experiment(self, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        _guard_public(payload)
        for field in ("capability", "hypothesis", "method"):
            if not payload.get(field):
                raise LabError(f"{field} is required")
        experiment = ReplicationExperiment(
            capability=payload["capability"],
            hypothesis=payload["hypothesis"],
            method=payload["method"],
            isolated=True,
            result="planned",
        )
        self.db.add(experiment)
        await self.db.commit()
        await self.db.refresh(experiment)
        return {**self.experiment_dict(experiment), "protected_core_unchanged": True}

    async def record_result(self, experiment_id: str, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        _guard_public(payload)
        experiment = await self._experiment(experiment_id)
        result = payload.get("result")
        if result not in {"running", "succeeded", "failed"}:
            raise LabError("invalid experiment result")
        evidence = payload.get("evidence") or {}
        if result in {"succeeded", "failed"} and not evidence:
            raise LabError("evidence is required for a concluded experiment")
        experiment.result = result
        experiment.evidence = evidence
        await self.db.commit()
        return self.experiment_dict(experiment)

    async def adopt_experiment(
        self, experiment_id: str, creator_approval_reference: str, actor: str = "creator"
    ) -> Dict[str, Any]:
        experiment = await self._experiment(experiment_id)
        if experiment.result != "succeeded":
            raise LabError("only a successful isolated experiment can be adopted")
        if not creator_approval_reference:
            raise LabError("creator approval reference is required; IAM cannot self-adopt")
        if not experiment.isolated:
            raise LabError("experiments must be isolated before adoption")
        experiment.production_adopted = True
        experiment.creator_approval_reference = creator_approval_reference
        self.db.add(
            AuditEvent(
                event_type="assistant_capability_adopted",
                actor=actor,
                target=experiment_id,
                details={"capability": experiment.capability, "isolated": True},
            )
        )
        await self.db.commit()
        return {
            "experiment_id": experiment_id,
            "production_adopted": True,
            "note": "IAM's own capability only; no vendor identity or protected-core change",
        }

    async def compare(self, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        _guard_public(payload)
        system = await self._system(payload.get("assistant_id"))
        rating = int(payload.get("rating", 0))
        if not 0 <= rating <= 5:
            raise LabError("rating must be between 0 and 5")
        if not payload.get("capability") or not payload.get("evidence_note"):
            raise LabError("capability and evidence_note are required")
        comparison = CapabilityComparison(
            assistant_id=system.id,
            capability=payload["capability"],
            rating=rating,
            evidence_note=payload["evidence_note"],
        )
        self.db.add(comparison)
        await self.db.commit()
        await self.db.refresh(comparison)
        return {
            "id": str(comparison.id),
            "assistant_id": str(comparison.assistant_id),
            "capability": comparison.capability,
            "rating": comparison.rating,
        }

    async def comparisons(self, capability: Optional[str] = None) -> List[Dict[str, Any]]:
        query = select(CapabilityComparison)
        if capability:
            query = query.where(CapabilityComparison.capability == capability)
        result = await self.db.execute(query.order_by(CapabilityComparison.rating.desc()))
        return [
            {
                "id": str(c.id),
                "assistant_id": str(c.assistant_id),
                "capability": c.capability,
                "rating": c.rating,
                "evidence_note": c.evidence_note,
            }
            for c in result.scalars().all()
        ]

    async def experiments(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(ReplicationExperiment).order_by(ReplicationExperiment.created_at.desc())
        )
        return [self.experiment_dict(e) for e in result.scalars().all()]

    async def status(self) -> Dict[str, Any]:
        systems = await self.db.execute(select(AssistantSystem))
        experiments = await self.db.execute(select(ReplicationExperiment))
        return {
            "assistant_systems": len(systems.scalars().all()),
            "experiments": len(experiments.scalars().all()),
            "levels": ["study", "integration", "independent_learning"],
            "internal_capability": True,
            "claim": "no_vendor_dependency",
        }

    @staticmethod
    def boundaries() -> Dict[str, Any]:
        return {
            "claim": "internal_research_not_user_feature",
            "levels": {
                "study": "public docs, research papers, permitted source code",
                "integration": "authorised connections through official interfaces",
                "independent_learning": "reproduce and improve inside IAM's own environment",
            },
            "prohibited": [
                "private_internal_reasoning", "proprietary_models", "impersonation",
                "credential_access", "vendor_dependency", "protected_core_change",
            ],
        }

    async def _system(self, assistant_id: Any) -> AssistantSystem:
        result = await self.db.execute(
            select(AssistantSystem).where(AssistantSystem.id == assistant_id)
        )
        system = result.scalar_one_or_none()
        if not system:
            raise LabError("assistant system not found")
        return system

    async def _experiment(self, experiment_id: str) -> ReplicationExperiment:
        result = await self.db.execute(
            select(ReplicationExperiment).where(ReplicationExperiment.id == experiment_id)
        )
        experiment = result.scalar_one_or_none()
        if not experiment:
            raise LabError("experiment not found")
        return experiment

    @staticmethod
    def system_dict(system: AssistantSystem) -> Dict[str, Any]:
        return {
            "id": str(system.id),
            "name": system.name,
            "vendor": system.vendor,
            "official_docs_url": system.official_docs_url,
            "integration_method": system.integration_method,
            "public_capabilities": system.public_capabilities,
            "status": system.status,
        }

    @staticmethod
    def note_dict(note: AssistantResearchNote) -> Dict[str, Any]:
        return {
            "id": str(note.id),
            "assistant_id": str(note.assistant_id),
            "topic": note.topic,
            "observation": note.observation,
            "source_url": note.source_url,
            "confidence": note.confidence,
            "status": note.status,
        }

    @staticmethod
    def adapter_dict(adapter: AssistantAdapter) -> Dict[str, Any]:
        return {
            "id": str(adapter.id),
            "assistant_id": str(adapter.assistant_id),
            "name": adapter.name,
            "interface_type": adapter.interface_type,
            "auth_method": adapter.auth_method,
            "requires_credential": adapter.requires_credential,
            "is_active": adapter.is_active,
        }

    @staticmethod
    def experiment_dict(experiment: ReplicationExperiment) -> Dict[str, Any]:
        return {
            "id": str(experiment.id),
            "capability": experiment.capability,
            "hypothesis": experiment.hypothesis,
            "method": experiment.method,
            "result": experiment.result,
            "evidence": experiment.evidence,
            "isolated": experiment.isolated,
            "production_adopted": experiment.production_adopted,
        }
