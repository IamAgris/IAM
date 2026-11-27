"""Fiat on/off-ramp research (proposed Doc 33).

Provider availability, fees, geography and KYC requirements must be verified
live before any integration. No account is opened and no payment is initiated.
"""

from typing import Any, Dict, List

from app.core.config import settings
from app.services.blockchain.providers.base import ProviderDenied, require_flag

CANDIDATES = (
    {"name": "regulated_exchange", "route": "on_off_ramp", "verified": False},
    {"name": "local_payment_provider", "route": "on_ramp", "verified": False},
    {"name": "card_provider", "route": "on_ramp", "verified": False},
    {"name": "bank_payout_provider", "route": "off_ramp", "verified": False},
)


class FiatRampResearch:
    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.web3_registry_enabled,
            "integration_enabled": False,
            "kyc_and_geography_must_be_verified": True,
            "paid_provider_requires_approval": True,
        }

    def candidates(self, route: str | None = None) -> List[Dict[str, Any]]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        return [dict(item) for item in CANDIDATES if not route or item["route"] == route]

    def evaluate(
        self,
        *,
        provider: str,
        fee_pct: float,
        supports_south_africa: bool,
        kyc_required: bool,
        terms_verified: bool,
    ) -> Dict[str, Any]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        if fee_pct < 0:
            raise ProviderDenied("fee_pct cannot be negative")
        blockers: List[str] = []
        if not supports_south_africa:
            blockers.append("geography")
        if kyc_required and not terms_verified:
            blockers.append("kyc_terms_unverified")
        if not terms_verified:
            blockers.append("terms")
        return {
            "provider": provider,
            "fee_pct": fee_pct,
            "eligible": not blockers,
            "blockers": blockers,
            "integration_enabled": False,
            "note": "Eligibility is research data, not a legal or commercial approval.",
        }
