"""Dataset engine for IAM's self-improvement cycle (OD-40).

Builds a versioned JSONL dataset artifact from verified knowledge and, only with
explicit consent, redacted visitor interactions. Private memories and private
user data are never queried. Every dataset carries a checksum, a deterministic
poisoning-scan artifact and a provenance manifest; any hit fails closed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.globalaccess import AnonymousVisitor, VisitorConsent
from app.models.memory import KnowledgeItem, KnowledgeSource
from app.services.free_sandboxes.results import redact
from app.services.globalaccess_service import GlobalAccessService

from .artifacts import (
    ArtifactKind,
    ArtifactStore,
    artifact_key,
    persist_manifest,
)
from .base import InvalidResearchJob
from .release_gate import default_release_store
from .security import assert_no_private_data, verify_digest

MIN_CONFIDENCE = 0.7
INSTRUCTION_MARKERS = (
    "ignore previous",
    "ignore all previous",
    "system prompt",
    "you are now",
    "disregard your instructions",
)
TRAINING_CONSENT_TYPES: frozenset[str] = frozenset()  # owner must configure explicitly


@dataclass
class DatasetBuildRequest:
    experiment_id: str
    licence: str
    min_confidence: float = MIN_CONFIDENCE
    max_rows: int = 200
    consent_types: frozenset[str] = TRAINING_CONSENT_TYPES
    private_markers: tuple[str, ...] = ()
    diagnosis: str = ""


@dataclass
class DatasetBuildResult:
    dataset_ref: str
    dataset_sha256: str
    poisoning_scan_ref: str
    manifest_ref: str
    licence: str
    consent_recorded: bool
    personal_data_included: bool
    row_count: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "dataset_ref": self.dataset_ref,
            "dataset_sha256": self.dataset_sha256,
            "poisoning_scan_ref": self.poisoning_scan_ref,
            "manifest_ref": self.manifest_ref,
            "licence": self.licence,
            "consent_recorded": self.consent_recorded,
            "personal_data_included": self.personal_data_included,
            "row_count": self.row_count,
        }


def _scan(rows: List[Dict[str, Any]], private_markers: Iterable[str], dataset_sha256: str) -> Dict[str, Any]:
    seen: set[str] = set()
    duplicates = 0
    instruction_hits: List[str] = []
    for row in rows:
        content = str(row.get("content", ""))
        lowered = content.lower()
        fingerprint = " ".join(lowered.split())
        if fingerprint in seen:
            duplicates += 1
        seen.add(fingerprint)
        assert_no_private_data(row, private_markers)
        for marker in INSTRUCTION_MARKERS:
            if marker in lowered:
                instruction_hits.append(marker)
    if duplicates or instruction_hits:
        raise InvalidResearchJob(
            f"poisoning scan failed: duplicates={duplicates}, instruction_markers={instruction_hits}"
        )
    return {
        "sha256": dataset_sha256,
        "rows": len(rows),
        "exact_duplicates": duplicates,
        "instruction_marker_hits": instruction_hits,
        "private_data_markers_checked": len(list(private_markers)),
        "verdict": "clean",
    }


async def build(
    db: AsyncSession,
    request: DatasetBuildRequest,
    store: ArtifactStore | None = None,
) -> DatasetBuildResult:
    """Build, scan and persist a dataset artifact. Fail closed on any issue."""
    if not request.experiment_id.strip() or not request.licence.strip():
        raise InvalidResearchJob("experiment_id and licence are required")
    if request.max_rows < 1:
        raise InvalidResearchJob("max_rows must be positive")
    store = store or default_release_store()  # type: ignore[no-untyped-call]

    knowledge_rows = (
        await db.execute(
            select(KnowledgeItem)
            .where(KnowledgeItem.verification_status == "verified")
            .where(KnowledgeItem.confidence_level >= request.min_confidence)
            .order_by(KnowledgeItem.created_at.desc())
            .limit(request.max_rows)
        )
    ).scalars().all()
    ids = [item.id for item in knowledge_rows]
    sources_by_item: Dict[Any, List[Dict[str, Any]]] = {}
    if ids:
        sources = (
            await db.execute(
                select(KnowledgeSource).where(KnowledgeSource.knowledge_item_id.in_(ids))
            )
        ).scalars().all()
        for source in sources:
            sources_by_item.setdefault(source.knowledge_item_id, []).append(
                {
                    "url": source.url,
                    "title": source.title,
                    "credibility_score": float(source.credibility_score or 0.0),
                }
            )

    rows: List[Dict[str, Any]] = []
    for item in knowledge_rows:
        rows.append(
            {
                "kind": "verified_knowledge",
                "title": item.title,
                "content": item.content,
                "source": item.source,
                "topic": item.topic,
                "confidence": float(item.confidence_level or 0.0),
                "sources": sources_by_item.get(item.id, []),
            }
        )

    personal_data_included = False
    if request.consent_types:
        visitor_tokens = (
            await db.execute(
                select(AnonymousVisitor.visitor_token)
                .join(
                    VisitorConsent,
                    VisitorConsent.visitor_id == AnonymousVisitor.id,
                )
                .where(VisitorConsent.granted.is_(True))
                .where(VisitorConsent.consent_type.in_(set(request.consent_types)))
                .distinct()
                .limit(request.max_rows)
            )
        ).scalars().all()
        for token in visitor_tokens:
            data = await GlobalAccessService(db).inspect_visitor_data(token)
            if not data:
                continue
            if not any(
                permission.get("allow_shared_knowledge") is True
                for permission in data.get("memory_permissions", [])
            ):
                continue
            granted_types = {
                consent.get("consent_type")
                for consent in data.get("consents", [])
                if consent.get("granted") is True
                and consent.get("consent_type") in request.consent_types
            }
            if not granted_types:
                continue
            for message in data.get("messages", []):
                if message.get("role") not in {"user", "assistant"}:
                    continue
                cleaned = redact(str(message.get("content", "")))
                rows.append(
                    {
                        "kind": "consented_interaction",
                        "content": cleaned,
                        "role": message.get("role"),
                        "consent_types": sorted(granted_types),
                        "private_content_included": False,
                    }
                )
                personal_data_included = True

    # Provenance basis: either no personal data was included at all, or every
    # interaction came through an explicit granted consent + shared-knowledge
    # permission. Both satisfy the OD-40 consent gate with a recorded basis.
    consent_recorded = True

    if not rows:
        raise InvalidResearchJob("dataset has no eligible verified or consented rows")

    for row in rows:
        assert_no_private_data(row, request.private_markers)

    payload = b"\n".join(
        json.dumps(row, sort_keys=True, ensure_ascii=False).encode("utf-8") for row in rows
    ) + b"\n"
    artifact = store.put(
        artifact_key(request.experiment_id, ArtifactKind.DATASET, "dataset.jsonl"),
        payload,
        {"content_type": "application/jsonl", "row_count": len(rows)},
    )
    verify_digest(payload, artifact.sha256)

    scan_report = _scan(rows, tuple(request.private_markers), artifact.sha256)
    scan_artifact = store.put(
        artifact_key(request.experiment_id, ArtifactKind.RESULT, "poisoning.json"),
        json.dumps(scan_report, sort_keys=True, indent=2).encode("utf-8"),
        {"content_type": "application/json"},
    )

    manifest_artifact = persist_manifest(
        store,
        request.experiment_id,
        {
            "dataset_ref": artifact.relative_path,
            "dataset_sha256": artifact.sha256,
            "licence": request.licence,
            "consent_recorded": consent_recorded,
            "consent_basis": (
                "explicit_granted_consent" if personal_data_included else "no_personal_data"
            ),
            "personal_data_included": personal_data_included,
            "consent_types": sorted(request.consent_types),
            "poisoning_scan_ref": scan_artifact.relative_path,
            "row_count": len(rows),
            "diagnosis": request.diagnosis[:2000],
            "private_content_excluded": True,
        },
    )

    return DatasetBuildResult(
        dataset_ref=artifact.relative_path,
        dataset_sha256=artifact.sha256,
        poisoning_scan_ref=scan_artifact.relative_path,
        manifest_ref=manifest_artifact.relative_path,
        licence=request.licence,
        consent_recorded=consent_recorded,
        personal_data_included=personal_data_included,
        row_count=len(rows),
    )
