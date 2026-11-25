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
        if self.options.access_client_id and self.options.access_client_secret:
            headers["CF-Access-Client-Id"] = self.options.access_client_id
            headers["CF-Access-Client-Secret"] = self.options.access_client_secret
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


class _PublicRecords:
    BASE = "/api/v1/public-records"

    def __init__(self, transport: _Transport) -> None:
        self._t = transport

    async def register_source(self, source: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/sources", source)

    async def sources(self) -> Any:
        return await self._t.request("GET", f"{self.BASE}/sources")

    async def ingest(self, record: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/records", record)

    async def search(self, **filters: Any) -> Any:
        query = "&".join(f"{k}={v}" for k, v in filters.items())
        return await self._t.request("GET", f"{self.BASE}/records?{query}")

    async def cross_reference(self, record_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request(
            "POST", f"{self.BASE}/records/{record_id}/cross-reference", body
        )

    async def correct(self, record_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request(
            "POST", f"{self.BASE}/records/{record_id}/corrections", body
        )

    async def relationships(self, record_id: str) -> Any:
        return await self._t.request(
            "GET", f"{self.BASE}/records/{record_id}/relationships"
        )

    async def status(self) -> dict[str, Any]:
        return await self._t.request("GET", f"{self.BASE}/status")


class _Legal:
    BASE = "/api/v1/legal"

    def __init__(self, transport: _Transport) -> None:
        self._t = transport

    async def sources(self) -> Any:
        return await self._t.request("GET", f"{self.BASE}/sources")

    async def register_source(self, source: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/sources", source)

    async def check_source(self, source_id: str, content: str | None = None) -> dict[str, Any]:
        return await self._t.request(
            "POST", f"{self.BASE}/sources/{source_id}/check", {"content": content}
        )

    async def record_instrument(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/instruments", payload)

    async def record_change(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/changes", payload)

    async def authenticate(self, change_id: str) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/changes/{change_id}/authenticate")

    async def understand(self, change_id: str, summary: str) -> dict[str, Any]:
        return await self._t.request(
            "POST", f"{self.BASE}/changes/{change_id}/understand", {"summary": summary}
        )

    async def assess(self, change_id: str, impacts: list[dict[str, Any]]) -> dict[str, Any]:
        return await self._t.request(
            "POST", f"{self.BASE}/changes/{change_id}/assess", {"impacts": impacts}
        )

    async def recommend(self, change_id: str, recommendations: list[str]) -> dict[str, Any]:
        return await self._t.request(
            "POST", f"{self.BASE}/changes/{change_id}/recommend",
            {"recommendations": recommendations},
        )

    async def authorise(self, change_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request(
            "POST", f"{self.BASE}/changes/{change_id}/authorise", payload
        )

    async def implement(self, change_id: str, evidence: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request(
            "POST", f"{self.BASE}/changes/{change_id}/implement", {"evidence": evidence}
        )

    async def verify(self, change_id: str, evidence: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request(
            "POST", f"{self.BASE}/changes/{change_id}/verify", {"evidence": evidence}
        )

    async def alerts(self, severity: str | None = None) -> Any:
        path = f"{self.BASE}/alerts"
        if severity:
            path += f"?severity={severity}"
        return await self._t.request("GET", path)

    async def status(self) -> dict[str, Any]:
        return await self._t.request("GET", f"{self.BASE}/status")


class _Geo:
    BASE = "/api/v1/geo"

    def __init__(self, transport: _Transport) -> None:
        self._t = transport

    async def register_provider(self, provider: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/providers", provider)

    async def providers(self, kind: str | None = None) -> Any:
        path = f"{self.BASE}/providers" + (f"?kind={kind}" if kind else "")
        return await self._t.request("GET", path)

    async def map_config(self, kind: str = "tile") -> dict[str, Any]:
        return await self._t.request("GET", f"{self.BASE}/map/config?kind={kind}")

    async def add_place(self, place: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/places", place)

    async def places(self, query: str, country_code: str | None = None) -> Any:
        path = f"{self.BASE}/places?query={query}"
        if country_code:
            path += f"&country_code={country_code}"
        return await self._t.request("GET", path)

    async def nearby(self, lat: float, lon: float, radius_km: float = 25) -> Any:
        return await self._t.request(
            "GET", f"{self.BASE}/places/nearby?latitude={lat}&longitude={lon}&radius_km={radius_km}"
        )

    async def reverse(self, lat: float, lon: float, radius_km: float = 25) -> Any:
        return await self._t.request(
            "GET", f"{self.BASE}/places/reverse?latitude={lat}&longitude={lon}&radius_km={radius_km}"
        )

    async def geocode(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/geocode", payload)

    async def import_geojson(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/data", payload)

    async def export_geojson(self, place_ids: list[str] | None = None) -> Any:
        path = f"{self.BASE}/data/export"
        if place_ids:
            path += "?place_ids=" + ",".join(place_ids)
        return await self._t.request("GET", path)

    async def register_feed(self, feed: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/feeds", feed)

    async def feeds(self) -> Any:
        return await self._t.request("GET", f"{self.BASE}/feeds")

    async def snapshot_feed(self, feed_id: str, data: Any) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/feeds/{feed_id}/snapshot", {"data": data})

    async def cache_tile(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/tiles", payload)

    async def tile_status(self) -> dict[str, Any]:
        return await self._t.request("GET", f"{self.BASE}/tiles/status")

    async def grant_permission(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/permissions", payload)

    async def resolve_location(
        self, subject: str, lat: float | None = None, lon: float | None = None
    ) -> dict[str, Any]:
        path = f"{self.BASE}/location?subject={subject}"
        if lat is not None and lon is not None:
            path += f"&latitude={lat}&longitude={lon}"
        return await self._t.request("GET", path)

    async def status(self) -> dict[str, Any]:
        return await self._t.request("GET", f"{self.BASE}/status")


class _HumanPresence:
    BASE = "/api/v1/human-presence"

    def __init__(self, transport: _Transport) -> None:
        self._t = transport

    async def boundaries(self) -> dict[str, Any]:
        return await self._t.request("GET", f"{self.BASE}/boundaries")

    async def create_person(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/people", payload)

    async def people(self, name: str | None = None) -> Any:
        path = f"{self.BASE}/people" + (f"?name={name}" if name else "")
        return await self._t.request("GET", path)

    async def add_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/profiles", payload)

    async def verify_profile(self, profile_id: str) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/profiles/{profile_id}/verify")

    async def add_claim(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/claims", payload)

    async def match_people(self, person_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/people/{person_id}/match", payload)

    async def add_relationship(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/relationships", payload)

    async def profiles(self, person_id: str) -> Any:
        return await self._t.request("GET", f"{self.BASE}/people/{person_id}/profiles")

    async def claims(self, person_id: str) -> Any:
        return await self._t.request("GET", f"{self.BASE}/people/{person_id}/claims")

    async def timeline(self, person_id: str) -> Any:
        return await self._t.request("GET", f"{self.BASE}/people/{person_id}/timeline")


class _Creator:
    """Creator channel for locally reviewed, signed decisions (OD-03/OD-19).

    This section is for the human Creator's tooling, not for IAM. Reading a
    challenge is harmless; only a valid signature can create authority.
    """

    BASE = "/api/v1/creator"

    def __init__(self, transport: _Transport) -> None:
        self._t = transport

    async def policy(self) -> dict[str, Any]:
        return await self._t.request("GET", f"{self.BASE}/policy")

    async def pending(self, status: str | None = "pending") -> Any:
        path = self.BASE + "/requests"
        if status:
            path += f"?status={status}"
        return await self._t.request("GET", path)

    async def get(self, request_id: str) -> dict[str, Any]:
        return await self._t.request("GET", f"{self.BASE}/requests/{request_id}")

    async def challenge(self, request_id: str) -> dict[str, Any]:
        return await self._t.request("GET", f"{self.BASE}/requests/{request_id}/challenge")

    async def decide(
        self, request_id: str, decision: str, signature: str, signer_id: str
    ) -> dict[str, Any]:
        return await self._t.request(
            "POST",
            f"{self.BASE}/requests/{request_id}/decide",
            {"decision": decision, "signature": signature, "signer_id": signer_id},
        )


class _AssistantLab:
    BASE = "/api/v1/assistant-lab"

    def __init__(self, transport: _Transport) -> None:
        self._t = transport

    async def boundaries(self) -> dict[str, Any]:
        return await self._t.request("GET", f"{self.BASE}/boundaries")

    async def register_system(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/systems", payload)

    async def systems(self) -> Any:
        return await self._t.request("GET", f"{self.BASE}/systems")

    async def add_note(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/notes", payload)

    async def notes(self, assistant_id: str, topic: str | None = None) -> Any:
        path = f"{self.BASE}/notes?assistant_id={assistant_id}"
        if topic:
            path += f"&topic={topic}"
        return await self._t.request("GET", path)

    async def register_adapter(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/adapters", payload)

    async def adapters(self, assistant_id: str) -> Any:
        return await self._t.request("GET", f"{self.BASE}/adapters?assistant_id={assistant_id}")

    async def start_experiment(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/experiments", payload)

    async def experiments(self) -> Any:
        return await self._t.request("GET", f"{self.BASE}/experiments")

    async def record_result(self, experiment_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/experiments/{experiment_id}/result", payload)

    async def adopt_experiment(self, experiment_id: str, approval_reference: str) -> dict[str, Any]:
        return await self._t.request(
            "POST",
            f"{self.BASE}/experiments/{experiment_id}/adopt",
            {"creator_approval_reference": approval_reference},
        )

    async def compare(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/comparisons", payload)

    async def comparisons(self, capability: str | None = None) -> Any:
        path = f"{self.BASE}/comparisons" + (f"?capability={capability}" if capability else "")
        return await self._t.request("GET", path)

    async def status(self) -> dict[str, Any]:
        return await self._t.request("GET", f"{self.BASE}/status")


class _FreeSandbox:
    """OEDIE free infrastructure provider management (IAM Doc 22)."""

    BASE = "/api/v1/free-sandboxes"

    def __init__(self, transport: _Transport) -> None:
        self._t = transport

    async def policy(self) -> dict[str, Any]:
        return await self._t.request("GET", f"{self.BASE}/policy")

    async def providers(self) -> dict[str, Any]:
        return await self._t.request("GET", f"{self.BASE}/providers")

    async def discover(self) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/discover")

    async def request_registration(self, provider: str) -> dict[str, Any]:
        return await self._t.request(
            "POST", f"{self.BASE}/providers/{provider}/request-registration"
        )

    async def verify_credentials(self, provider: str) -> dict[str, Any]:
        return await self._t.request(
            "POST", f"{self.BASE}/providers/{provider}/verify-credentials"
        )

    async def verify_quota(self, provider: str) -> dict[str, Any]:
        return await self._t.request(
            "POST", f"{self.BASE}/providers/{provider}/verify-quota"
        )

    async def status(self) -> dict[str, Any]:
        return await self._t.request("GET", f"{self.BASE}/status")

    async def monitor(self) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/monitor")

    async def expiry_calendar(self) -> dict[str, Any]:
        return await self._t.request("GET", f"{self.BASE}/expiry-calendar")

    async def provision(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/provision", payload)

    async def recover(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._t.request("POST", f"{self.BASE}/recover", payload)

    async def environments(self) -> dict[str, Any]:
        return await self._t.request("GET", f"{self.BASE}/environments")

    async def environment(self, external_id: str) -> dict[str, Any]:
        return await self._t.request("GET", f"{self.BASE}/environments/{external_id}")

    async def start(self, external_id: str) -> dict[str, Any]:
        return await self._t.request(
            "POST", f"{self.BASE}/environments/{external_id}/start"
        )

    async def stop(self, external_id: str) -> dict[str, Any]:
        return await self._t.request(
            "POST", f"{self.BASE}/environments/{external_id}/stop"
        )

    async def remove(self, external_id: str) -> dict[str, Any]:
        return await self._t.request("DELETE", f"{self.BASE}/environments/{external_id}")

    async def results(self, external_id: str) -> dict[str, Any]:
        return await self._t.request(
            "POST", f"{self.BASE}/environments/{external_id}/results"
        )


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
        self.public_records = _PublicRecords(self._transport)
        self.legal = _Legal(self._transport)
        self.geo = _Geo(self._transport)
        self.human_presence = _HumanPresence(self._transport)
        self.assistant_lab = _AssistantLab(self._transport)
        self.creator = _Creator(self._transport)
        self.free_sandbox = _FreeSandbox(self._transport)

    async def connect(self) -> None:
        await self.core.status()
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    @property
    def queued_tasks(self) -> int:
        return len(self._queue)
