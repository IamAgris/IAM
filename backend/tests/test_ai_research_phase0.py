"""Phase 0 acceptance tests for OD-41 (A0, A1, A2, A3, A14)."""

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.services.ai_research import (
    CredentialLeak,
    CredentialRef,
    CredentialVault,
    DigestMismatch,
    FileSystemArtifactStore,
    HardwareRequirement,
    IsolationPolicy,
    IsolationViolation,
    InvalidResearchJob,
    PaidUpgradeRequested,
    PrivateDataLeak,
    ResearchJob,
    ResearchMethod,
    ResearchQuotaGuard,
    ResearchQuotaSnapshot,
    assert_isolation_policy,
    validate_job,
    assert_no_private_data,
    persist_manifest,
    prepare_job,
    sha256_bytes,
    verify_digest,
    wrap_research_output,
)
from app.services.free_sandboxes.base import FreeTierUnverified, QuotaExceeded

VERIFIED_AT = datetime.now(timezone.utc).isoformat()


def job(**overrides):
    defaults = dict(
        experiment_id="exp_phase0_test",
        title="QLoRA coding experiment",
        task_type="coding",
        complexity=3,
        method=ResearchMethod.QLORA,
        model="Qwen2.5-Coder-3B",
        dataset_ref="s3://iam-datasets/code-v1",
        hardware=HardwareRequirement(min_ram_mb=4096, max_runtime_minutes=60),
        outputs=["checkpoint", "benchmark_report"],
    )
    defaults.update(overrides)
    return ResearchJob(**defaults)


def snapshot(**overrides):
    defaults = dict(
        provider="colab",
        used_percent=10.0,
        verified_at=VERIFIED_AT,
        source_url="https://colab.research.google.com/",
        gpu_name="T4",
        gpu_capability=7.5,
        vram_mb=16000,
        ram_mb=7800,
        session_limit_minutes=720,
        concurrent_jobs_limit=1,
    )
    defaults.update(overrides)
    return ResearchQuotaSnapshot(**defaults)


# A0 — artifact contract survives session expiry
def test_a0_artifacts_survive_notebook_session_expiry(tmp_path):
    store = FileSystemArtifactStore(tmp_path / "persistent")
    notebook = tmp_path / "notebook"
    notebook.mkdir()
    manifest_path = notebook / "job.json"
    manifest_path.write_text(json.dumps(job().to_manifest()), encoding="utf-8")

    artifact = persist_manifest(store, "exp_phase0_test", json.loads(manifest_path.read_text()))
    shutil.rmtree(notebook)

    assert store.exists(artifact.relative_path)
    assert json.loads(store.get(artifact.relative_path))["title"] == "QLoRA coding experiment"
    assert artifact.sha256 == sha256_bytes(store.get(artifact.relative_path))
    assert store.list("exp_phase0_test")[0].relative_path == artifact.relative_path


# A1 — secret isolation
def test_a1_secret_value_never_enters_job_payload(tmp_path):
    vault = CredentialVault({"COLAB_TOKEN": "xyzzy9876543210"})
    leaky = job(metadata={"note": "xyzzy9876543210"})
    store = FileSystemArtifactStore(tmp_path / "store")
    with pytest.raises(CredentialLeak):
        prepare_job(leaky, store, vault=vault)
    assert vault.redact("value xyzzy9876543210") == "value [REDACTED]"


def test_a1_secret_key_in_metadata_is_rejected(tmp_path):
    vault = CredentialVault()
    bad = job(metadata={"api_key": "anything"})
    with pytest.raises(InvalidResearchJob):
        prepare_job(bad, FileSystemArtifactStore(tmp_path / "store"), vault=vault)


def test_a1_credential_refs_store_names_not_values(tmp_path):
    vault = CredentialVault({"COLAB_TOKEN": "xyzzy9876543210"})
    ref = CredentialRef("colab", "COLAB_TOKEN")
    store = FileSystemArtifactStore(tmp_path / "store")
    prepared = prepare_job(job(), store, vault=vault, credentials=[ref])
    assert prepared.manifest["credentials"][0]["env_var"] == "COLAB_TOKEN"
    assert "xyzzy9876543210" not in json.dumps(prepared.manifest)


# A2 — quota gate
def test_a2_verified_snapshot_allows_job():
    ResearchQuotaGuard().assert_allowed(snapshot(), job())


def test_a2_unverified_quota_refused():
    with pytest.raises(FreeTierUnverified):
        ResearchQuotaGuard().assert_allowed(snapshot(verified_at=None), job())


def test_a2_safety_margin_enforced():
    with pytest.raises(QuotaExceeded):
        ResearchQuotaGuard().assert_allowed(snapshot(used_percent=95.0), job())


def test_a2_paid_upgrade_never_automatic():
    with pytest.raises(PaidUpgradeRequested):
        ResearchQuotaGuard().assert_allowed(snapshot(paid_required=True), job())


def test_a2_vllm_rejects_compute_capability_below_7_5():
    serving = job(
        method=ResearchMethod.SERVING,
        dataset_ref="",
        hardware=HardwareRequirement(min_ram_mb=4096, min_gpu_capability=7.5),
    )
    with pytest.raises(QuotaExceeded):
        ResearchQuotaGuard().assert_allowed(
            snapshot(gpu_name="P100", gpu_capability=6.0, vram_mb=16000), serving
        )


def test_a2_insufficient_vram_or_session_refused():
    vram_job = job(hardware=HardwareRequirement(min_ram_mb=4096, min_vram_mb=4000))
    with pytest.raises(QuotaExceeded):
        ResearchQuotaGuard().assert_allowed(snapshot(vram_mb=2000), vram_job)
    with pytest.raises(QuotaExceeded):
        ResearchQuotaGuard().assert_allowed(snapshot(session_limit_minutes=30), job())


def test_a2_ranking_prefers_eligible_low_usage():
    guard = ResearchQuotaGuard()
    ranked = guard.rank(
        [snapshot(provider="a", used_percent=40), snapshot(provider="b", used_percent=5)],
        job(),
    )
    assert ranked == ["b", "a"]


# A3 — common job format
def test_a3_manifest_round_trip_is_stable():
    original = job()
    manifest = original.to_manifest()
    assert ResearchJob.from_manifest(manifest).to_manifest() == manifest


def test_a3_serving_job_requires_vllm_capability():
    serving = job(method=ResearchMethod.SERVING, dataset_ref="", hardware=HardwareRequirement())
    with pytest.raises(InvalidResearchJob):
        validate_job(serving)


# A14 — isolation, integrity and privacy
def test_a14_digest_verification():
    payload = b"model-weights"
    verify_digest(payload, sha256_bytes(payload))
    with pytest.raises(DigestMismatch):
        verify_digest(payload, "0" * 64)


def test_a14_private_marker_detected():
    with pytest.raises(PrivateDataLeak):
        assert_no_private_data({"note": "user alice said..."}, ["alice"])


def test_a14_core_access_forbidden():
    with pytest.raises(IsolationViolation):
        assert_isolation_policy(IsolationPolicy(core_access=True))
    with pytest.raises(IsolationViolation):
        assert_isolation_policy(IsolationPolicy(network_allowed=True))


def test_a14_external_output_marked_untrusted_and_redacted():
    wrapped = wrap_research_output({"log": "ghp_" + "a" * 24}, "colab")
    assert wrapped["trusted"] is False
    assert "ghp_" not in json.dumps(wrapped)
    assert wrapped["isolation"]["network_allowed"] is False
