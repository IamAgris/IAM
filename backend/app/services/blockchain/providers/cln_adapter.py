"""Read-only Core Lightning (CLNRest) adapter over Tailscale.

CLN is an independent node, never merged with LND. Its restricted rune and CA
certificate come from Docker secrets through environment-variable NAMES. Only the
allowlisted read RPCs are POSTed; payment and channel-changing RPCs are unreachable.
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

READ_METHODS = (
    "getinfo",
    "listfunds",
    "listpeers",
    "listchannels",
    "listpeerchannels",
    "listinvoices",
    "listpayments",
)
WRITE_METHODS = ("invoice", "pay")


class ClnAdapter:
    name = "cln"

    def policy(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "read_enabled": settings.cln_read_enabled,
            "allowed_methods": list(READ_METHODS),
            "write_methods": list(WRITE_METHODS),
            "write_enabled": settings.cln_write_enabled,
            "execution_requires_signed_authorization": True,
            "separate_write_rune": True,
            "independent_from": "lnd",
            "credentials_are_env_var_names": True,
            "rune_env": settings.cln_rune_env,
            "ca_cert_env": settings.cln_ca_cert_env,
            "transport": "tailscale",
            "tls_verification_required": True,
        }

    def configured(self) -> bool:
        return bool(settings.cln_rest_url) and bool(read_secret(settings.cln_rune_env))

    def _tls(self):  # type: ignore[no-untyped-def]
        material = read_secret(settings.cln_ca_cert_env) or ""
        if not material:
            raise ProviderDenied("CLN CA certificate is not configured")
        if "BEGIN CERTIFICATE" in material:
            context = ssl.create_default_context()
            context.load_verify_locations(cadata=material)
            return context
        if Path(material).is_file():
            return material
        raise ProviderDenied("CLN CA certificate secret is neither a cert nor a cert path")

    async def get_info(self) -> ProviderResponse:
        return ProviderResponse(
            provider=self.name,
            operation="get_info",
            data={
                **self.policy(),
                "configured": self.configured(),
                "available": settings.cln_read_enabled and self.configured(),
                "network_calls_made": False,
            },
        )

    async def _call(self, method: str, params: Dict[str, Any] | None = None) -> ProviderResponse:
        require_flag(settings.cln_read_enabled, "CLN read adapter is disabled")
        if method not in READ_METHODS:
            raise ProviderDenied(f"CLN RPC '{method}' is not in the read-only allowlist")
        if not self.configured():
            raise ProviderDenied("CLN adapter is not configured")
        rune = read_secret(settings.cln_rune_env) or ""
        headers = {"Rune": rune, "Content-Type": "application/json"}
        async with httpx.AsyncClient(
            timeout=settings.web3_request_timeout_seconds, verify=self._tls()  # type: ignore[no-untyped-call]
        ) as client:
            response = await client.post(
                f"{settings.cln_rest_url.rstrip('/')}/v1/{method}",
                json=params or {},
                headers=headers,
            )
            response.raise_for_status()
            return ProviderResponse(
                provider=self.name,
                operation=method,
                data={"result": response.json()},
                network_calls_made=True,
            )

    async def get_node_info(self) -> ProviderResponse:
        return await self._call("getinfo")

    async def get_balance(self) -> ProviderResponse:
        return await self._call("listfunds")

    async def get_channels(self) -> ProviderResponse:
        return await self._call("listpeerchannels")

    async def get_peers(self) -> ProviderResponse:
        return await self._call("listpeers")

    async def get_invoices(self) -> ProviderResponse:
        return await self._call("listinvoices")

    async def get_payments(self) -> ProviderResponse:
        return await self._call("listpayments")

    async def _write_call(
        self,
        method: str,
        params: Dict[str, Any],
        authorization: Optional[ExecutionAuthorization],
        action: str,
    ) -> ProviderResponse:
        require_flag(settings.cln_write_enabled, "CLN write adapter is disabled")
        if method not in WRITE_METHODS:
            raise ProviderDenied(f"CLN RPC '{method}' is not in the write allowlist")
        Web3ApprovalService.require_authorization(authorization, action)
        if not self.configured():
            raise ProviderDenied("CLN adapter is not configured")
        rune = read_secret(settings.cln_write_rune_env) or ""
        if not rune:
            raise ProviderDenied("a separate write-scoped CLN rune is required")
        headers = {"Rune": rune, "Content-Type": "application/json"}
        async with httpx.AsyncClient(
            timeout=settings.web3_request_timeout_seconds, verify=self._tls()  # type: ignore[no-untyped-call]
        ) as client:
            response = await client.post(
                f"{settings.cln_rest_url.rstrip('/')}/v1/{method}",
                json=params,
                headers=headers,
            )
            response.raise_for_status()
            return ProviderResponse(
                provider=self.name,
                operation=method,
                data={"result": response.json(), "authorization": authorization.summary() if authorization is not None else {}, "read_only": False},
                network_calls_made=True,
                read_only=False,
            )

    async def create_invoice(
        self, payload: Dict[str, Any], authorization: Optional[ExecutionAuthorization] = None
    ) -> ProviderResponse:
        Web3ApprovalService.require_authorization(authorization, "web3.invoice.create")
        try:
            amount_msat = int(payload.get("amount_msat"))  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise ProviderDenied("amount_msat must be an integer") from exc
        if amount_msat <= 0:
            raise ProviderDenied("amount_msat must be positive")
        return await self._write_call(
            "invoice",
            {"amount_msat": amount_msat, "label": str(payload.get("label", "iam"))[:200]},
            authorization,
            "web3.invoice.create",
        )

    async def pay_invoice(
        self, payload: Dict[str, Any], authorization: Optional[ExecutionAuthorization] = None
    ) -> ProviderResponse:
        Web3ApprovalService.require_authorization(authorization, "web3.payment.pay_invoice")
        bolt11 = payload.get("bolt11")
        if not bolt11 or not isinstance(bolt11, str):
            raise ProviderDenied("bolt11 is required")
        return await self._write_call(
            "pay", {"invoice": bolt11}, authorization, "web3.payment.pay_invoice"
        )
