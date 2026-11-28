"""x402 machine-to-machine payment discovery and preparation (proposed Doc 35).

Discovery is an HTTP GET only; a 402 response is treated as untrusted data.
Nothing is paid here. Purchase requires the existing signed Creator approval and
a payment rail, neither of which is enabled by this module.
"""

from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.blockchain.providers.base import ProviderDenied, require_flag
from app.services.iics.egress import EgressGateway


def _allowed_hosts() -> list[str]:
    """Configured public-host boundary for x402 discovery (empty = public web)."""
    return [
        host.strip().lower().rstrip(".")
        for host in settings.web3_x402_allowed_hosts.split(",")
        if host.strip()
    ]


class X402Service:
    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.web3_x402_enabled,
            "payment_enabled": False,
            "discovery_is_get_only": True,
            "service_data_is_untrusted": True,
            "escrow_policy": "verify delivery before settlement where protocol supports it",
        }

    async def discover(self, service_url: str) -> Dict[str, Any]:
        """GET a service endpoint and report its 402 price without paying.

        All egress goes through the shared pinned gateway: scheme/host/DNS checks,
        private and metadata rejection, per-hop redirect re-assessment, a timeout
        and a response-size cap. The optional configured host list is an extra
        boundary for deployments that only talk to known providers.
        """
        require_flag(settings.web3_x402_enabled, "x402 discovery is disabled")
        gateway = EgressGateway(
            allowed_hosts=_allowed_hosts(),
            timeout=float(settings.web3_request_timeout_seconds),
            max_bytes=100_000,
        )
        result = await gateway.fetch_pinned(
            service_url, headers={"Accept": "application/json"}
        )
        if not result.ok:
            raise ProviderDenied(f"x402 discovery blocked: {result.error}")
        body = result.body[:1000].decode("utf-8", errors="replace")
        if result.status_code != 402:
            return {
                "paid_endpoint": False,
                "status_code": result.status_code,
                "body_excerpt": body[:500],
                "note": "No 402 challenge returned; nothing was paid.",
            }
        return {
            "paid_endpoint": True,
            "status_code": 402,
            "challenge_headers": {
                key: value[:500]
                for key, value in result.headers.items()
                if key in ("x-price", "www-authenticate", "content-type")
            },
            "body_excerpt": body,
            "untrusted": True,
            "note": "Provider and price must be independently verified before approval.",
        }

    def evaluate(
        self, *, price_usd: float, budget_usd: float, provider_reputation: Optional[str] = None
    ) -> Dict[str, Any]:
        require_flag(settings.web3_x402_enabled, "x402 evaluation is disabled")
        try:
            price = float(price_usd)
            budget = float(budget_usd)
        except (TypeError, ValueError) as exc:
            raise ProviderDenied("price and budget must be numeric") from exc
        if price <= 0 or budget < 0:
            raise ProviderDenied("price must be positive and budget non-negative")
        within = price <= budget
        reputation = (provider_reputation or "unknown").lower()
        recommended = within and reputation in ("verified", "trusted")
        return {
            "price_usd": price,
            "budget_usd": budget,
            "provider_reputation": reputation,
            "within_budget": within,
            "recommended": recommended,
            "reason": None if recommended else "budget exceeded or provider not verified",
            "approval_required": True,
        }

    def prepare_purchase(
        self, *, service_url: str, amount_usd: float, payment_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepare a purchase; settlement is deliberately not implemented here."""
        require_flag(settings.web3_x402_enabled, "x402 is disabled")
        if not service_url or amount_usd <= 0:
            raise ProviderDenied("service_url and positive amount_usd are required")
        return {
            "status": "prepared",
            "service_url": service_url,
            "amount_usd": amount_usd,
            "payment_hash": payment_hash,
            "approval_action": "web3.x402.purchase",
            "approval_required": True,
            "execution_enabled": False,
            "escrow_required": True,
        }

    async def settle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise ProviderDenied(
            "x402 settlement requires signed Creator approval and a configured payment rail"
        )
