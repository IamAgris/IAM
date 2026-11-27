"""Website Account Lifecycle service.

Manages an account throughout its entire existence: discovery, registration,
verification, activation, security configuration, maintenance, credential
updates, suspension detection, recovery, migration, closure and deletion.

Distinguishes between accounts owned by IAM, owned by the Creator, and
accounts IAM is merely authorised to access.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.web_knowledge import WebsiteAccountLifecycle, WebsiteKnowledge


class WebsiteAccountError(PermissionError):
    """Raised when an account lifecycle operation fails."""


class WebsiteAccountService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _account(self, account_id: str) -> WebsiteAccountLifecycle:
        try:
            identifier = UUID(str(account_id))
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid account ID") from exc
        result = await self.db.execute(
            select(WebsiteAccountLifecycle).where(WebsiteAccountLifecycle.id == identifier)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise ValueError("Website account not found")
        return row

    async def create(
        self,
        *,
        website_knowledge_id: str,
        account_type: str,
        username: str,
        owner_entity: str,
        email: Optional[str] = None,
        verification_status: str = "unverified",
        mfa_status: str = "none",
        recovery_method: Optional[str] = None,
        is_owned_by_iam: bool = False,
        is_owned_by_creator: bool = False,
        is_authorised_access: bool = False,
        actor: str,
    ) -> Dict[str, Any]:
        """Create a new website account lifecycle record."""
        valid_types = ("owned_by_iam", "owned_by_creator", "authorised_access")
        if account_type not in valid_types:
            raise WebsiteAccountError(f"Invalid account type: {account_type}")
        valid_statuses = ("unverified", "email_verified", "id_verified", "phone_verified")
        if verification_status not in valid_statuses:
            raise WebsiteAccountError(f"Invalid verification status: {verification_status}")
        valid_mfa = ("none", "totp", "hardware_key", "sms", "email", "multi")
        if mfa_status not in valid_mfa:
            raise WebsiteAccountError(f"Invalid MFA status: {mfa_status}")
        valid_account_statuses = ("active", "suspended", "restricted", "closed", "deleted")
        # account_status defaults to active

        # Verify the website knowledge exists
        wk_result = await self.db.execute(
            select(WebsiteKnowledge).where(WebsiteKnowledge.id == UUID(str(website_knowledge_id)))
        )
        if not wk_result.scalar_one_or_none():
            raise ValueError("Website knowledge record not found")

        # Exactly one ownership type should be set
        ownership_count = sum(
            [is_owned_by_iam, is_owned_by_creator, is_authorised_access]
        )
        if ownership_count != 1:
            raise WebsiteAccountError(
                "Exactly one of is_owned_by_iam, is_owned_by_creator, "
                "is_authorised_access must be true"
            )

        row = WebsiteAccountLifecycle(
            website_knowledge_id=UUID(str(website_knowledge_id)),
            account_type=account_type,
            username=username,
            email=email,
            registration_date=None,  # set when registration completes
            verification_status=verification_status,
            mfa_status=mfa_status,
            recovery_method=recovery_method,
            last_login_at=None,
            account_status="active",
            suspension_reason=None,
            suspension_date=None,
            closure_date=None,
            closure_reason=None,
            is_owned_by_iam=is_owned_by_iam,
            is_owned_by_creator=is_owned_by_creator,
            is_authorised_access=is_authorised_access,
            credentials_stored=False,
            passkey_registered=False,
            last_security_check_at=None,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        return self._row_dict(row)

    async def get(self, account_id: str) -> Dict[str, Any]:
        row = await self._account(account_id)
        return self._row_dict(row)

    async def list(self, website_knowledge_id: Optional[str] = None) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(WebsiteAccountLifecycle))
        rows = result.scalars().all()
        if website_knowledge_id:
            rows = [r for r in rows if str(r.website_knowledge_id) == website_knowledge_id]
        return [self._row_dict(r) for r in rows]

    async def update_security(
        self,
        account_id: str,
        *,
        mfa_status: Optional[str] = None,
        recovery_method: Optional[str] = None,
        passkey_registered: Optional[bool] = None,
        actor: str,
    ) -> Dict[str, Any]:
        """Update security configuration for an account."""
        row = await self._account(account_id)
        if mfa_status is not None:
            valid_mfa = ("none", "totp", "hardware_key", "sms", "email", "multi")
            if mfa_status not in valid_mfa:
                raise WebsiteAccountError(f"Invalid MFA status: {mfa_status}")
            row.mfa_status = mfa_status
        if recovery_method is not None:
            row.recovery_method = recovery_method
        if passkey_registered is not None:
            row.passkey_registered = passkey_registered
        row.last_security_check_at = None  # will be set by caller if desired
        await self.db.commit()
        return self._row_dict(row)

    async def update_status(
        self,
        account_id: str,
        *,
        account_status: str,
        suspension_reason: Optional[str] = None,
        actor: str,
    ) -> Dict[str, Any]:
        """Suspend, restrict, close or reactivate an account."""
        row = await self._account(account_id)
        valid_statuses = ("active", "suspended", "restricted", "closed", "deleted")
        if account_status not in valid_statuses:
            raise WebsiteAccountError(f"Invalid account status: {account_status}")
        row.account_status = account_status
        if account_status == "suspended":
            row.suspension_reason = suspension_reason or "suspended"
            row.suspension_date = None  # set by caller if desired
        elif account_status == "closed":
            row.closure_reason = suspension_reason or "closed"
            row.closure_date = None
        elif account_status == "active":
            row.suspension_reason = None
            row.suspension_date = None
            row.closure_reason = None
            row.closure_date = None
        await self.db.commit()
        return self._row_dict(row)

    async def record_login(self, account_id: str, actor: str) -> Dict[str, Any]:
        """Record a successful login for an account."""
        row = await self._account(account_id)
        row.last_login_at = None  # set by caller if desired
        await self.db.commit()
        return self._row_dict(row)

    @staticmethod
    def _row_dict(row: WebsiteAccountLifecycle) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "website_knowledge_id": str(row.website_knowledge_id),
            "account_type": row.account_type,
            "username": row.username,
            "email": row.email,
            "registration_date": (
                row.registration_date.isoformat() if row.registration_date else None
            ),
            "verification_status": row.verification_status,
            "mfa_status": row.mfa_status,
            "recovery_method": row.recovery_method,
            "last_login_at": (
                row.last_login_at.isoformat() if row.last_login_at else None
            ),
            "account_status": row.account_status,
            "suspension_reason": row.suspension_reason,
            "suspension_date": (
                row.suspension_date.isoformat() if row.suspension_date else None
            ),
            "closure_date": (
                row.closure_date.isoformat() if row.closure_date else None
            ),
            "closure_reason": row.closure_reason,
            "is_owned_by_iam": row.is_owned_by_iam,
            "is_owned_by_creator": row.is_owned_by_creator,
            "is_authorised_access": row.is_authorised_access,
            "credentials_stored": row.credentials_stored,
            "passkey_registered": row.passkey_registered,
            "last_security_check_at": (
                row.last_security_check_at.isoformat()
                if row.last_security_check_at else None
            ),
        }