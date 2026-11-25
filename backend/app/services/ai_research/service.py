"""Phase 0 orchestration: validate, isolate and persist a research job."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Optional

from .artifacts import ArtifactStore, ResearchArtifact, persist_manifest
from .base import ResearchError
from .credentials import CredentialRef, CredentialVault
from .jobs import ResearchJob, validate_job
from .security import (
    DEFAULT_ISOLATION_POLICY,
    IsolationPolicy,
    assert_isolation_policy,
    assert_no_private_data,
)


@dataclass
class PreparedJob:
    job: ResearchJob
    manifest: dict
    artifact: ResearchArtifact
    isolation: IsolationPolicy


def prepare_job(
    job: ResearchJob,
    store: ArtifactStore,
    vault: Optional[CredentialVault] = None,
    credentials: Iterable[CredentialRef] = (),
    private_markers: Iterable[str] = (),
    policy: IsolationPolicy = DEFAULT_ISOLATION_POLICY,
) -> PreparedJob:
    """Fail-closed preparation before a job may leave IAM's boundary."""
    validate_job(job)
    assert_isolation_policy(policy)
    assert_no_private_data(job.to_manifest(), private_markers)

    manifest = job.to_manifest()
    manifest["isolation"] = asdict(policy)
    manifest["credentials"] = [asdict(ref) for ref in credentials]  # refs, never values
    if vault is not None:
        vault.assert_no_credentials(manifest)

    artifact = persist_manifest(store, job.experiment_id, manifest)
    return PreparedJob(job=job, manifest=manifest, artifact=artifact, isolation=policy)


def require_repo_metadata(manifest: dict) -> None:
    """Reject a job that would send results to a temporary notebook only."""
    if not manifest.get("output_artifact_ref") and not manifest.get("outputs"):
        raise ResearchError("job must declare IAM-controlled outputs")
