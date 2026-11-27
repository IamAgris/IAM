"""External threat-intel ingestion, dependency mapping, DLP and rotation policy.

§2.6. Defensive only: no scanning, exploitation or offensive capability
(OD-16/OD-34). Feeds are allowlisted and fetched through the egress gateway.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.iics import IICSAdvisory, IICSDLPEvent

DLP_RULES = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("api_key", re.compile(r"(?i)\b(?:sk-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9]{20,})\b")),
    ("bearer_token", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._-]{12,}")),
    ("credential_assignment", re.compile(r"(?i)\b(?:password|api[_-]?key|secret)\s*[:=]\s*\S+")),
)


@dataclass(frozen=True)
class CredentialRef:
    """A secret *reference* — never the secret itself."""

    reference: str
    rotated_at: Optional[str] = None
    owner: str = "iam"


class AdvisoryIngestor:
    """Normalise OSV/NVD-shaped advisories and deduplicate by CVE ID."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def parse(payload: Mapping[str, Any], source: str = "osv") -> List[Dict[str, Any]]:
        advisories: List[Dict[str, Any]] = []
        if source == "osv":
            entries = payload.get("vulns") or []
            for entry in entries:
                cve = str(entry.get("id") or "")
                if not cve:
                    continue
                specifics = dict(entry.get("database_specific") or {})
                severity = str(specifics.get("severity") or "UNKNOWN").upper()
                affected = [
                    str((item.get("package") or {}).get("name") or "")
                    for item in (entry.get("affected") or [])
                ]
                advisories.append(
                    {
                        "cve_id": cve,
                        "source": source,
                        "severity": severity,
                        "published": str(entry.get("published") or ""),
                        "url": next(
                            (
                                str(ref.get("url"))
                                for ref in (entry.get("references") or [])
                                if ref.get("url")
                            ),
                            "",
                        ),
                        "summary": str(entry.get("summary") or ""),
                        "affected": [name for name in affected if name],
                        "evidence": {"source": source, "raw_id": cve},
                    }
                )
        elif source == "nvd":
            for entry in payload.get("vulnerabilities") or []:
                cve_data = dict(entry.get("cve") or {})
                cve = str(cve_data.get("id") or "")
                if not cve:
                    continue
                descriptions = cve_data.get("descriptions") or []
                summary = next(
                    (str(d.get("value")) for d in descriptions if d.get("value")), ""
                )
                metrics = cve_data.get("metrics") or {}
                severity = "UNKNOWN"
                for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                    values = metrics.get(key) or []
                    if values and isinstance(values[0], Mapping):
                        data = dict(values[0].get("cvssData") or {})
                        severity = str(
                            data.get("baseSeverity")
                            or values[0].get("baseSeverity")
                            or "UNKNOWN"
                        ).upper()
                        break
                advisories.append(
                    {
                        "cve_id": cve,
                        "source": source,
                        "severity": severity,
                        "published": str(cve_data.get("published") or ""),
                        "url": "",
                        "summary": summary,
                        "affected": [],
                        "evidence": {"source": source, "raw_id": cve},
                    }
                )
        return advisories

    async def ingest(self, payload: Mapping[str, Any], source: str = "osv") -> Dict[str, Any]:
        parsed = self.parse(payload, source)
        inserted = 0
        skipped = 0
        for item in parsed:
            result = await self.db.execute(
                select(IICSAdvisory).where(IICSAdvisory.cve_id == item["cve_id"])
            )
            if result.scalar_one_or_none():
                skipped += 1
                continue
            self.db.add(IICSAdvisory(**item))
            inserted += 1
        if inserted:
            await self.db.commit()
        return {"inserted": inserted, "skipped": skipped, "source": source}

    async def list(self, limit: int = 100) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(IICSAdvisory).order_by(IICSAdvisory.created_at.desc()).limit(limit)
        )
        return [
            {
                "cve_id": row.cve_id,
                "source": row.source,
                "severity": row.severity,
                "published": row.published,
                "url": row.url,
                "summary": row.summary,
                "affected": list(row.affected or []),
            }
            for row in result.scalars().all()
        ]

    @staticmethod
    def map_dependencies(advisory: Mapping[str, Any], sbom: Mapping[str, Any]) -> List[str]:
        """Return SBOM component names affected by an advisory."""
        names = {
            str(component.get("name") or "").lower()
            for component in (sbom.get("components") or [])
            if isinstance(component, Mapping)
        }
        return sorted(
            {
                str(name).lower()
                for name in (advisory.get("affected") or [])
                if str(name).lower() in names
            }
        )


class DLPEngine:
    """Cross-channel content-level data-loss prevention."""

    @staticmethod
    def check(text: str, channel: str = "api") -> Dict[str, Any]:
        matched = [label for label, pattern in DLP_RULES if pattern.search(text or "")]
        allowed = not matched
        return {
            "allowed": allowed,
            "matched_labels": matched,
            "action": "allowed" if allowed else "blocked",
            "channel": channel,
        }

    @staticmethod
    async def record(
        db: AsyncSession, outcome: Mapping[str, Any], details: Optional[Mapping[str, Any]] = None
    ) -> Dict[str, Any]:
        if outcome.get("allowed"):
            return {"recorded": False}
        db.add(
            IICSDLPEvent(
                channel=str(outcome.get("channel") or "unknown"),
                matched_labels=list(outcome.get("matched_labels") or []),
                action=str(outcome.get("action") or "blocked"),
                details=dict(details or {}),
            )
        )
        await db.commit()
        return {"recorded": True}


class CredentialRotationPolicy:
    """Rotation scheduling for secret *references*, never secret values."""

    @staticmethod
    def due(
        credentials: List[CredentialRef], interval_days: int = 90, now: Optional[datetime] = None
    ) -> List[str]:
        moment = now or datetime.now(timezone.utc)
        due: List[str] = []
        for credential in credentials:
            if not credential.rotated_at:
                due.append(credential.reference)
                continue
            try:
                rotated = datetime.fromisoformat(str(credential.rotated_at).replace("Z", "+00:00"))
            except ValueError:
                due.append(credential.reference)
                continue
            if rotated.tzinfo is None:
                rotated = rotated.replace(tzinfo=timezone.utc)
            if rotated + timedelta(days=interval_days) <= moment:
                due.append(credential.reference)
        return due

    @staticmethod
    def due_from_vault(
        records: List[Mapping[str, Any]],
        now: Optional[datetime] = None,
    ) -> List[str]:
        """Map vault public records to rotation references (no secret values)."""
        refs = [
            CredentialRef(
                str(record.get("key_id") or record.get("id") or "unknown"),
                str(record.get("rotated_at") or record.get("updated_at") or ""),
                str(record.get("provider") or "iam"),
            )
            for record in records
        ]
        return CredentialRotationPolicy.due(refs, interval_days, now)
