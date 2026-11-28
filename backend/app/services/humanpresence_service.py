"""Human Public Presence Intelligence / PPIICE (OD-30).

Evidence-based research of publicly presented identity only. Never de-anonymise,
never touch private visitor memory or credentials, never infer sensitive traits,
and never present a public profile as proof of real-world identity.
"""

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.humanpresence import (
    IdentityMatch,
    PresenceClaim,
    PublicPerson,
    PublicProfile,
    PublicRelationship,
)
from app.models.security import AuditEvent

PROFILE_TYPES = {
    "personal_site", "professional_profile", "company_site", "publication",
    "news", "public_social", "community", "conference", "portfolio",
}
CLAIM_TYPES = {
    "role", "affiliation", "achievement", "publication", "interest",
    "public_statement", "project", "education", "award",
}
RELATIONSHIP_TYPES = {
    "affiliation", "collaboration", "public_partnership", "mentorship", "public_appearance",
}
SENSITIVE = re.compile(
    r"religio|health|medical|disab|sexual|orientation|politic|ethnic|race|biometric|"
    r"deanonym|real.identity|anonymous|password|credential|home.address|phone.number|"
    r"private.message|visitor.memory|stalk|harass",
    re.IGNORECASE,
)


class PresenceError(ValueError):
    pass


def _hash(data: Any) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _confidence(value: Any) -> float:
    result = float(value)
    if not 0 <= result <= 1:
        raise PresenceError("confidence must be between 0 and 1")
    return result


def _guard_sensitive(payload: Dict[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, default=str)
    if SENSITIVE.search(serialized):
        raise PresenceError(
            "request contains sensitive or private-identity information; "
            "public-presence research must not compile it"
        )


def _domains(evidence: Dict[str, Any]) -> set:  # type: ignore[type-arg]
    urls = re.findall(r"https?://[^\s\"']+", json.dumps(evidence, ensure_ascii=False))
    return {urlparse(url).netloc.lower() for url in urls if urlparse(url).netloc}


class HumanPresenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_person(self, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        payload = dict(payload)
        if payload.pop("deanonymize_target", False):
            raise PresenceError(
                "de-anonymisation is never permitted; only publicly presented identity may be researched"
            )
        _guard_sensitive(payload)
        name = str(payload.get("canonical_name") or "").strip()
        if not name:
            raise PresenceError("canonical_name is required")
        person = PublicPerson(
            canonical_name=name,
            internal_public_id=f"pub-{uuid.uuid4().hex}",
            notes=payload.get("notes"),
        )
        self.db.add(person)
        self.db.add(
            AuditEvent(
                event_type="public_person_created",
                actor=actor,
                target=person.internal_public_id,
                details={"name_length": len(name)},
            )
        )
        await self.db.commit()
        await self.db.refresh(person)
        return {**self.person_dict(person), "real_world_identity_proven": False}

    async def add_profile(self, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        _guard_sensitive(payload)
        person = await self._person(payload.get("person_id"))
        source_url = str(payload.get("source_url") or "")
        if not payload.get("source_name") or not source_url:
            raise PresenceError("source_name and source_url are required")
        profile_type = payload.get("profile_type", "personal_site")
        if profile_type not in PROFILE_TYPES:
            raise PresenceError("invalid profile type")
        status = payload.get("status", "self_reported")
        if status not in {"self_reported", "uncertain", "verified"}:
            raise PresenceError("profiles cannot be created as verified without cross-source review")
        domain = urlparse(source_url).netloc.lower()
        if not domain:
            raise PresenceError("source_url must include a domain")
        content = {
            "source_name": payload["source_name"],
            "source_url": source_url,
            "stated_name": payload.get("stated_name"),
            "role": payload.get("role"),
            "organization": payload.get("organization"),
            "bio": payload.get("bio"),
        }
        profile = PublicProfile(
            person_id=person.id,
            source_name=payload["source_name"],
            source_url=source_url,
            source_domain=domain,
            profile_type=profile_type,
            stated_name=payload.get("stated_name"),
            role=payload.get("role"),
            organization=payload.get("organization"),
            bio=payload.get("bio"),
            interests=payload.get("interests") or [],
            status=status,
            confidence=_confidence(payload.get("confidence", 0.4)),
            content_hash=_hash(content),
            published_at=payload.get("published_at"),
            retrieved_at=payload.get("retrieved_at") or datetime.now(timezone.utc),
        )
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return {**self.profile_dict(profile), "untrusted": True}

    async def verify_profile(self, profile_id: str, actor: str = "sdk") -> Dict[str, Any]:
        profile = await self._profile(profile_id)
        result = await self.db.execute(
            select(PublicProfile).where(PublicProfile.person_id == profile.person_id)
        )
        domains = {p.source_domain for p in result.scalars().all()}
        if len(domains) < 2:
            raise PresenceError(
                "at least two independent public source domains are required before a profile can be verified"
            )
        profile.status = "verified"  # type: ignore[assignment]
        profile.confidence = max(profile.confidence, 0.8)  # type: ignore[arg-type]
        self.db.add(
            AuditEvent(
                event_type="public_profile_verified",
                actor=actor,
                target=str(profile.id),
                details={"independent_domains": len(domains)},
            )
        )
        await self.db.commit()
        return {
            "profile_id": profile_id,
            "status": "verified",
            "independent_domains": len(domains),
            "claim": "public_profile_equivalence_not_real_world_identity",
        }

    async def add_claim(self, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        _guard_sensitive(payload)
        person = await self._person(payload.get("person_id"))
        claim_type = str(payload.get("claim_type") or "")
        if claim_type not in CLAIM_TYPES:
            raise PresenceError("unsupported claim type")
        status = payload.get("status", "uncertain")
        if status not in {"verified", "self_reported", "uncertain"}:
            raise PresenceError("invalid claim status")
        claim = PresenceClaim(
            person_id=person.id,
            profile_id=payload.get("profile_id"),
            claim_type=claim_type,
            value=payload.get("value") or {},
            status=status,
            confidence=_confidence(payload.get("confidence", 0.5)),
            source_url=payload.get("source_url"),
            first_seen_at=payload.get("first_seen_at"),
            last_seen_at=payload.get("last_seen_at") or datetime.now(timezone.utc),
            supersedes_id=payload.get("supersedes_id"),
        )
        self.db.add(claim)
        await self.db.commit()
        await self.db.refresh(claim)
        return {**self.claim_dict(claim), "untrusted": True}

    async def match_people(
        self,
        person_id: str,
        other_id: str,
        evidence: Dict[str, Any],
        confidence: Any,
        actor: str = "sdk",
    ) -> Dict[str, Any]:
        _guard_sensitive(evidence)
        if person_id == other_id:
            raise PresenceError("cannot match a person to themselves")
        await self._person(person_id)
        await self._person(other_id)
        if not evidence:
            raise PresenceError("evidence is required; profiles are never merged automatically")
        score = _confidence(confidence)
        independent = _domains(evidence)
        result = "same" if score >= 0.9 and len(independent) >= 2 else "uncertain"
        match = IdentityMatch(
            person_id=person_id,
            other_person_id=other_id,
            evidence=evidence,
            confidence=score,
            result=result,
        )
        self.db.add(match)
        self.db.add(
            AuditEvent(
                event_type="public_identity_match_recorded",
                actor=actor,
                target=person_id,
                details={"other": other_id, "result": result},
            )
        )
        await self.db.commit()
        await self.db.refresh(match)
        return {
            "id": str(match.id),
            "result": result,
            "confidence": score,
            "independent_domains": len(independent),
            "claim": "public_profile_equivalence_only",
            "note": "not proof of real-world identity",
        }

    async def add_relationship(self, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        _guard_sensitive(payload)
        person = await self._person(payload.get("person_id"))
        relation_type = payload.get("relationship_type")
        if relation_type not in RELATIONSHIP_TYPES:
            raise PresenceError("invalid relationship type")
        if not payload.get("organization_name") and not payload.get("related_person_id"):
            raise PresenceError("an organization or related person is required")
        if not payload.get("evidence"):
            raise PresenceError("public evidence is required for a relationship")
        relationship = PublicRelationship(
            person_id=person.id,
            related_person_id=payload.get("related_person_id"),
            organization_name=payload.get("organization_name"),
            relationship_type=relation_type,
            evidence=payload["evidence"],
            confidence=_confidence(payload.get("confidence", 0.5)),
        )
        self.db.add(relationship)
        await self.db.commit()
        await self.db.refresh(relationship)
        return {
            "id": str(relationship.id),
            "relationship_type": relation_type,
            "confidence": relationship.confidence,
        }

    async def correct_claim(
        self, claim_id: str, value: Dict[str, Any], reason: str, actor: str = "sdk"
    ) -> Dict[str, Any]:
        if not reason:
            raise PresenceError("a correction reason is required")
        original = await self._claim(claim_id)
        correction = PresenceClaim(
            person_id=original.person_id,
            profile_id=original.profile_id,
            claim_type=original.claim_type,
            value=value,
            status="uncertain",
            confidence=original.confidence,
            source_url=original.source_url,
            last_seen_at=datetime.now(timezone.utc),
            supersedes_id=original.id,
        )
        original.status = "corrected"  # type: ignore[assignment]
        self.db.add(correction)
        await self.db.commit()
        await self.db.refresh(correction)
        return {**self.claim_dict(correction), "original_preserved": True}

    async def research_public_page(
        self, person_id: str, url: str, actor: str = "sdk"
    ) -> Dict[str, Any]:
        """Inspect a permitted public page through UWAIE; store it as unverified."""
        await self._person(person_id)
        from app.services.uwaie_service import UWAIEService, UWAIEError

        try:
            inspected = await UWAIEService(self.db).inspect(url, actor)
        except UWAIEError as exc:
            raise PresenceError(str(exc)) from exc
        return await self.add_profile(
            {
                "person_id": person_id,
                "source_name": inspected.get("title") or urlparse(url).netloc,
                "source_url": url,
                "profile_type": "personal_site",
                "bio": inspected.get("text_preview", "")[:2000],
                "status": "uncertain",
                "confidence": 0.3,
            },
            actor,
        )

    async def profiles(self, person_id: str) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(PublicProfile).where(PublicProfile.person_id == person_id)
        )
        return [self.profile_dict(p) for p in result.scalars().all()]

    async def claims(self, person_id: str) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(PresenceClaim).where(PresenceClaim.person_id == person_id)
        )
        return [self.claim_dict(c) for c in result.scalars().all()]

    async def timeline(self, person_id: str) -> Dict[str, Any]:
        profiles = await self.profiles(person_id)
        claims = await self.claims(person_id)
        items = [
            {
                "kind": "profile",
                "date": p.get("published_at") or p.get("retrieved_at"),
                "source_url": p["source_url"],
                "status": p["status"],
                "summary": p.get("role") or p.get("stated_name") or p["source_name"],
            }
            for p in profiles
        ] + [
            {
                "kind": "claim",
                "date": c.get("last_seen_at"),
                "source_url": c.get("source_url"),
                "status": c["status"],
                "summary": f"{c['claim_type']}: {c['value']}",
            }
            for c in claims
        ]
        items.sort(key=lambda item: item["date"] or "")
        return {"person_id": person_id, "items": items, "untrusted": True}

    async def people(self, name: Optional[str] = None) -> List[Dict[str, Any]]:
        query = select(PublicPerson)
        if name:
            query = query.where(PublicPerson.canonical_name.ilike(f"%{name}%"))
        result = await self.db.execute(query.limit(100))
        return [self.person_dict(p) for p in result.scalars().all()]

    async def matches(self, person_id: str) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(IdentityMatch).where(IdentityMatch.person_id == person_id)
        )
        return [
            {
                "id": str(m.id),
                "other_person_id": str(m.other_person_id),
                "result": m.result,
                "confidence": m.confidence,
            }
            for m in result.scalars().all()
        ]

    @staticmethod
    def boundaries() -> Dict[str, Any]:
        return {
            "claim": "public_presence_not_private_identity",
            "rules": [
                "public_information_only", "no_login_or_paywall_bypass",
                "no_deanonymisation", "no_sensitive_characteristic_inference",
                "no_visitor_memory_or_credentials", "public_profile_is_not_identity_proof",
                "evidence_dated_traceable_correctable", "no_harassment_or_stalking",
            ],
        }

    async def _person(self, person_id: Any) -> PublicPerson:
        result = await self.db.execute(
            select(PublicPerson).where(PublicPerson.id == person_id)
        )
        person = result.scalar_one_or_none()
        if not person:
            raise PresenceError("person not found")
        return person

    async def _profile(self, profile_id: str) -> PublicProfile:
        result = await self.db.execute(
            select(PublicProfile).where(PublicProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise PresenceError("profile not found")
        return profile

    async def _claim(self, claim_id: str) -> PresenceClaim:
        result = await self.db.execute(
            select(PresenceClaim).where(PresenceClaim.id == claim_id)
        )
        claim = result.scalar_one_or_none()
        if not claim:
            raise PresenceError("claim not found")
        return claim

    @staticmethod
    def person_dict(person: PublicPerson) -> Dict[str, Any]:
        return {
            "id": str(person.id),
            "canonical_name": person.canonical_name,
            "internal_public_id": person.internal_public_id,
            "deanonymized": person.deanonymized,
            "created_at": person.created_at.isoformat() if person.created_at else None,
        }

    @staticmethod
    def profile_dict(profile: PublicProfile) -> Dict[str, Any]:
        return {
            "id": str(profile.id),
            "person_id": str(profile.person_id),
            "source_name": profile.source_name,
            "source_url": profile.source_url,
            "source_domain": profile.source_domain,
            "profile_type": profile.profile_type,
            "stated_name": profile.stated_name,
            "role": profile.role,
            "organization": profile.organization,
            "interests": profile.interests,
            "status": profile.status,
            "confidence": profile.confidence,
            "published_at": profile.published_at.isoformat() if profile.published_at else None,
        }

    @staticmethod
    def claim_dict(claim: PresenceClaim) -> Dict[str, Any]:
        return {
            "id": str(claim.id),
            "person_id": str(claim.person_id),
            "profile_id": str(claim.profile_id) if claim.profile_id else None,
            "claim_type": claim.claim_type,
            "value": claim.value,
            "status": claim.status,
            "confidence": claim.confidence,
            "source_url": claim.source_url,
            "supersedes_id": str(claim.supersedes_id) if claim.supersedes_id else None,
        }
