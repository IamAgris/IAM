"""Website Consent service (Privacy & Data Governance).

Tracks per-website cookie categories, consent status, data-retention
preferences and privacy-law applicability (GDPR, CCPA).
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.web_knowledge import WebsiteConsent, WebsiteKnowledge


class WebsiteConsentError(PermissionError):
    """Raised when a consent operation fails."""


class WebsiteConsentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _consent(self, consent_id: str) -> WebsiteConsent:
        try:
            identifier = UUID(str(consent_id))
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid consent ID") from exc
        result = await self.db.execute(
            select(WebsiteConsent).where(WebsiteConsent.id == identifier)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise ValueError("Website consent record not found")
        return row

    async def create(
        self,
        *,
        website_knowledge_id: str,
        cookie_categories: Optional[List[str]] = None,
        consent_status: str = "pending",
        data_retention_preference: Optional[str] = None,
        sensitive_info_classification: Optional[str] = None,
        gdpr_applicable: bool = False,
        ccpa_applicable: bool = False,
        actor: str,
    ) -> Dict[str, Any]:
        """Create or update consent for a website."""
        valid_statuses = ("pending", "accepted", "rejected", "withdrawn")
        if consent_status not in valid_statuses:
            raise WebsiteConsentError(f"Invalid consent status: {consent_status}")

        # Verify the website knowledge exists
        wk_result = await self.db.execute(
            select(WebsiteKnowledge).where(WebsiteKnowledge.id == UUID(str(website_knowledge_id)))
        )
        if not wk_result.scalar_one_or_none():
            raise ValueError("Website knowledge record not found")

        row = WebsiteConsent(
            website_knowledge_id=UUID(str(website_knowledge_id)),
            cookie_categories=cookie_categories or [],
            consent_status=consent_status,
            consent_date=None,  # set when consent is given
            data_retention_preference=data_retention_preference,
            sensitive_info_classification=sensitive_info_classification,
            gdpr_applicable=gdpr_applicable,
            ccpa_applicable=ccpa_applicable,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        return self._row_dict(row)

    async def get(self, consent_id: str) -> Dict[str, Any]:
        row = await self._consent(consent_id)
        return self._row_dict(row)

    async def list(self, website_knowledge_id: Optional[str] = None) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(WebsiteConsent))
        rows = result.scalars().all()
        if website_knowledge_id:
            rows = [r for r in rows if str(r.website_knowledge_id) == website_knowledge_id]
        return [self._row_dict(r) for r in rows]

    async def update_consent(
        self,
        consent_id: str,
        *,
        consent_status: Optional[str] = None,
        cookie_categories: Optional[List[str]] = None,
        data_retention_preference: Optional[str] = None,
        sensitive_info_classification: Optional[str] = None,
        actor: str,
    ) -> Dict[str, Any]:
        """Update consent status and preferences."""
        row = await self._consent(consent_id)
        valid_statuses = ("pending", "accepted", "rejected", "withdrawn")
        if consent_status is not None and consent_status not in valid_statuses:
            raise WebsiteConsentError(f"Invalid consent status: {consent_status}")
        if consent_status is not None:
            row.consent_status = consent_status
            from datetime import datetime, timezone
            row.consent_date = None  # set by caller if desired
        if cookie_categories is not None:
            row.cookie_categories = cookie_categories
        if data_retention_preference is not None:
            row.data_retention_preference = data_retention_preference
        if sensitive_info_classification is not None:
            row.sensitive_info_classification = sensitive_info_classification
        await self.db.commit()
        return self._row_dict(row)

    async def delete(self, consent_id: str) -> Dict[str, Any]:
        row = await self._consent(consent_id)
        await self.db.delete(row)
        await self.db.commit()
        return {"id": str(row.id), "status": "deleted"}

    @staticmethod
    def _row_dict(row: WebsiteConsent) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "website_knowledge_id": str(row.website_knowledge_id),
            "cookie_categories": row.cookie_categories,
            "consent_status": row.consent_status,
            "consent_date": (
                row.consent_date.isoformat() if row.consent_date else None
            ),
            "data_retention_preference": row.data_retention_preference,
            "sensitive_info_classification": row.sensitive_info_classification,
            "gdpr_applicable": row.gdpr_applicable,
            "ccpa_applicable": row.ccpa_applicable,
            "last_updated_at": (
                row.last_updated_at.isoformat() if row.last_updated_at else None
            ),
        }