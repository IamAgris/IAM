# IAM Core SDK Protocol (version 1)

**Status:** v1 draft for SDK scaffold · must match `IAM_API_CONTRACTS.md`

All official clients (`@iam/sdk`, `iam-sdk`, `iam` CLI, local agent) speak this one protocol. They never access the database or implement their own intelligence/permission logic.

## Transport

- Base URL: `<endpoint>/api/v1` (health is absolute: `<endpoint>/health`).
- JSON, UTF-8; timestamps ISO-8601 UTC; IDs UUID except permanent ULID.
- Auth header: `Authorization: Bearer <scoped API credential>` (created via `POST /api/v1/auth/bootstrap` with `X-Bootstrap-Key`, or via `/api/v1/auth/credentials` using an admin key). Node routes need `operator` scope or higher; `/health` and `/api/v1/access/*` stay public.
- Protocol header: `X-IAM-Protocol-Version: 1`; server rejects incompatible versions with `426`.
- POST that creates resources sends `Idempotency-Key`.
- Errors: `{ detail, code, request_id }` with HTTP status.
- Retries: controlled exponential backoff on `429` and `5xx` only; honour `Retry-After`.
- TLS required outside localhost.

## Endpoint map

| Capability | Method | Path | Status |
|-----------|--------|------|--------|
| Core status | GET | `/health` | exists |
| Readiness | GET | `/health/ready` | platform-dependent |
| Submit task | POST | `/autonomy/tasks/` | exists |
| Get task | GET | `/autonomy/tasks/{id}` | exists |
| Submit research | POST | `/research/` | exists |
| Register node | POST | `/nodes/register` | implemented — candidate node only |
| Node status | GET | `/nodes/{id}` | implemented |
| Resource report | POST | `/nodes/{id}/resources` | implemented — 1% ceiling enforced |
| Node attestation | POST | `/nodes/{id}/attestation` | implemented — Ed25519 signed |
| Restricted report / revoke | POST | `/nodes/{id}/restricted-report`, `/revoke` | implemented |
| SDK diagnostics | GET | `/nodes/protocol/diagnostics` | implemented |
| File upload/retrieve | POST/GET | `/storage/objects` | implemented — core-authorised S3, checksum-verified |
| UWAIE inspect/execute | POST | `/uwaie/inspect`, `/uwaie/execute` | implemented — permission-gated, verified |
| Integrity status / manifest | GET/POST | `/integrity/status`, `/integrity/manifest` | implemented — best-effort, explicit approval |
| Knowledge contribution | POST | `/knowledge/contributions` | reserved |
| Sync objects/status | POST/GET | `/sync/objects`, `/sync/status` | implemented — signed, untrusted data |
| Events | GET (SSE) | `/events` | reserved |

Remaining reserved endpoints return `501` until implemented. SDKs surface a clear diagnostic rather than silently degrading.

## Shared semantics

- **Scoped tokens:** separate credentials per project and per node; no token grants protected-core modification.
- **Offline queue:** tasks submitted while offline are queued locally per client and flushed on reconnect. Queue state is in-memory in v1; durable queue belongs to the local agent.
- **Node registration:** produces a *candidate* node only (OD-26). Trust, capabilities and the 1% resource reservation are core-controlled.
- **Auditing:** all mutating calls include an idempotency key and are logged server-side.
- **Parity:** TypeScript and Python expose the same conceptual surface: `core`, `tasks`, `events`, `nodes`, `resources`, `files`, `knowledge`, `sync`, `diagnostics`.
