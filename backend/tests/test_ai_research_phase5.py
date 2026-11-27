"""Phase 5 acceptance tests for OD-41 (A13 registry, A15 learning, A16 autonomy)."""

import pytest

from app.services.ai_research import (
    ActionKind,
    AutonomyGate,
    CreatorApprovalRequired,
    ExperimentRecord,
    FileSystemArtifactStore,
    ModelNotApproved,
    ModelRegistry,
    ModelVersion,
    ResearchMemory,
    SignedApproval,
)


def version(name, score=0.8):
    return ModelVersion(
        model="iam-coder",
        version=name,
        checkpoint_ref=f"s3://iam-research/{name}",
        benchmark_score=score,
        capability_profile={"coding": score},
    )


# ---- A13: registry, approval, rollback ---------------------------------------------
def test_a13_approve_deploy_and_rollback(tmp_path):
    events = []
    store = FileSystemArtifactStore(tmp_path / "store")
    registry = ModelRegistry(store, audit_sink=lambda e, d: events.append(e))

    registry.register(version("v1", 0.80))
    registry.approve("iam-coder", "v1")
    registry.deploy("iam-coder", "v1")
    assert registry.active("iam-coder") == "v1"

    registry.register(version("v2", 0.86))
    registry.approve("iam-coder", "v2")
    registry.deploy("iam-coder", "v2")
    rolled = registry.rollback("iam-coder", "v1")

    assert registry.active("iam-coder") == "v1"
    assert rolled.rollback_ref == "v2"
    assert "model_rollback" in events
    assert any(a.kind.value == "result" for a in store.list("registry_iam-coder_v1"))


def test_a13_unapproved_version_cannot_deploy(tmp_path):
    registry = ModelRegistry(FileSystemArtifactStore(tmp_path / "store"))
    registry.register(version("v3"))
    with pytest.raises(ModelNotApproved):
        registry.deploy("iam-coder", "v3")


def test_a13_protected_change_requires_signed_creator_approval(tmp_path):
    events = []
    store = FileSystemArtifactStore(tmp_path / "store")
    registry = ModelRegistry(store, audit_sink=lambda e, d: events.append(e))
    registry.register(version("v4"))

    with pytest.raises(CreatorApprovalRequired):
        registry.approve("iam-coder", "v4", protected=True)

    approval = SignedApproval(
        request_id="req-od11-1", signed_by="creator", signature="ed25519:abc123"
    )
    approved = registry.approve("iam-coder", "v4", approval=approval, protected=True)
    assert approved.approval.signature == "ed25519:abc123"
    assert "creator_authority_used" in events


# ---- A15: research memory ----------------------------------------------------------
def test_a15_failed_experiments_feed_next_plan(tmp_path):
    store = FileSystemArtifactStore(tmp_path / "store")
    memory = ResearchMemory(store)
    memory.record(
        ExperimentRecord(
            experiment_id="exp_fail_2bit",
            task_type="coding",
            method="qlora",
            score=0.2,
            succeeded=False,
            diagnosis="2-bit quantisation produced syntax errors",
            tags=["2bit", "short-context"],
        )
    )
    memory.record(
        ExperimentRecord(
            experiment_id="exp_ok_qlora",
            task_type="coding",
            method="qlora",
            score=0.82,
            succeeded=True,
        )
    )

    hint = memory.suggest_next("coding")
    assert "exp_fail_2bit" in hint["from_failures"]
    assert any("2-bit" in text for text in hint["diagnoses"])
    assert "2bit" in hint["avoid"]
    assert hint["reuse"] == "qlora"
    assert store.list("exp_fail_2bit")


def test_a15_no_failures_yields_empty_avoid_list(tmp_path):
    memory = ResearchMemory(FileSystemArtifactStore(tmp_path / "store"))
    hint = memory.suggest_next("reasoning")
    assert hint["from_failures"] == []
    assert hint["avoid"] == []


# ---- A16: autonomy boundary --------------------------------------------------------
def test_a16_routine_work_needs_no_approval():
    events = []
    gate = AutonomyGate(audit_sink=lambda e, d: events.append(e))
    gate.assert_allowed(ActionKind.ROUTINE)
    assert events == []


def test_a16_authority_actions_require_signed_approval():
    events = []
    gate = AutonomyGate(audit_sink=lambda e, d: events.append(e))
    authority_actions = (
        ActionKind.PAID,
        ActionKind.BINDING,
        ActionKind.HUMAN_ACTION,
        ActionKind.PROTECTED_CORE,
    )
    for kind in authority_actions:
        with pytest.raises(CreatorApprovalRequired):
            gate.assert_allowed(kind)

    approval = SignedApproval(
        request_id="req-a16", signed_by="creator", signature="ed25519:signed"
    )
    for kind in authority_actions:
        gate.assert_allowed(kind, approval)
    assert len(events) == len(authority_actions)
