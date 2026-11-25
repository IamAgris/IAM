"""Official asynchronous client for the IAM Core."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict

import httpx

from .types import IAMError, IAMOptions, NodeRegistration, TaskSubmit


class _Transport:
    def __init__(self, options: IAMOptions) -> None:
        self.base = options.endpoint.rstrip("/")
        self.options = options

    async def request(self, method: str, path: str, body: Any = None) -> Any:
        url = path if path.startswith("http") else f"{self.base}{path}"
        headers = {
            "X-IAM-Protocol-Version": self.options.api_version,
            "Accept": "application/json",
        }
        if self.options.token:
            headers["Authorization"] = f"Bearer {self.options.token}"
        if method == "POST":
            headers["Idempotency-Key"] = str(uuid.uuid4())

        last: Exception | None = None
        for attempt in range(self.options.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self.options.timeout_ms / 1000
                ) as client:
                    response = await client.request(
                        method, url, headers=headers, json=body
                    )
                if response.status_code == 204:
                    return None
                payload = response.json() if response.content else {}
                if not response.is_success:
                    raise IAMError(
                        str(payload.get("detail", response.reason_phrase)),
                        response.status_code,
                        str(payload.get("code", "iam_error")),
                        payload.get("request_id"),
                    )
                return payload
            except (IAMError, httpx.HTTPError) as exc:
                last = exc
                retryable = isinstance(exc, httpx.HTTPError) or (
                    isinstance(exc, IAMError)
                    and (exc.status == 429 or exc.status >= 500)
                )
                if not retryable or attempt == self.options.max_retries:
                    break
                await asyncio.sleep(2**attempt * 0.1)
        raise last or IAMError("request failed", 0)


class _Core:
    def __init__(self, transport: _Transport) -> None:
        self._t = transport

    async def status(self) -> dict[str, Any]:
        return await self._t.request("GET", "/health")


class _Tasks:
    def __init__(self, transport: _Transport, iam: "IAM") -> None:
        self._t = transport
        self._iam = iam

    async def submit(self, task: TaskSubmit) -> dict[str, Any]:
        if not self._iam.connected:
            self._iam._queue.append(task)
            raise IAMError("offline: task queued locally", 0, "offline")
        return await self._t.request(
            "POST", "/api/v1/autonomy/tasks/", task.to_payload()
        )

    async def get(self, task_id: str) -> dict[str, Any]:
        return await self._t.request("GET", f"/api/v1/autonomy/tasks/{task_id}")

    async def flush_queue(self) -> int:
        sent = 0
        while self._iam._queue:
            task = self._iam._queue.pop(0)
            await self._t.request(
                "POST", "/api/v1/autonomy/tasks/", task.to_payload()
            )
            sent += 1
        return sent


class _Nodes:
    def __init__(self, transport: _Transport) -> None:
        self._t = transport

    async def register(self, node: NodeRegistration) -> dict[str, Any]:
        return await self._t.request(
            "POST", "/api/v1/nodes/register", node.to_payload()
        )

    async def status(self, node_id: str) -> dict[str, Any]:
        return await self._t.request("GET", f"/api/v1/nodes/{node_id}")

    async def attest(
        self, node_id: str, payload: dict[str, Any], signature: str
    ) -> dict[str, Any]:
        return await self._t.request(
            "POST",
            f"/api/v1/nodes/{node_id}/attestation",
            {"payload": payload, "signature": signature},
        )

    async def restrict(self, node_id: str, reason: str) -> dict[str, Any]:
        return await self._t.request(
            "POST", f"/api/v1/nodes/{node_id}/restricted-report", {"reason": reason}
        )

    async def revoke(self, node_id: str) -> dict[str, Any]:
        return await self._t.request("POST", f"/api/v1/nodes/{node_id}/revoke")


class _Integrity:
    def __init__(self, transport: _Transport) -> None:
        self._t = transport

    async def status(self) -> dict[str, Any]:
        return await self._t.request("GET", "/api/v1/integrity/status")

    async def approve(self) -> dict[str, Any]:
        return await self._t.request(
            "POST", "/api/v1/integrity/manifest", {"confirm": True}
        )


class _Sync:
    def __init__(self, transport: _Transport) -> None:
        self._t = transport

    async def status(self) -> dict[str, Any]:
        return await self._t.request("GET", "/api/v1/sync/status")

    async def publish(self, obj: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", "/api/v1/sync/objects", obj)

    async def list(self, since: str | None = None) -> Any:
        path = "/api/v1/sync/objects"
        if since:
            path += f"?since={since}"
        return await self._t.request("GET", path)


class _Resources:
    def __init__(self, transport: _Transport) -> None:
        self._t = transport

    async def report(self, node_id: str, report: dict[str, Any]) -> None:
        await self._t.request(
            "POST", f"/api/v1/nodes/{node_id}/resources", report
        )


class _Files:
    def __init__(self, transport: _Transport) -> None:
        self._t = transport

    async def upload(self, name: str, content: str) -> dict[str, Any]:
        return await self._t.request(
            "POST", "/api/v1/storage/objects", {"name": name, "content": content}
        )

    async def get(self, object_id: str) -> dict[str, Any]:
        return await self._t.request(
            "GET", f"/api/v1/storage/objects/{object_id}"
        )


class _Simple:
    def __init__(self, transport: _Transport, method: str, path: str) -> None:
        self._t = transport
        self._method = method
        self._path = path

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        path = self._path
        if args:
            path = path.format(*args)
        body = kwargs.get("body")
        if body is None and kwargs:
            body = kwargs
        return await self._t.request(self._method, path, body)


class _UWAIE:
    def __init__(self, transport: _Transport) -> None:
        self._t = transport

    async def inspect(self, url: str) -> Dict[str, Any]:
        return await self._t.request("POST", "/api/v1/uwaie/inspect", {"url": url})

    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._t.request("POST", "/api/v1/uwaie/execute", payload)

    async def workflows(self) -> Any:
        return await self._t.request("GET", "/api/v1/uwaie/workflows")


class IAM:
    """Connect local applications and nodes to the IAM Core."""

    def __init__(self, endpoint: str, token: str | None = None, **kwargs: Any) -> None:
        options = IAMOptions(endpoint=endpoint, token=token, **kwargs)
        self._transport = _Transport(options)
        self._queue: list[TaskSubmit] = []
        self.connected = False

        self.core = _Core(self._transport)
        self.tasks = _Tasks(self._transport, self)
        self.nodes = _Nodes(self._transport)
        self.resources = _Resources(self._transport)
        self.files = _Files(self._transport)
        self.knowledge = _Simple(
            self._transport, "POST", "/api/v1/knowledge/contributions"
        )
        self.integrity = _Integrity(self._transport)
        self.sync = _Sync(self._transport)
        self.diagnostics = _Simple(
            self._transport, "GET", "/api/v1/nodes/protocol/diagnostics"
        )
        self.uwaie = _UWAIE(self._transport)

    async def connect(self) -> None:
        await self.core.status()
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    @property
    def queued_tasks(self) -> int:
        return len(self._queue)
