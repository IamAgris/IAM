"""Website Knowledge Base service (Universal Web Intelligence - Module 11).

Stores per-website learned knowledge: login procedures, auth methods,
known restrictions, browser compatibility, verification requirements and
prior failures. No credentials or secrets are stored here - only procedural
metadata that enables safe, repeatable website interaction.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.web_knowledge import WebsiteKnowledge


class WebsiteKnowledgeError(PermissionError):
    """Raised when a website knowledge operation fails."""


class WebsiteKnowledgeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _knowledge(self, knowledge_id: str) -> WebsiteKnowledge:
        try:
            identifier = UUID(str(knowledge_id))
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid website knowledge ID") from exc
        result = await self.db.execute(
            select(WebsiteKnowledge).where(WebsiteKnowledge.id == identifier)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise ValueError("Website knowledge record not found")
        return row

    async def create(
        self,
        *,
        domain: str,
        display_name: Optional[str] = None,
        homepage_url: Optional[str] = None,
        login_procedure: Optional[List[Dict[str, Any]]] = None,
        auth_methods: Optional[List[str]] = None,
        registration_procedure: Optional[List[Dict[str, Any]]] = None,
        supported_passkeys: bool = False,
        mfa_methods: Optional[List[str]] = None,
        known_restrictions: Optional[List[str]] = None,
        browser_compatibility: Optional[List[str]] = None,
        verification_requirements: Optional[List[str]] = None,
        prior_failures: Optional[List[Dict[str, Any]]] = None,
        success_patterns: Optional[List[Dict[str, Any]]] = None,
        actor: str,
    ) -> Dict[str, Any]:
        """Create or update website knowledge for a domain."""
        result = await self.db.execute(
            select(WebsiteKnowledge).where(WebsiteKnowledge.domain == domain.lower())
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise WebsiteKnowledgeError(f"Website knowledge already exists for {domain}")

        row = WebsiteKnowledge(
            domain=domain.lower(),
            display_name=display_name,
            homepage_url=homepage_url,
            login_procedure=login_procedure or [],
            auth_methods=auth_methods or [],
            registration_procedure=registration_procedure or [],
            supported_passkeys=supported_passkeys,
            mfa_methods=mfa_methods or [],
            known_restrictions=known_restrictions or [],
            browser_compatibility=browser_compatibility or [],
            verification_requirements=verification_requirements or [],
            prior_failures=prior_failures or [],
            success_patterns=success_patterns or [],
            is_active=True,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        return self._row_dict(row)

    async def get(self, knowledge_id: str) -> Dict[str, Any]:
        row = await self._knowledge(knowledge_id)
        return self._row_dict(row)

    async def get_by_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            select(WebsiteKnowledge).where(WebsiteKnowledge.domain == domain.lower())
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return self._row_dict(row)

    async def list(self, active_only: bool = False) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(WebsiteKnowledge))
        rows = result.scalars().all()
        if active_only:
            rows = [r for r in rows if r.is_active]
        return [self._row_dict(r) for r in rows]

    async def update(
        self,
        knowledge_id: str,
        *,
        display_name: Optional[str] = None,
        homepage_url: Optional[str] = None,
        login_procedure: Optional[List[Dict[str, Any]]] = None,
        auth_methods: Optional[List[str]] = None,
        registration_procedure: Optional[List[Dict[str, Any]]] = None,
        supported_passkeys: Optional[bool] = None,
        mfa_methods: Optional[List[str]] = None,
        known_restrictions: Optional[List[str]] = None,
        browser_compatibility: Optional[List[str]] = None,
        verification_requirements: Optional[List[str]] = None,
        prior_failures: Optional[List[Dict[str, Any]]] = None,
        success_patterns: Optional[List[Dict[str, Any]]] = None,
        actor: str,
    ) -> Dict[str, Any]:
        row = await self._knowledge(knowledge_id)
        if display_name is not None:
            row.display_name = display_name
        if homepage_url is not None:
            row.homepage_url = homepage_url
        if login_procedure is not None:
            row.login_procedure = login_procedure
        if auth_methods is not None:
            row.auth_methods = auth_methods
        if registration_procedure is not None:
            row.registration_procedure = registration_procedure
        if supported_passkeys is not None:
            row.supported_passkeys = supported_passkeys
        if mfa_methods is not None:
            row.mfa_methods = mfa_methods
        if known_restrictions is not None:
            row.known_restrictions = known_restrictions
        if browser_compatibility is not None:
            row.browser_compatibility = browser_compatibility
        if verification_requirements is not None:
            row.verification_requirements = verification_requirements
        if prior_failures is not None:
            row.prior_failures = prior_failures
        if success_patterns is not None:
            row.success_patterns = success_patterns
        await self.db.commit()
        return self._row_dict(row)

    async def delete(self, knowledge_id: str) -> Dict[str, Any]:
        row = await self._knowledge(knowledge_id)
        await self.db.delete(row)
        await self.db.commit()
        return {"id": str(row.id), "domain": row.domain, "status": "deleted"}

    @staticmethod
    def _row_dict(row: WebsiteKnowledge) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "domain": row.domain,
            "display_name": row.display_name,
            "homepage_url": row.homepage_url,
            "login_procedure": row.login_procedure,
            "auth_methods": row.auth_methods,
            "registration_procedure": row.registration_procedure,
            "supported_passkeys": row.supported_passkeys,
            "mfa_methods": row.mfa_methods,
            "known_restrictions": row.known_restrictions,
            "browser_compatibility": row.browser_compatibility,
            "verification_requirements": row.verification_requirements,
            "prior_failures": row.prior_failures,
            "success_patterns": row.success_patterns,
            "last_verified_at": (
                row.last_verified_at.isoformat() if row.last_verified_at else None
            ),
            "is_active": row.is_active,
        }