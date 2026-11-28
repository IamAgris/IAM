"""OD-24 South African banking capability registry and consent gates.

No bank credential value is stored or logged. The default adapter is a stub:
payment proposals are recorded, never submitted. Live adapters are opt-in and
require explicit signed consent plus signed payment authority.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.banking import BankingConsent
from app.models.security import AuditEvent
from app.services.creatorapproval_service import CreatorApprovalService

BANKING_CAPABILITIES = (
    "multi_bank_integration",
    "open_banking_consent",
    "account_balance",
    "payment_initiation",
    "eft_payshap_instant",
    "statement_transaction",
    "beneficiary_verification",
    "multi_currency_fx",
    "merchant_gateway",
    "business_treasury",
    "payroll_supplier",
    "accounting_tax_reconciliation",
    "fraud_risk_detection",
    "compliance_audit",
    "provider_discovery_replacement",
    "payment_interoperability",
    "resilience_recovery",
    "financial_authority",
)
CONSENT_ACTION = "banking.consent"
PAYMENT_ACTION = "banking.payment"


class BankingDenied(PermissionError):
    """Raised when a banking action lacks consent or signed authority."""


class BankingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.banking_enabled,
            "adapter": settings.banking_adapter,
            "country": settings.banking_country,
            "capabilities": list(BANKING_CAPABILITIES),
            "credentials_are_env_var_names": True,
            "consent_required": True,
            "payment_requires_signed_authorization": PAYMENT_ACTION,
        }

    def status(self) -> Dict[str, Any]:
        configured = bool(settings.banking_base_url) and bool(
            os.environ.get(settings.banking_token_env)
        )
        return {
            **self.policy(),
            "configured": configured,
            "available": settings.banking_enabled and configured,
            "live_payment_submission": settings.banking_enabled
            and settings.banking_adapter != "stub"
            and configured,
        }

    async def request_consent(
        self,
        *,
        institution: str,
        account_ref: str,
        capabilities: List[str],
        approval_id: Optional[str],
        ttl_seconds: int,
        actor: str,
    ) -> Dict[str, Any]:
        if not settings.banking_enabled:
            raise BankingDenied("banking adapter is disabled")
        if not institution or not account_ref:
            raise BankingDenied("institution and account_ref are required")
        unknown = [item for item in capabilities if item not in BANKING_CAPABILITIES]
        if unknown:
            raise BankingDenied(f"unknown banking capabilities: {unknown}")
        if not approval_id:
            raise BankingDenied("banking consent requires signed Creator authority")
        authority = await CreatorApprovalService(self.db).check_authorization(
            CONSENT_ACTION, requested_level="3", target_ref=str(approval_id)
        )
        if not authority.get("authorized"):
            raise BankingDenied("no active signed Creator authorization for this consent")
        ttl = max(60, min(int(ttl_seconds or 3600), 86400 * 30))
        consent = BankingConsent(
            institution=institution,
            account_ref=account_ref,
            capabilities=list(capabilities),
            authorization_id=str(authority["authorization_id"]),
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl),
        )
        self.db.add(consent)
        await self.db.flush()
        self.db.add(
            AuditEvent(
                event_type="banking_consent_granted",
                actor=actor,
                target=str(consent.id),
                details={
                    "institution": institution,
                    "capabilities": list(capabilities),
                    "authorization_id": str(authority["authorization_id"]),
                },
            )
        )
        await self.db.commit()
        return self._consent(consent)

    async def consents(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(BankingConsent))
        return [self._consent(row) for row in result.scalars().all()]

    async def revoke_consent(self, consent_id: str, actor: str) -> Dict[str, Any]:
        result = await self.db.execute(
            select(BankingConsent).where(BankingConsent.id == UUID(str(consent_id)))
        )
        consent = result.scalar_one_or_none()
        if not consent:
            raise LookupError("banking consent not found")
        consent.is_active = False  # type: ignore[assignment]
        consent.revoked_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        self.db.add(
            AuditEvent(
                event_type="banking_consent_revoked",
                actor=actor,
                target=str(consent.id),
                details={"institution": consent.institution},
            )
        )
        await self.db.commit()
        return self._consent(consent)

    async def propose_payment(
        self,
        *,
        consent_id: str,
        amount: float,
        beneficiary: str,
        approval_id: Optional[str],
        actor: str,
    ) -> Dict[str, Any]:
        if not approval_id:
            raise BankingDenied("payments require a separate signed Creator authorization")
        authority = await CreatorApprovalService(self.db).check_authorization(
            PAYMENT_ACTION, requested_level="4", target_ref=str(approval_id)
        )
        if not authority.get("authorized"):
            raise BankingDenied("no active signed Creator authorization for this payment")
        result = await self.db.execute(
            select(BankingConsent).where(BankingConsent.id == UUID(str(consent_id)))
        )
        consent = result.scalar_one_or_none()
        if not consent or not consent.is_active or consent.revoked_at:
            raise BankingDenied("no active banking consent for this account")
        if "payment_initiation" not in (consent.capabilities or []):
            raise BankingDenied("consent does not include payment_initiation")
        if amount <= 0 or not beneficiary:
            raise BankingDenied("amount and beneficiary are required")
        self.db.add(
            AuditEvent(
                event_type="banking_payment_proposed",
                actor=actor,
                target=str(consent.id),
                details={
                    "amount": amount,
                    "beneficiary": beneficiary,
                    "authorization_id": authority["authorization_id"],
                    "submitted": False,
                },
            )
        )
        await self.db.commit()
        return {
            "consent_id": str(consent.id),
            "amount": amount,
            "beneficiary": beneficiary,
            "authorization_id": authority["authorization_id"],
            "submitted": False,
            "reason": "no live bank adapter configured; proposal recorded only",
        }

    @staticmethod
    def _consent(row: BankingConsent) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "institution": row.institution,
            "account_ref": row.account_ref,
            "capabilities": row.capabilities or [],
            "is_active": bool(row.is_active),
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
        }
