"""Tests for the OEDIE free sandbox adapter layer (Doc 22)."""

from __future__ import annotations

import asyncio

import pytest

from app.services.free_sandboxes import (
    FreeSandboxManager,
    FreeTierUnverified,
    ProviderInfo,
    ProviderUnavailable,
    QuotaExceeded,
    QuotaGuard,
    QuotaSnapshot,
    SandboxCapability,
    SandboxDisabled,
    SandboxError,
    SandboxEnvironment,
    WorkloadRequest,
    build_default_manager,
)
from app.services.free_sandboxes.registration import RegistrationGate
from app.services.free_sandboxes.results import redact, wrap_untrusted
from app.services.free_sandboxes.service import FreeSandboxService


class StubAdapter:
    def __init__(self, name="stub", credential=True, used=10.0, fail=False):
        self.info = ProviderInfo(
            name=name,
            capabilities={SandboxCapability.DEVELOPMENT},
            terms_url="https://example.com/terms",
        )
        self.credential = credential
        self.used = used
        self.fail = fail

    def credentials_available(self):
        return self.credential

    async def verify_free_tier(self):
        return QuotaSnapshot(
            provider=self.info.name,
            used_percent=self.used,
            verified_at="test",
            source_url=self.info.terms_url,
        )

    async def provision(self, request):
        if self.fail:
            raise ProviderUnavailable("stub failure")
        return SandboxEnvironment(
            provider=self.info.name,
            external_id=f"{self.info.name}-{request.task_id}",
            capability=request.capability,
            state="running",
            metadata={"task_id": request.task_id},
        )

    async def start(self, external_id):
        return None

    async def stop(self, external_id):
        return None

    async def delete(self, external_id):
        return None

    async def status(self, external_id):
        return SandboxEnvironment(
            provider=self.info.name,
            external_id=external_id,
            capability=SandboxCapability.DEVELOPMENT,
            state="running",
        )

    async def collect_results(self, external_id):
        return {"external_id": external_id}


def _request(task_id="t1"):
    return WorkloadRequest(
        task_id=task_id,
        capability=SandboxCapability.DEVELOPMENT,
        description="smoke test",
    )


def test_quota_guard_fails_closed_on_unverified():
    guard = QuotaGuard()
    with pytest.raises(FreeTierUnverified):
        guard.assert_allowed(QuotaSnapshot("unknown"))


def test_quota_guard_enforces_safety_margin():
    guard = QuotaGuard()
    with pytest.raises(QuotaExceeded):
        guard.assert_allowed(
            QuotaSnapshot("high", used_percent=85, verified_at="now", source_url="https://docs")
        )


def test_quota_guard_ranking_skips_ineligible():
    guard = QuotaGuard()
    snapshots = [
        QuotaSnapshot("a", used_percent=85, verified_at="now", source_url="https://docs"),
        QuotaSnapshot("b", used_percent=10, verified_at="now", source_url="https://docs"),
        QuotaSnapshot("c", source_url="https://docs"),
    ]
    assert guard.rank(snapshots) == ["b"]


def test_manager_refuses_when_disabled():
    manager = FreeSandboxManager(enabled=False)
    with pytest.raises(SandboxDisabled):
        asyncio.run(manager.provision(_request()))


def test_manager_refuses_without_credentials():
    manager = FreeSandboxManager()
    manager.register(StubAdapter(credential=False))
    with pytest.raises(ProviderUnavailable):
        asyncio.run(manager.provision(_request()))


def test_manager_recovers_on_another_free_provider():
    manager = FreeSandboxManager()
    manager.register(StubAdapter(name="broken", used=10, fail=True))
    manager.register(StubAdapter(name="backup", used=20))
    env = asyncio.run(manager.recover(_request(), failed_provider="broken"))
    assert env.provider == "backup"


def test_manager_collects_results():
    manager = FreeSandboxManager()
    manager.register(StubAdapter())
    env = asyncio.run(manager.provision(_request()))
    results = asyncio.run(manager.collect_results(env.external_id))
    assert results["external_id"] == env.external_id


def test_default_manager_is_disabled_and_registers_all_providers():
    manager = build_default_manager()
    assert manager.enabled is False
    assert {p.name for p in manager.discover()} == {
        "github_codespaces",
        "kaggle",
        "huggingface",
        "google_colab",
        "stackblitz",
    }


def test_service_policy_reports_no_paid_fallback():
    service = FreeSandboxService(db=None)
    policy = service.policy()
    assert policy["paid_fallback"] is False
    assert policy["enabled"] is False
    assert policy["threshold_percent"] == 80


def test_redaction_removes_secret_like_values():
    # Synthetic token used only to exercise redaction; not a credential.
    cleaned = redact({"token": "ghp_abcdefghijklmnopqrstuvwxyz1234567890"})  # gitleaks:allow
    assert "ghp_" not in str(cleaned)


def test_wrap_untrusted_marks_output_as_data_only():
    wrapped = wrap_untrusted({"status": "ok"})
    assert wrapped["trusted"] is False
    assert wrapped["content"]["status"] == "ok"


def test_registration_gate_requires_creator_approval_by_default():
    decision = RegistrationGate().decide("kaggle")
    assert decision.action == "creator_approval"
    assert decision.creator_approval_required is True


def test_circuit_breaker_opens_after_repeated_failures():
    manager = FreeSandboxManager()
    adapter = StubAdapter(name="flaky", fail=True)
    manager.register(adapter)
    for _ in range(manager.policy.circuit_breaker_threshold):
        try:
            asyncio.run(manager.provision(_request()))
        except ProviderUnavailable:
            pass
    assert manager.health()["flaky"]["circuit_open"] is True


def test_protected_core_material_is_refused():
    request = WorkloadRequest(
        task_id="t9",
        capability=SandboxCapability.DEVELOPMENT,
        description="test",
        metadata={"private_key": "do-not-send"},
    )
    try:
        FreeSandboxService.assert_no_protected_data(request)
        raise AssertionError("should have refused")
    except SandboxError:
        pass
