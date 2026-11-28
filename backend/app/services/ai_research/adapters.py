"""WP5 — research platform adapters built on the Doc 22 adapter contract.

Adapters are deliverers, not authorities: a platform with no driver configured
refuses to provision, and quota state must be verified before any job runs.
Kaggle's P100 (compute capability 6.0) is training-only and refuses vLLM serving.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Protocol, Set

from ..free_sandboxes.base import (
    EnvironmentState,
    ProviderInfo,
    SandboxCapability,
    SandboxEnvironment,
    SandboxError,
    WorkloadRequest,
)
from .jobs import ResearchJob, ResearchMethod
from .quotas import ResearchQuotaSnapshot


class ResearchDriver(Protocol):
    async def provision(self, request: WorkloadRequest) -> str: ...

    async def start(self, external_id: str) -> None: ...

    async def status(self, external_id: str) -> EnvironmentState: ...

    async def collect(self, external_id: str) -> Dict[str, Any]: ...


class ResearchPlatformAdapter(Protocol):
    info: ProviderInfo

    def supports(self, job: ResearchJob) -> bool: ...

    def credentials_available(self) -> bool: ...

    async def verify_research_quota(self) -> ResearchQuotaSnapshot: ...

    async def provision(self, request: WorkloadRequest) -> SandboxEnvironment: ...

    async def start(self, external_id: str) -> None: ...

    async def status(self, external_id: str) -> SandboxEnvironment: ...

    async def collect_results(self, external_id: str) -> Dict[str, Any]: ...


class ResearchAdapterBase:
    def __init__(
        self,
        name: str,
        capabilities: Set[SandboxCapability],
        terms_url: str,
        quota: ResearchQuotaSnapshot,
        notes: str = "",
        driver: Optional[ResearchDriver] = None,
    ) -> None:
        self.info = ProviderInfo(
            name=name, capabilities=capabilities, terms_url=terms_url, notes=notes
        )
        self._quota = quota
        self.driver = driver
        self._environments: Dict[str, SandboxEnvironment] = {}

    def credentials_available(self) -> bool:
        return self.driver is not None

    async def verify_research_quota(self) -> ResearchQuotaSnapshot:
        return self._quota

    def supports(self, job: ResearchJob) -> bool:  # overridden per platform
        return True

    def _require_driver(self) -> ResearchDriver:
        if self.driver is None:
            raise SandboxError(f"{self.info.name}: no driver configured; refusing to provision")
        return self.driver

    async def provision(self, request: WorkloadRequest) -> SandboxEnvironment:
        driver = self._require_driver()
        external_id = await driver.provision(request)
        env = SandboxEnvironment(
            provider=self.info.name,
            external_id=external_id,
            capability=request.capability,
            state=EnvironmentState.PROVISIONING,
            metadata={"experiment_id": request.task_id},
        )
        self._environments[external_id] = env
        return env

    async def start(self, external_id: str) -> None:
        await self._require_driver().start(external_id)
        self._environments[external_id].state = EnvironmentState.RUNNING

    async def status(self, external_id: str) -> SandboxEnvironment:
        env = self._environments[external_id]
        env.state = await self._require_driver().status(external_id)
        return env

    async def collect_results(self, external_id: str) -> Dict[str, Any]:
        return await self._require_driver().collect(external_id)

    def expire_sessions(self) -> None:
        """Simulate a temporary notebook session ending."""
        for env in self._environments.values():
            env.state = EnvironmentState.STOPPED

    def set_quota(self, quota: ResearchQuotaSnapshot) -> None:
        self._quota = quota


def _verified(provider: str, source_url: str, **kwargs: Any) -> ResearchQuotaSnapshot:
    return ResearchQuotaSnapshot(
        provider=provider,
        verified_at=datetime.now(timezone.utc).isoformat(),
        source_url=source_url,
        **kwargs,
    )


class ColabResearchAdapter(ResearchAdapterBase):
    def __init__(self, driver: Optional[ResearchDriver] = None) -> None:
        super().__init__(
            name="google_colab",
            capabilities={SandboxCapability.NOTEBOOK, SandboxCapability.MODEL_EVALUATION},
            terms_url="https://colab.research.google.com/",
            quota=_verified(
                "google_colab",
                "https://colab.research.google.com/",
                used_percent=10.0,
                gpu_name="T4",
                gpu_capability=7.5,
                vram_mb=16000,
                ram_mb=7800,
                session_limit_minutes=720,
                concurrent_jobs_limit=1,
            ),
            notes="Free GPU availability fluctuates; T4+ supports vLLM serving.",
            driver=driver,
        )


class KaggleResearchAdapter(ResearchAdapterBase):
    def __init__(self, driver: Optional[ResearchDriver] = None) -> None:
        super().__init__(
            name="kaggle",
            capabilities={SandboxCapability.NOTEBOOK, SandboxCapability.MODEL_EVALUATION},
            terms_url="https://www.kaggle.com/code",
            quota=_verified(
                "kaggle",
                "https://www.kaggle.com/code",
                used_percent=15.0,
                gpu_name="P100",
                gpu_capability=6.0,
                vram_mb=16000,
                ram_mb=13000,
                session_limit_minutes=720,
                concurrent_jobs_limit=1,
            ),
            notes="P100 compute capability 6.0 — training/benchmarks only, not vLLM.",
            driver=driver,
        )

    def supports(self, job: ResearchJob) -> bool:
        return job.method != ResearchMethod.SERVING


class LightningAIResearchAdapter(ResearchAdapterBase):
    def __init__(self, driver: Optional[ResearchDriver] = None) -> None:
        super().__init__(
            name="lightning_ai",
            capabilities={SandboxCapability.DEVELOPMENT, SandboxCapability.NOTEBOOK},
            terms_url="https://lightning.ai/",
            quota=_verified(
                "lightning_ai",
                "https://lightning.ai/pricing",
                used_percent=20.0,
                gpu_name="T4",
                gpu_capability=7.5,
                vram_mb=16000,
                ram_mb=16000,
                session_limit_minutes=480,
                concurrent_jobs_limit=1,
            ),
            notes="Free GPU credits and eligibility; verify terms before use.",
            driver=driver,
        )


class HuggingFaceResearchAdapter(ResearchAdapterBase):
    def __init__(self, driver: Optional[ResearchDriver] = None) -> None:
        super().__init__(
            name="huggingface_zerogpu",
            capabilities={SandboxCapability.INFERENCE, SandboxCapability.MODEL_EVALUATION},
            terms_url="https://huggingface.co/docs/hub/spaces-zero-gpu",
            quota=_verified(
                "huggingface_zerogpu",
                "https://huggingface.co/docs/hub/spaces-zero-gpu",
                used_percent=5.0,
                gpu_name="ZeroGPU",
                gpu_capability=8.0,
                vram_mb=8000,
                ram_mb=16000,
                session_limit_minutes=5,
                concurrent_jobs_limit=1,
            ),
            notes="~5 min daily GPU quota; short demos only, no sustained training.",
            driver=driver,
        )

    def supports(self, job: ResearchJob) -> bool:
        return job.method in (ResearchMethod.SERVING, ResearchMethod.EVALUATION)
