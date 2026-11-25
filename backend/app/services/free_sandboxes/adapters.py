"""Thin provider adapters (Doc 22).

These are scaffolds: they use official endpoints/CLIs and fail closed, but each
requires live verification and a real credential before activation. Provider
figures are intentionally not hard-coded as guarantees (Doc 19 §1).
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from .base import (
    CredentialMissing,
    EnvironmentState,
    ProviderInfo,
    ProviderUnavailable,
    QuotaSnapshot,
    SandboxCapability,
    SandboxEnvironment,
    SandboxError,
    WorkloadRequest,
)


def _token(env_name: str) -> Optional[str]:
    return os.getenv(env_name) or None


def _verified_snapshot(
    provider: str,
    used_percent: float,
    source_url: str,
    **extra: Any,
) -> QuotaSnapshot:
    return QuotaSnapshot(
        provider=provider,
        used_percent=used_percent,
        verified_at=datetime.now(timezone.utc).isoformat(),
        source_url=source_url,
        **extra,
    )


class GitHubCodespacesAdapter:
    info = ProviderInfo(
        name="github_codespaces",
        capabilities={SandboxCapability.DEVELOPMENT},
        terms_url="https://docs.github.com/en/billing/concepts/product-billing/github-codespaces",
        notes="Token needs the `codespace` scope; set idle timeout and retention.",
    )
    api_base = "https://api.github.com"

    def __init__(self, owner: str, repo: str, token_env: str = "GITHUB_CODESPACES_TOKEN") -> None:
        self.owner = owner
        self.repo = repo
        self.token_env = token_env
        self._quota: Optional[QuotaSnapshot] = None

    def credentials_available(self) -> bool:
        return bool(_token(self.token_env))

    def set_verified_usage(self, used_percent: float, source_url: str, **extra: Any) -> None:
        """Inject a quota reading obtained from an authenticated billing source."""
        self._quota = _verified_snapshot(self.info.name, used_percent, source_url, **extra)

    async def verify_free_tier(self) -> QuotaSnapshot:
        if self._quota:
            return self._quota
        if not self.credentials_available():
            return QuotaSnapshot(
                provider=self.info.name,
                source_url=self.info.terms_url,
                reason="credential not configured",
            )
        # Attempt the authenticated billing usage endpoint. It is only available
        # on the enhanced billing platform; otherwise stay unverified (fail closed).
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    f"{self.api_base}/user/billing/usage",
                    headers=self._headers(),
                    params={"addon_type": "codespaces"},
                )
        except httpx.HTTPError:
            return QuotaSnapshot(
                provider=self.info.name,
                source_url=self.info.terms_url,
                reason="billing usage endpoint unavailable",
            )
        if response.status_code != 200:
            return QuotaSnapshot(
                provider=self.info.name,
                source_url=self.info.terms_url,
                reason=f"billing usage endpoint returned HTTP {response.status_code}",
            )
        data = response.json()
        used = self._find_number(data, "used")
        remaining = self._find_number(data, "remaining")
        if used is None or remaining is None or used + remaining <= 0:
            return QuotaSnapshot(
                provider=self.info.name,
                source_url=self.info.terms_url,
                reason="billing response did not expose a usable quota figure",
            )
        return _verified_snapshot(
            self.info.name,
            used / (used + remaining) * 100,
            self.info.terms_url,
            remaining=remaining,
        )

    @staticmethod
    def _find_number(data: Any, key: str) -> Optional[float]:
        if isinstance(data, dict):
            for k, v in data.items():
                if k == key and isinstance(v, (int, float)):
                    return float(v)
                found = GitHubCodespacesAdapter._find_number(v, key)
                if found is not None:
                    return found
        elif isinstance(data, list):
            for item in data:
                found = GitHubCodespacesAdapter._find_number(item, key)
                if found is not None:
                    return found
        return None

    def _headers(self) -> Dict[str, str]:
        token = _token(self.token_env)
        if not token:
            raise CredentialMissing(f"{self.info.name}: {self.token_env} is not set")
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def provision(self, request: WorkloadRequest) -> SandboxEnvironment:
        body = {
            "ref": request.metadata.get("ref", "main"),
            "devcontainer_path": request.metadata.get(
                "devcontainer_path", ".devcontainer/devcontainer.json"
            ),
            "idle_timeout_minutes": min(max(request.max_runtime_seconds // 60, 5), 240),
            "retention_period_minutes": min(
                max(request.max_runtime_seconds // 60 * 2, 30), 43200
            ),
            "display_name": f"iam-{request.task_id}",
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.api_base}/repos/{self.owner}/{self.repo}/codespaces",
                    headers=self._headers(),
                    json=body,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"{self.info.name}: provisioning failed: {exc}") from exc
        return SandboxEnvironment(
            provider=self.info.name,
            external_id=str(data["name"]),
            capability=request.capability,
            state=EnvironmentState.RUNNING,
            metadata={"web_url": data.get("web_url"), "machine": data.get("machine")},
        )

    async def start(self, external_id: str) -> None:
        await self._post(f"/user/codespaces/{external_id}/start")

    async def stop(self, external_id: str) -> None:
        await self._post(f"/user/codespaces/{external_id}/stop")

    async def delete(self, external_id: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.delete(
                    f"{self.api_base}/user/codespaces/{external_id}",
                    headers=self._headers(),
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"{self.info.name}: delete failed: {exc}") from exc

    async def status(self, external_id: str) -> SandboxEnvironment:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.api_base}/user/codespaces/{external_id}",
                    headers=self._headers(),
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"{self.info.name}: status failed: {exc}") from exc
        return SandboxEnvironment(
            provider=self.info.name,
            external_id=external_id,
            capability=SandboxCapability.DEVELOPMENT,
            state=EnvironmentState.RUNNING if data.get("state") == "available" else EnvironmentState.STOPPED,
            metadata={"state": data.get("state")},
        )

    async def collect_results(self, external_id: str) -> Dict[str, Any]:
        env = await self.status(external_id)
        return {"provider": self.info.name, "external_id": external_id, "status": env.state.value}

    async def _post(self, path: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.api_base}{path}", headers=self._headers()
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"{self.info.name}: {path} failed: {exc}") from exc


class KaggleAdapter:
    info = ProviderInfo(
        name="kaggle",
        capabilities={SandboxCapability.NOTEBOOK, SandboxCapability.MODEL_EVALUATION},
        terms_url="https://www.kaggle.com/docs/efficient-gpu-usage",
        notes="Use script kernels with hard timeouts; phone verification for GPUs.",
    )

    def __init__(self, token_env: str = "KAGGLE_API_TOKEN") -> None:
        self.token_env = token_env

    def credentials_available(self) -> bool:
        return bool(_token(self.token_env))

    async def verify_free_tier(self) -> QuotaSnapshot:
        try:
            out = await self._cli("quota")
            data = json.loads(out)
        except (ProviderUnavailable, json.JSONDecodeError):
            return QuotaSnapshot(
                provider=self.info.name,
                source_url=self.info.terms_url,
                reason="kaggle quota command unavailable or unparseable",
            )

        used = self._find_number(data, "totalSecondsUsed")
        left = self._find_number(data, "totalSecondsLeft")
        if used is None or left is None or used + left <= 0:
            return QuotaSnapshot(
                provider=self.info.name,
                source_url=self.info.terms_url,
                reason="quota response did not expose usable figures",
            )
        return _verified_snapshot(
            self.info.name,
            used / (used + left) * 100,
            self.info.terms_url,
            remaining=left,
            unit="seconds",
        )

    @staticmethod
    def _find_number(data: Any, key: str) -> Optional[float]:
        if isinstance(data, dict):
            for k, v in data.items():
                if k == key and isinstance(v, (int, float)):
                    return float(v)
                found = KaggleAdapter._find_number(v, key)
                if found is not None:
                    return found
        elif isinstance(data, list):
            for item in data:
                found = KaggleAdapter._find_number(item, key)
                if found is not None:
                    return found
        return None

    async def provision(self, request: WorkloadRequest) -> SandboxEnvironment:
        kernel_dir = request.metadata.get("kernel_dir")
        if not kernel_dir:
            raise SandboxError("kaggle: request.metadata['kernel_dir'] is required")
        await self._cli(
            "kernels", "push", "-p", str(kernel_dir),
            "-t", str(request.max_runtime_seconds),
        )
        return SandboxEnvironment(
            provider=self.info.name,
            external_id=str(request.metadata.get("kernel_slug") or request.task_id),
            capability=request.capability,
            state=EnvironmentState.RUNNING,
            metadata={"kernel_dir": str(kernel_dir)},
        )

    async def start(self, external_id: str) -> None:
        await self.status(external_id)

    async def stop(self, external_id: str) -> None:
        await self._cli("kernels", "cancel", "-k", external_id)

    async def delete(self, external_id: str) -> None:
        await self._cli("kernels", "delete", "-k", external_id)

    async def status(self, external_id: str) -> SandboxEnvironment:
        return SandboxEnvironment(
            provider=self.info.name,
            external_id=external_id,
            capability=SandboxCapability.NOTEBOOK,
            state=EnvironmentState.RUNNING,
        )

    async def collect_results(self, external_id: str) -> Dict[str, Any]:
        target = self.info.name
        output_dir = os.getenv("IAM_SANDBOX_RESULTS_DIR", ".")
        await self._cli("kernels", "output", external_id, "-p", output_dir)
        return {"provider": target, "external_id": external_id, "output_dir": output_dir}

    async def _cli(self, *args: str) -> str:
        try:
            process = await asyncio.create_subprocess_exec(
                "kaggle", *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise ProviderUnavailable("kaggle CLI is not installed") from exc
        stdout, stderr = await process.communicate()
        if process.returncode:
            raise ProviderUnavailable(f"kaggle {' '.join(args)}: {stderr.decode().strip()}")
        return stdout.decode()


class HuggingFaceAdapter:
    info = ProviderInfo(
        name="huggingface",
        capabilities={SandboxCapability.MODEL_EVALUATION, SandboxCapability.INFERENCE},
        terms_url="https://huggingface.co/docs/inference-providers/en/pricing",
        notes="Free inference credits are volatile; verify live before any call.",
    )
    api_base = "https://huggingface.co/api"

    def __init__(self, token_env: str = "HF_TOKEN") -> None:
        self.token_env = token_env
        self._quota: Optional[QuotaSnapshot] = None

    def credentials_available(self) -> bool:
        return bool(_token(self.token_env))

    def set_verified_usage(self, used_percent: float, source_url: str, **extra: Any) -> None:
        self._quota = _verified_snapshot(self.info.name, used_percent, source_url, **extra)

    async def verify_free_tier(self) -> QuotaSnapshot:
        return self._quota or QuotaSnapshot(
            provider=self.info.name,
            source_url=self.info.terms_url,
            reason="free inference credits are volatile; no authenticated quota API",
        )

    async def provision(self, request: WorkloadRequest) -> SandboxEnvironment:
        model = request.metadata.get("model")
        if not model:
            raise SandboxError("huggingface: request.metadata['model'] is required")
        return SandboxEnvironment(
            provider=self.info.name,
            external_id=f"hf:{model}",
            capability=request.capability,
            state=EnvironmentState.REGISTERED,
            metadata={"model": str(model)},
        )

    async def start(self, external_id: str) -> None:
        return None

    async def stop(self, external_id: str) -> None:
        return None

    async def delete(self, external_id: str) -> None:
        return None

    async def status(self, external_id: str) -> SandboxEnvironment:
        model = external_id.split(":", 1)[-1]
        return SandboxEnvironment(
            provider=self.info.name,
            external_id=external_id,
            capability=SandboxCapability.MODEL_EVALUATION,
            state=EnvironmentState.REGISTERED,
            metadata={"model": model},
        )

    async def collect_results(self, external_id: str) -> Dict[str, Any]:
        model = external_id.split(":", 1)[-1]
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{self.api_base}/models/{model}")
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"{self.info.name}: model lookup failed: {exc}") from exc
        return {
            "provider": self.info.name,
            "model": model,
            "pipeline_tag": data.get("pipeline_tag"),
            "library_name": data.get("library_name"),
        }


class ColabAdapter:
    info = ProviderInfo(
        name="google_colab",
        capabilities={SandboxCapability.NOTEBOOK, SandboxCapability.MODEL_EVALUATION},
        terms_url="https://developers.google.com/colab/api/reference/rest",
        notes="CLI is Linux/macOS only; REST works everywhere. Release runtimes after use.",
    )
    api_base = "https://colaboratory.googleapis.com/v1beta"

    def __init__(self, token_env: str = "COLAB_API_TOKEN") -> None:
        self.token_env = token_env
        self._quota: Optional[QuotaSnapshot] = None

    def credentials_available(self) -> bool:
        return bool(_token(self.token_env))

    def set_verified_usage(self, used_percent: float, source_url: str, **extra: Any) -> None:
        self._quota = _verified_snapshot(self.info.name, used_percent, source_url, **extra)

    async def verify_free_tier(self) -> QuotaSnapshot:
        return self._quota or QuotaSnapshot(
            provider=self.info.name,
            source_url=self.info.terms_url,
            reason="Colab runtime API does not expose a free-tier quota reading",
        )

    def _headers(self) -> Dict[str, str]:
        token = _token(self.token_env)
        if not token:
            raise CredentialMissing(f"{self.info.name}: {self.token_env} is not set")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def provision(self, request: WorkloadRequest) -> SandboxEnvironment:
        spec = request.metadata.get("runtime_spec") or {}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.api_base}/runtimes", headers=self._headers(), json=spec
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"{self.info.name}: runtime creation failed: {exc}") from exc
        name = str(data.get("name") or data.get("runtimeName") or request.task_id)
        return SandboxEnvironment(
            provider=self.info.name,
            external_id=name,
            capability=request.capability,
            state=EnvironmentState.RUNNING,
            metadata=data,
        )

    async def start(self, external_id: str) -> None:
        await self.status(external_id)

    async def stop(self, external_id: str) -> None:
        # The runtime API has no separate stop; deleting releases the free quota.
        await self.delete(external_id)

    async def delete(self, external_id: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.delete(
                    f"{self.api_base}/{external_id}", headers=self._headers()
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"{self.info.name}: delete failed: {exc}") from exc

    async def status(self, external_id: str) -> SandboxEnvironment:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.api_base}/{external_id}", headers=self._headers()
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"{self.info.name}: status failed: {exc}") from exc
        return SandboxEnvironment(
            provider=self.info.name,
            external_id=external_id,
            capability=SandboxCapability.NOTEBOOK,
            state=EnvironmentState.RUNNING,
            metadata=data,
        )

    async def collect_results(self, external_id: str) -> Dict[str, Any]:
        env = await self.status(external_id)
        return {"provider": self.info.name, "external_id": external_id, "runtime": env.metadata}


class StackBlitzAdapter:
    info = ProviderInfo(
        name="stackblitz",
        capabilities={SandboxCapability.WEB_PROTOTYPE},
        terms_url="https://developer.stackblitz.com/guides/integration/create-with-sdk",
        headless=False,
        notes="Browser-mediated only: WebContainer runs in a tab; no headless server API.",
    )

    def credentials_available(self) -> bool:
        return True  # public project links need no credential

    async def verify_free_tier(self) -> QuotaSnapshot:
        return _verified_snapshot(
            self.info.name, 0.0, self.info.terms_url, unit="public projects"
        )

    @staticmethod
    def project_link(owner: str, repo: str) -> str:
        return f"https://stackblitz.com/github/{owner}/{repo}"

    async def provision(self, request: WorkloadRequest) -> SandboxEnvironment:
        raise SandboxError(
            "stackblitz is browser-mediated: use project_link(owner, repo) and "
            "open it in an interactive browser; it is not background compute"
        )

    async def start(self, external_id: str) -> None:
        raise SandboxError("stackblitz projects are opened in a browser")

    async def stop(self, external_id: str) -> None:
        return None

    async def delete(self, external_id: str) -> None:
        return None

    async def status(self, external_id: str) -> SandboxEnvironment:
        return SandboxEnvironment(
            provider=self.info.name,
            external_id=external_id,
            capability=SandboxCapability.WEB_PROTOTYPE,
            state=EnvironmentState.REGISTERED,
        )

    async def collect_results(self, external_id: str) -> Dict[str, Any]:
        return {"provider": self.info.name, "external_id": external_id, "results": "browser-only"}
