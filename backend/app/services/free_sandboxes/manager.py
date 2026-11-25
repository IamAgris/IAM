"""OEDIE free-infrastructure registry, scheduler and lifecycle manager (Doc 22)."""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Set

from .base import (
    EnvironmentState,
    ProviderAdapter,
    ProviderInfo,
    ProviderUnavailable,
    SandboxCapability,
    SandboxEnvironment,
    SandboxError,
    WorkloadRequest,
)
from .quota import QuotaGuard

AuditSink = Callable[[str, Dict[str, Any]], None]


class FreeSandboxManager:
    """Chooses eligible *free* providers and manages environment lifecycles.

    Failures trigger retry on another eligible provider; there is no paid
    fallback. All actions are emitted to an injectable audit sink so the
    caller can persist them as `AuditEvent` records.
    """

    def __init__(
        self,
        quota_guard: Optional[QuotaGuard] = None,
        audit_sink: Optional[AuditSink] = None,
    ) -> None:
        self.guard = quota_guard or QuotaGuard()
        self.audit_sink = audit_sink
        self._adapters: Dict[str, ProviderAdapter] = {}
        self._environments: Dict[str, SandboxEnvironment] = {}

    def register(self, adapter: ProviderAdapter) -> None:
        name = adapter.info.name
        if name in self._adapters:
            raise ValueError(f"provider already registered: {name}")
        self._adapters[name] = adapter
        self._audit("sandbox_provider_registered", {"provider": name})

    def discover(self) -> List[ProviderInfo]:
        """Return discovered providers and their declared capabilities."""
        return [adapter.info for adapter in self._adapters.values()]

    async def provision(
        self,
        request: WorkloadRequest,
        exclude: Optional[Set[str]] = None,
    ) -> SandboxEnvironment:
        skipped = exclude or set()
        candidates = [
            adapter
            for adapter in self._adapters.values()
            if adapter.info.name not in skipped
            and request.capability in adapter.info.capabilities
            and adapter.credentials_available()
        ]
        if not candidates:
            raise ProviderUnavailable(
                f"no eligible free provider for {request.capability.value}"
            )

        failures: List[str] = []
        for adapter in candidates:
            try:
                snapshot = await adapter.verify_free_tier()
                self.guard.assert_allowed(snapshot)
                env = await adapter.provision(request)
            except SandboxError as exc:
                failures.append(f"{adapter.info.name}: {exc}")
                continue
            self._environments[env.external_id] = env
            self._audit(
                "sandbox_provisioned",
                {
                    "provider": adapter.info.name,
                    "external_id": env.external_id,
                    "task_id": request.task_id,
                    "capability": request.capability.value,
                },
            )
            return env
        raise ProviderUnavailable(
            f"all eligible free providers failed for {request.task_id}: {'; '.join(failures)}"
        )

    async def recover(
        self, request: WorkloadRequest, failed_provider: str
    ) -> SandboxEnvironment:
        """Attempt the same task on another eligible free provider."""
        self._audit(
            "sandbox_recovery_started",
            {"task_id": request.task_id, "failed_provider": failed_provider},
        )
        return await self.provision(request, exclude={failed_provider})

    async def status(self, external_id: str) -> SandboxEnvironment:
        env = self._require(external_id)
        updated = await self._adapter_for(env).status(external_id)
        self._environments[external_id] = updated
        return updated

    async def start(self, external_id: str) -> None:
        env = self._require(external_id)
        await self._adapter_for(env).start(external_id)
        env.state = EnvironmentState.RUNNING
        self._audit("sandbox_started", {"provider": env.provider, "external_id": external_id})

    async def stop(self, external_id: str) -> None:
        env = self._require(external_id)
        await self._adapter_for(env).stop(external_id)
        env.state = EnvironmentState.STOPPED
        self._audit("sandbox_stopped", {"provider": env.provider, "external_id": external_id})

    async def delete(self, external_id: str) -> None:
        env = self._require(external_id)
        await self._adapter_for(env).delete(external_id)
        env.state = EnvironmentState.DELETED
        self._audit("sandbox_deleted", {"provider": env.provider, "external_id": external_id})

    async def collect_results(self, external_id: str) -> Dict[str, Any]:
        env = self._require(external_id)
        results = await self._adapter_for(env).collect_results(external_id)
        results["task_provider"] = env.provider
        self._audit(
            "sandbox_results_collected",
            {"provider": env.provider, "external_id": external_id},
        )
        return results

    def list_environments(self) -> List[SandboxEnvironment]:
        return list(self._environments.values())

    def _require(self, external_id: str) -> SandboxEnvironment:
        env = self._environments.get(external_id)
        if not env:
            raise SandboxError(f"unknown sandbox environment: {external_id}")
        return env

    def _adapter_for(self, env: SandboxEnvironment) -> ProviderAdapter:
        adapter = self._adapters.get(env.provider)
        if not adapter:
            raise SandboxError(f"provider not registered: {env.provider}")
        return adapter

    def _audit(self, event_type: str, details: Dict[str, Any]) -> None:
        if self.audit_sink:
            self.audit_sink(event_type, details)


def build_default_manager(
    audit_sink: Optional[AuditSink] = None,
) -> FreeSandboxManager:
    """Register the shipped adapters without activating any of them.

    Provider selection still requires credentials and verified quota state;
    the capability stays disabled until an operator explicitly authorises it.
    """
    from .adapters import (
        ColabAdapter,
        GitHubCodespacesAdapter,
        HuggingFaceAdapter,
        KaggleAdapter,
        StackBlitzAdapter,
    )
    from app.core.config import settings

    manager = FreeSandboxManager(audit_sink=audit_sink)
    manager.register(
        GitHubCodespacesAdapter(
            owner=getattr(settings, "free_sandbox_github_owner", "IamAgris"),
            repo=getattr(settings, "free_sandbox_github_repo", "IAM"),
        )
    )
    for adapter in (
        KaggleAdapter(),
        HuggingFaceAdapter(),
        ColabAdapter(),
        StackBlitzAdapter(),
    ):
        manager.register(adapter)
    return manager
