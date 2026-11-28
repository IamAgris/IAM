"""Read-only LND REST adapter over Tailscale with TLS verification.

The macaroon and TLS certificate are read from Docker secrets through environment
variable NAMES. No admin macaroon is acceptable for routine access; the operator
must provision a restricted read-only macaroon. Only GET endpoints are reachable.
"""

import ssl
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.core.secrets import read_secret
from app.services.blockchain.governance import (
    ExecutionAuthorization,
    Web3ApprovalService,
)
from app.services.blockchain.providers.base import (
    ProviderDenied,
    ProviderResponse,
    require_flag,
)

READ_PATHS = (
    "/v1/getinfo",
    "/v1/balance/blockchain",
    "/v1/channels",
    "/v1/peers",
    "/v1/invoices",
    "/v1/payments",
)
WRITE_PATHS = ("/v1/invoices", "/v1/channels/transactions")


class LndAdapter:
    name = "lnd"

    def policy(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "read_enabled": settings.lnd_read_enabled,
            "allowed_paths": list(READ_PATHS),
            "write_paths": list(WRITE_PATHS),
            "methods": ["GET", "POST"],
            "write_enabled": settings.lnd_write_enabled,
            "execution_requires_signed_authorization": True,
            "separate_write_macaroon": True,
            "credentials_are_env_var_names": True,
            "macaroon_env": settings.lnd_macaroon_env,
            "tls_cert_env": settings.lnd_tls_cert_env,
            "transport": "tailscale",
            "tls_verification_required": True,
        }

    def configured(self) -> bool:
        return bool(settings.lnd_rest_url) and bool(
            read_secret(settings.lnd_macaroon_env)
        )

    def _tls(self):  # type: ignore[no-untyped-def]
        """Never disable verification: use a cert path or PEM from the secret."""
        material = read_secret(settings.lnd_tls_cert_env) or ""
        if not material:
            raise ProviderDenied("LND TLS certificate is not configured")
        if "BEGIN CERTIFICATE" in material:
            context = ssl.create_default_context()
            context.load_verify_locations(cadata=material)
            return context
        if Path(material).is_file():
            return material
        raise ProviderDenied("LND TLS certificate secret is neither a cert nor a cert path")

    async def get_info(self) -> ProviderResponse:
        return ProviderResponse(
            provider=self.name,
            operation="get_info",
            data={
                **self.policy(),
                "configured": self.configured(),
                "available": settings.lnd_read_enabled and self.configured(),
                "network_calls_made": False,
            },
        )

    async def _get(self, path: str) -> ProviderResponse:
        require_flag(settings.lnd_read_enabled, "LND read adapter is disabled")
        if path not in READ_PATHS:
            raise ProviderDenied(f"LND path '{path}' is not in the read-only allowlist")
        if not self.configured():
            raise ProviderDenied("LND adapter is not configured")
        macaroon = read_secret(settings.lnd_macaroon_env) or ""
        headers = {"Grpc-Metadata-macaroon": macaroon}
        async with httpx.AsyncClient(
            timeout=settings.web3_request_timeout_seconds, verify=self._tls()  # type: ignore[no-untyped-call]
        ) as client:
            response = await client.get(f"{settings.lnd_rest_url.rstrip('/')}{path}", headers=headers)
            response.raise_for_status()
            return ProviderResponse(
                provider=self.name,
                operation=path,
                data={"result": response.json()},
                network_calls_made=True,
            )

    async def get_node_info(self) -> ProviderResponse:
        return await self._get("/v1/getinfo")

    async def get_balance(self) -> ProviderResponse:
        return await self._get("/v1/balance/blockchain")

    async def get_channels(self) -> ProviderResponse:
        return await self._get("/v1/channels")

    async def get_peers(self) -> ProviderResponse:
        return await self._get("/v1/peers")

    async def get_invoices(self) -> ProviderResponse:
        return await self._get("/v1/invoices")

    async def get_payments(self) -> ProviderResponse:
        return await self._get("/v1/payments")

    async def _write(
        self,
        path: str,
        body: Dict[str, Any],
        authorization: Optional[ExecutionAuthorization],
        action: str,
    ) -> ProviderResponse:
        require_flag(settings.lnd_write_enabled, "LND write adapter is disabled")
        if path not in WRITE_PATHS:
            raise ProviderDenied(f"LND path '{path}' is not in the write allowlist")
        Web3ApprovalService.require_authorization(authorization, action)
        if not self.configured():
            raise ProviderDenied("LND adapter is not configured")
        macaroon = read_secret(settings.lnd_write_macaroon_env) or ""
        if not macaroon:
            raise ProviderDenied("a separate write-scoped LND macaroon is required")
        headers = {"Grpc-Metadata-macaroon": macaroon, "Content-Type": "application/json"}
        async with httpx.AsyncClient(
            timeout=settings.web3_request_timeout_seconds, verify=self._tls()  # type: ignore[no-untyped-call]
        ) as client:
            response = await client.post(
                f"{settings.lnd_rest_url.rstrip('/')}{path}", json=body, headers=headers
            )
            response.raise_for_status()
            return ProviderResponse(
                provider=self.name,
                operation=path,
                data={"result": response.json(), "authorization": authorization.summary() if authorization is not None else {}, "read_only": False},
                network_calls_made=True,
                read_only=False,
            )

    async def create_invoice(
        self, payload: Dict[str, Any], authorization: Optional[ExecutionAuthorization] = None
    ) -> ProviderResponse:
        Web3ApprovalService.require_authorization(authorization, "web3.invoice.create")
        try:
            value = int(payload.get("amount_sats"))  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise ProviderDenied("amount_sats must be an integer") from exc
        if value <= 0:
            raise ProviderDenied("amount_sats must be positive")
        return await self._write(
            "/v1/invoices",
            {"value": value, "memo": str(payload.get("memo", "IAM"))[:200]},
            authorization,
            "web3.invoice.create",
        )

    async def pay_invoice(
        self, payload: Dict[str, Any], authorization: Optional[ExecutionAuthorization] = None
    ) -> ProviderResponse:
        Web3ApprovalService.require_authorization(authorization, "web3.payment.pay_invoice")
        payment_request = payload.get("payment_request")
        if not payment_request or not isinstance(payment_request, str):
            raise ProviderDenied("payment_request is required")
        return await self._write(
            "/v1/channels/transactions",
            {"payment_request": payment_request},
            authorization,
            "web3.payment.pay_invoice",
        )
