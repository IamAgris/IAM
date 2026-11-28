# IAM Core SDK Protocol (version 1)

**Status:** v1 · server rejects an incompatible `X-IAM-Protocol-Version` with `426` and advertises the current version at `GET /api/v1/auth/protocol` · strict header requirement is opt-in (`IAM_PROTOCOL_REQUIRE_HEADER`)

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

### IPLCI governance headers (OD-48)

Calls that touch external material, training data, publishing or tools should send a governance context. The backend middleware converts these into an ambient context inherited by all downstream services.

- `X-IPLCI-Source-Id` — registered IPLCI source identifier (required for governed operations).
- `X-IPLCI-Dataset-Id` — dataset identifier for training requests.
- `X-IPLCI-Approval-Id` — independent training approval identifier.
- `X-IPLCI-Agent-Id` — calling agent/sub-agent identity.
- `X-IPLCI-Jurisdiction` — applicable jurisdiction.

Never send a fabricated source id. Missing context is **not** approval; operations that require provenance fail closed with `IPLCI_PROVENANCE_REQUIRED`. The official frontend client exposes `setIPLCIGovernanceContext()` in `frontend/lib/api.ts`; direct API callers send the headers above.

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
| Public records sources/records | POST/GET | `/public-records/sources`, `/public-records/records` | implemented — provenance, access gates |
| Record cross-reference/correction | POST | `/public-records/records/{id}/cross-reference`, `/corrections` | implemented — no silent overwrite |
| Legal sources/instruments/changes | POST/GET | `/legal/sources`, `/legal/instruments`, `/legal/changes` | implemented — 8-stage lifecycle |
| Legal alerts/status | GET | `/legal/alerts`, `/legal/status` | implemented — research, not legal advice |
| Geospatial providers/places | POST/GET | `/geo/providers`, `/geo/places` | implemented — own place index |
| Geocoding/GIS data | POST/GET | `/geo/geocode`, `/geo/data` | implemented — GeoJSON, provider-independent |
| Live feeds / map config / tiles | POST/GET | `/geo/feeds`, `/geo/map/config`, `/geo/tiles` | implemented — source + freshness |
| Location permissions | POST/GET | `/geo/permissions`, `/geo/location` | implemented — no covert precise tracking |
| Human public presence | POST/GET | `/human-presence/people`, `/profiles`, `/claims` | implemented — public only, no de-anonymisation |
| Assistant interoperability lab | POST/GET | `/assistant-lab/systems`, `/notes`, `/experiments` | implemented — internal research only |
| Digital assets / licences / IP | GET/POST/PATCH/DELETE | `/digital-assets`, `/digital-assets/{id}/licences`, `/digital-assets/{id}/ip` | implemented — owner entity required, no secrets |
| Domain registrations | GET/POST | `/domain-registrations` | implemented — metadata only, no live registrar call |
| Integrity status / manifest | GET/POST | `/integrity/status`, `/integrity/manifest` | implemented — best-effort, explicit approval |
| Knowledge contribution | POST | `/knowledge/contributions` | implemented — unverified, attributed, audited |
| Sync objects/status | POST/GET | `/sync/objects`, `/sync/status` | implemented — signed, untrusted data |
| Creator pending / challenge | GET | `/creator/requests`, `/creator/requests/{id}/challenge` | implemented — local review, no email |
| Creator signed decision | POST | `/creator/requests/{id}/decide` | implemented — ED25519 over one-time challenge |
| Creator messages | POST/GET | `/creator/messages/questions`, `/creator/messages` | implemented — informational only |
| Events | GET (SSE) | `/events` | implemented — durable audit trail with `?since=` replay |
| IPLCI rights assessment / gateway | POST | `/iplci/assessments`, `/iplci/gate/check` | implemented — tri-state rights, fail-closed |
| IPLCI training gate / lineage | POST | `/iplci/training/gate`, `/iplci/lineage` | implemented — independent approval, affected-by-revocation |
| IPLCI signed policies | POST/GET | `/iplci/policies`, `/iplci/policies/active` | implemented — human signer and approval reference required |
| IPLCI disputes / legal holds / audit | POST/GET | `/iplci/disputes`, `/iplci/legal-holds`, `/iplci/audit` | implemented — evidence preserved, allegations investigated |

All clients may send optional `CF-Access-Client-Id` / `CF-Access-Client-Secret` headers when the Core is behind Cloudflare Access (transport only; never authority).

Contributions always enter as `unverified`; verification remains a separate,
authorised operation. The SSE stream emits `audit` events with `id`,
`event_type`, `actor`, `target`, `details` and `created_at`; reconnect using the
last `created_at` as `?since=`. No reserved endpoints remain.

## Shared semantics

- **Scoped tokens:** separate credentials per project and per node; no token grants protected-core modification.
- **Offline queue:** tasks submitted while offline are queued locally per client and flushed on reconnect. Queue state is in-memory in v1; durable queue belongs to the local agent.
- **Node registration:** produces a *candidate* node only (OD-26). Trust, capabilities and the 1% resource reservation are core-controlled.
- **Auditing:** all mutating calls include an idempotency key and are logged server-side.
- **Parity:** TypeScript and Python expose the same conceptual surface: `core`, `tasks`, `events`, `nodes`, `resources`, `files`, `knowledge`, `sync`, `diagnostics`, `creator`, `integrity`, `uwaie`, `publicRecords`/`public_records`, `legal`, `geo`, `humanPresence`/`human_presence`, `assistantLab`/`assistant_lab`, `freeSandbox`/`free_sandbox`.
