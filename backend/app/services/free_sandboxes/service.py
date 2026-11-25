"""OEDIE free sandbox service: persistence, audit, credentials and activation.

This is the only supported entry point for the adapter layer. It enforces the
activation flag and records every external action as an AuditEvent.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.freesandbox import (
    FreeSandboxEnvironment,
    FreeSandboxProvider,
    FreeSandboxQuotaSnapshot,
    FreeSandboxResult,
)
from app.models.security import AuditEvent, CredentialReference, IntegrationRegistry
from app.models.creatorapproval import CreatorRequest
from app.services.free_sandboxes.base import (
    SandboxEnvironment,
    SandboxError,
    WorkloadRequest,
)
from app.services.free_sandboxes.manager import FreeSandboxManager, build_default_manager
from app.services.free_sandboxes.discovery import ProviderDiscovery
from app.services.free_sandboxes.registration import RegistrationGate
from app.services.free_sandboxes.results import redact, wrap_untrusted


def _env_names() -> Dict[str, str]:
    return {
        "github_codespaces": settings.github_codespaces_token_env,
        "kaggle": settings.kaggle_token_env,
        "huggingface": settings.huggingface_token_env,
        "google_colab": settings.colab_token_env,
        "stackblitz": "",  # public project links need no credential
    }


class FreeSandboxService:
    def __init__(
        self,
        db: AsyncSession,
        actor: str = "iam",
        manager: Optional[FreeSandboxManager] = None,
    ) -> None:
        self.db = db
        self.actor = actor
        self.manager = manager or build_default_manager(audit_sink=self._audit)

    # ------------------------------------------------------------------ policy
    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": self.manager.enabled,
            "safety_margin": self.manager.guard.safety_margin,
            "threshold_percent": self.manager.guard.threshold_percent,
            "paid_fallback": False,
            "account_registration": "creator-approved or permitted by provider terms only",
            "providers": [p.name for p in self.manager.discover()],
            "credential_status": self.credential_status(),
        }

    def credential_status(self) -> List[Dict[str, Any]]:
        names = _env_names()
        status = []
        for adapter in self.manager.adapters:
            env_name = names.get(adapter.info.name, "")
            configured = bool(os.getenv(env_name)) if env_name else True
            if adapter.info.name == "kaggle" and not configured:
                configured = (Path.home() / ".kaggle" / "kaggle.json").exists()
            status.append(
                {
                    "provider": adapter.info.name,
                    "configured": configured,
                    "credential_env": env_name or None,
                }
            )
        return status

    async def validate_credentials(self, provider: str) -> Dict[str, Any]:
        """Validate a credential without printing or storing its value."""
        adapter = self.manager.get_adapter(provider)
        env_name = _env_names().get(provider, "")
        token = os.getenv(env_name) if env_name else None
        if not token:
            await self._record_result(
                f"credential_validation_failed:{provider}", {"reason": "not configured"}
            )
            return {"provider": provider, "valid": False, "reason": "not configured"}

        if provider == "github_codespaces":
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    response = await client.get(
                        "https://api.github.com/user",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/vnd.github+json",
                        },
                    )
                    response.raise_for_status()
            except httpx.HTTPError as exc:
                return {"provider": provider, "valid": False, "reason": type(exc).__name__}
            scopes = [
                s.strip()
                for s in response.headers.get("X-OAuth-Scopes", "").split(",")
                if s.strip()
            ]
            result = {
                "provider": provider,
                "valid": True,
                "has_codespace_scope": "codespace" in scopes,
                "scopes": scopes,
            }
            await self._record_result("credential_validated", result)
            return result

        result = {"provider": provider, "valid": True}
        await self._record_result("credential_validated", result)
        return result

    # --------------------------------------------------------------- providers
    async def ensure_providers(self) -> List[Dict[str, Any]]:
        """Register built-in adapters as candidate providers (idempotent)."""
        names = _env_names()
        for adapter in self.manager.adapters:
            info = adapter.info
            existing = await self.db.execute(
                select(FreeSandboxProvider).where(FreeSandboxProvider.name == info.name)
            )
            record = existing.scalar_one_or_none()
            if not record:
                record = FreeSandboxProvider(
                    name=info.name,
                    provider_type=info.name,
                    capabilities=[c.value for c in info.capabilities],
                    terms_url=info.terms_url,
                    headless=info.headless,
                    registration_status="candidate",
                    is_active=False,
                    credential_env=names.get(info.name) or None,
                    config={"notes": info.notes},
                )
                self.db.add(record)
                await self.db.flush()
            await self._ensure_integration(info.name, names.get(info.name, ""))
        await self.db.commit()
        return await self.list_providers()

    async def list_providers(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(FreeSandboxProvider))
        return [
            {
                "name": p.name,
                "provider_type": p.provider_type,
                "capabilities": p.capabilities,
                "terms_url": p.terms_url,
                "headless": p.headless,
                "registration_status": p.registration_status,
                "is_active": p.is_active,
                "credential_env": p.credential_env,
                "docs_verified_at": p.docs_verified_at.isoformat() if p.docs_verified_at else None,
            }
            for p in result.scalars().all()
        ]

    async def _ensure_integration(self, provider: str, env_name: str) -> None:
        name = f"free_sandbox:{provider}"
        found = await self.db.execute(
            select(IntegrationRegistry).where(IntegrationRegistry.name == name)
        )
        integration = found.scalar_one_or_none()
        if not integration:
            integration = IntegrationRegistry(
                name=name,
                provider=provider,
                integration_type="free_sandbox",
                config={"credential_env": env_name},
                is_active=False,
                requires_creator_approval=True,
            )
            self.db.add(integration)
            await self.db.flush()
        ref = await self.db.execute(
            select(CredentialReference).where(
                CredentialReference.integration_id == integration.id,
                CredentialReference.secret_name == provider,
            )
        )
        if not ref.scalar_one_or_none():
            self.db.add(
                CredentialReference(
                    integration_id=integration.id,
                    secret_name=provider,
                    secret_store="env",
                    secret_path=env_name,  # the NAME, never the secret value
                )
            )

    # ------------------------------------------------------- discovery/register
    async def discover(self) -> List[Dict[str, Any]]:
        self.manager.require_enabled()
        if not getattr(settings, "free_sandbox_discovery_enabled", False):
            raise SandboxError("Provider discovery is disabled")
        found = await ProviderDiscovery().discover()
        for item in found:
            existing = await self.db.execute(
                select(FreeSandboxProvider).where(FreeSandboxProvider.name == item.name)
            )
            record = existing.scalar_one_or_none()
            if not record:
                record = FreeSandboxProvider(
                    name=item.name,
                    provider_type=item.provider_type,
                    capabilities=item.capabilities,
                    terms_url=item.terms_url,
                    headless=item.headless,
                    registration_status="candidate",
                    is_active=False,
                    config={"discovery_evidence": item.evidence},
                )
                self.db.add(record)
            else:
                record.terms_url = item.terms_url
                record.capabilities = item.capabilities
                record.docs_verified_at = datetime.now(timezone.utc)
                record.config = {
                    **(record.config or {}),
                    "discovery_evidence": item.evidence,
                }
        await self._record_result(
            "sandbox_providers_discovered",
            {"count": len(found), "names": [item.name for item in found]},
        )
        await self.db.commit()
        return ProviderDiscovery().to_records(found)

    async def request_registration(self, provider: str) -> Dict[str, Any]:
        self.manager.require_enabled()
        decision = RegistrationGate().decide(provider)
        existing = await self.db.execute(
            select(CreatorRequest).where(
                CreatorRequest.action_type == "free_sandbox_registration",
                CreatorRequest.target_ref == provider,
                CreatorRequest.status == "pending",
            )
        )
        pending = existing.scalar_one_or_none()
        if pending:
            return {
                "provider": provider,
                "request_id": pending.request_id,
                "status": "pending",
                "creator_approval_required": True,
            }
        request_id = f"free-sandbox-register-{provider}-{uuid.uuid4().hex[:8]}"
        self.db.add(
            CreatorRequest(
                request_id=request_id,
                action_type="free_sandbox_registration",
                target_ref=provider,
                risk_level="4",
                summary=f"Register and authorise free infrastructure provider: {provider}",
                reason=decision.reason,
                consequences=[
                    "Creates an external account only if provider terms permit it",
                    "No paid resources or upgrades are activated",
                    "Provider is registered as candidate infrastructure only",
                ],
                requester=self.actor,
                expires_at=datetime.now(timezone.utc)
                + timedelta(seconds=settings.creator_authorization_ttl_seconds),
                metadata_={"decision": decision.action, "provider": provider},
            )
        )
        record = await self.db.execute(
            select(FreeSandboxProvider).where(FreeSandboxProvider.name == provider)
        )
        provider_record = record.scalar_one_or_none()
        if provider_record:
            provider_record.registration_status = "pending_creator_approval"
        await self._record_result(
            "sandbox_registration_requested",
            {"provider": provider, "request_id": request_id, "decision": decision.action},
        )
        await self.db.commit()
        return {
            "provider": provider,
            "request_id": request_id,
            "status": "pending",
            "creator_approval_required": decision.creator_approval_required,
        }

    def enable_browser_opener(self, headless: bool = False) -> Dict[str, Any]:
        from app.services.free_sandboxes.browser import PlaywrightBrowserOpener

        adapter = self.manager.get_adapter("stackblitz")
        opener = PlaywrightBrowserOpener(headless=headless)
        adapter.set_browser_opener(opener)
        self._audit("sandbox_browser_opener_enabled", opener.describe())
        return {"provider": "stackblitz", **opener.describe()}

    def health(self) -> Dict[str, Any]:
        return self.manager.health()

    async def monitor_once(self) -> List[Dict[str, Any]]:
        from app.services.free_sandboxes.monitor import FreeSandboxMonitor

        return await FreeSandboxMonitor(self).poll()

    async def expiry_calendar(self) -> List[Dict[str, Any]]:
        from app.services.free_sandboxes.monitor import FreeSandboxMonitor

        return await FreeSandboxMonitor(self).expiry_calendar()

    # ---------------------------------------------------------------- safety
    @staticmethod
    def assert_no_protected_data(request: WorkloadRequest) -> None:
        forbidden = {
            "private_key", "signing_key", "seed_phrase", "password", "secret",
            "credential_value", "token_value", "memory_dump", "identity_export",
        }
        if forbidden.intersection(request.metadata.keys()):
            raise SandboxError("workload metadata contains protected-core material")
        if redact(request.metadata) != request.metadata:
            raise SandboxError("workload metadata contains a secret-like value")

    # ------------------------------------------------------------------- quota
    async def verify_quota(self, provider: str) -> Dict[str, Any]:
        self.manager.require_enabled()
        adapter = self.manager.get_adapter(provider)
        await self.ensure_providers()
        snapshot = await adapter.verify_free_tier()
        record = await self.db.execute(
            select(FreeSandboxProvider).where(FreeSandboxProvider.name == provider)
        )
        provider_record = record.scalar_one_or_none()
        if provider_record and snapshot.verified:
            self.db.add(
                FreeSandboxQuotaSnapshot(
                    provider_id=provider_record.id,
                    used_percent=snapshot.used_percent,
                    remaining=snapshot.remaining,
                    unit=snapshot.unit,
                    source_url=snapshot.source_url,
                    verified_at=snapshot.verified_at,
                )
            )
        try:
            self.manager.guard.assert_allowed(snapshot)
            allowed = True
            reason = None
        except SandboxError as exc:
            allowed = False
            reason = str(exc)
        await self._record_result(
            "sandbox_quota_verified" if allowed else "sandbox_quota_refused",
            {"provider": provider, "used_percent": snapshot.used_percent, "reason": reason},
        )
        await self.db.commit()
        return {
            "provider": provider,
            "verified": snapshot.verified,
            "used_percent": snapshot.used_percent,
            "source_url": snapshot.source_url,
            "allowed": allowed,
            "reason": reason,
        }

    # -------------------------------------------------------------- lifecycle
    async def provision(self, request: WorkloadRequest) -> Dict[str, Any]:
        self.manager.require_enabled()
        self.assert_no_protected_data(request)
        await self.ensure_providers()
        try:
            env = await self.manager.provision(request)
        except SandboxError as exc:
            await self._record_result("sandbox_provision_failed", {"task_id": request.task_id, "reason": str(exc)})
            await self.db.commit()
            raise
        await self._persist_environment(env)
        await self.db.commit()
        return self._env_dict(env)

    async def recover(self, request: WorkloadRequest, failed_provider: str) -> Dict[str, Any]:
        self.manager.require_enabled()
        env = await self.manager.recover(request, failed_provider)
        await self._persist_environment(env)
        await self.db.commit()
        return self._env_dict(env)

    async def status(self, external_id: str) -> Dict[str, Any]:
        env = await self.manager.status(external_id)
        await self._update_environment(env)
        await self.db.commit()
        return self._env_dict(env)

    async def start(self, external_id: str) -> Dict[str, Any]:
        await self.manager.start(external_id)
        return await self.status(external_id)

    async def stop(self, external_id: str) -> Dict[str, Any]:
        await self.manager.stop(external_id)
        return await self.status(external_id)

    async def delete(self, external_id: str) -> Dict[str, Any]:
        await self.manager.delete(external_id)
        return await self.status(external_id)

    async def collect_results(self, external_id: str) -> Dict[str, Any]:
        self.manager.require_enabled()
        results = await self.manager.collect_results(external_id)
        found = await self.db.execute(
            select(FreeSandboxEnvironment).where(
                FreeSandboxEnvironment.external_id == external_id
            )
        )
        record = found.scalar_one_or_none()
        if record:
            self.db.add(
                FreeSandboxResult(
                    environment_id=record.id,
                    payload=results,
                    artifacts=results.get("artifacts", []),
                    error=results.get("error"),
                )
            )
        await self.db.commit()
        return wrap_untrusted(results)

    async def list_environments(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(FreeSandboxEnvironment))
        return [
            {
                "external_id": e.external_id,
                "provider": e.provider_id,
                "task_id": e.task_id,
                "capability": e.capability,
                "state": e.state,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in result.scalars().all()
        ]

    # ---------------------------------------------------------------- helpers
    async def _persist_environment(self, env: SandboxEnvironment) -> None:
        found = await self.db.execute(
            select(FreeSandboxEnvironment).where(
                FreeSandboxEnvironment.external_id == env.external_id
            )
        )
        record = found.scalar_one_or_none()
        provider = await self.db.execute(
            select(FreeSandboxProvider).where(FreeSandboxProvider.name == env.provider)
        )
        provider_record = provider.scalar_one_or_none()
        if not provider_record:
            raise SandboxError(f"provider not registered in database: {env.provider}")
        if not record:
            record = FreeSandboxEnvironment(
                external_id=env.external_id,
                provider_id=provider_record.id,
                task_id=env.metadata.get("task_id", "unknown"),
                capability=env.capability.value,
                state=env.state.value,
                metadata=env.metadata,
            )
            self.db.add(record)

    async def _update_environment(self, env: SandboxEnvironment) -> None:
        found = await self.db.execute(
            select(FreeSandboxEnvironment).where(
                FreeSandboxEnvironment.external_id == env.external_id
            )
        )
        record = found.scalar_one_or_none()
        if record:
            record.state = env.state.value
            record.metadata = env.metadata

    async def _record_result(self, event_type: str, details: Dict[str, Any]) -> None:
        self.db.add(
            AuditEvent(
                event_type=event_type,
                actor=self.actor,
                target=str(details.get("provider") or details.get("task_id") or ""),
                details=details,
            )
        )

    def _audit(self, event_type: str, details: Dict[str, Any]) -> None:
        if self.db is None:
            return  # policy/introspection paths have no persistence session
        self.db.add(
            AuditEvent(
                event_type=event_type,
                actor=self.actor,
                target=str(details.get("provider") or details.get("external_id") or ""),
                details=dict(details),
            )
        )

    @staticmethod
    def _env_dict(env: SandboxEnvironment) -> Dict[str, Any]:
        return {
            "provider": env.provider,
            "external_id": env.external_id,
            "capability": env.capability.value,
            "state": env.state.value,
            "metadata": env.metadata,
        }
