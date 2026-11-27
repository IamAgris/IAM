# IAM — API Contracts

**Version:** 1.0 · 24 November 2026  
**Status:** Provisional — pending owner decisions  
**Parent:** `IAM_ARCHITECTURE_GAP_ANALYSIS.md` (resolves M-06, C-10)  
**Base URL:** `/api/v1` · **Frontend proxy:** Next.js rewrites `/api/*` → backend

---

## 1. Conventions

- JSON bodies; UTF-8; ISO-8601 timestamps (UTC).
- All IDs are UUID strings except `permanent_id` (ULID).
- All visitor-scoped endpoints require `X-Session-Token` header; server derives `visitor_id` from the token — never from a client-supplied visitor ID.
- All owner endpoints require the owner credential and are rejected for public sessions.
- Errors: `{ "detail": str, "code": str, "request_id": str }`.
- Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`.
- Idempotency: POST endpoints that create resources accept `Idempotency-Key`.

---

## 2. Authority and identity

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/identity/` | session | Current IAM identity |
| POST | `/identity/` | owner | Initialize identity (once) |
| PATCH | `/identity/` | owner | Update identity (history recorded) |
| GET | `/identity/history` | session | Identity change history |
| GET | `/governance/boundaries` | session | Authority ladder |
| POST | `/governance/check-authority` | session | `{action_type, requested_level}` → permitted? |
| GET | `/governance/security-boundaries` | session | Immutable boundaries |
| POST | `/governance/initialize` | admin | Install defaults |

Legacy `/external-presence/approvals` was removed. Integration activation now
requires a signed Creator authorization for `external_presence.connect_integration`;
`POST /external-presence/integrations/{id}/request-approval` sends the email request.

Creator authority is **only** `/creator/requests/{id}/decide` via signed email.
The legacy `/owner` routes, service and model are removed; no second authority path exists.
| POST | `/auth/bootstrap` | bootstrap key | Create first scoped credential (key returned once) |
| GET | `/auth/me` | credential | Current credential identity |
| GET/POST | `/auth/credentials` | admin | List/create scoped API credentials |
| POST | `/auth/credentials/{name}/revoke` | admin | Revoke a credential |
| GET | `/skill-runtime/policy` | admin | Runtime posture and container limits |
| GET | `/skill-runtime/capabilities/{id}` | admin | Effective permissions for a skill |
| POST | `/skill-runtime/invoke` | admin | Gated skill invocation |
| GET | `/skill-runtime/executions` | admin | Invocation audit trail |
| GET | `/deployment/preflight` | admin | Redacted configuration readiness report |
| GET | `/creator/policy` | session | Email-only Creator approval, no UI |
| POST | `/creator/requests` | session | Create approval request; `channel` = `creator_email` (default) or `creator_cli` / `creator_webhook` / `creator_node` / `creator_file` (no email required) |
| GET | `/creator/requests` | session | List requests |
| GET | `/creator/requests/{id}` | session | Request detail |
| POST | `/creator/requests/{id}/decide` | internal signed | Verify ED25519 challenge signature; only authority source |
| POST | `/creator/gateway/decision` | HMAC gateway | External email/signer webhook; HMAC over raw body + signed challenge |
| GET | `/creator/requests/{id}/challenge` | session | Challenge hash and messages for the external signer |
| POST | `/creator/requests/{id}/deliver` | session | Retry one queued Creator email |
| GET | `/creator/outbox` | session | Delivery status and retry history |
| POST | `/creator/outbox/retry` | worker | Retry all pending/failed deliveries |
| GET | `/creator/audit` | session | Creator-channel audit |
| POST | `/creator/authorizations/{id}/revoke` | signed gateway | Revoke a signed authorization |
| POST | `/creator/messages/questions` | session | IAM asks the Creator a question by email — informational, never authority |
| POST | `/creator/messages/status` | session | IAM sends a progress update by email — informational |
| GET | `/creator/messages` | session | Message history with authority markers |
| POST | `/creator/messages/replies` | HMAC gateway | Record a Creator reply — informational, never authority |

**OD-19:** Creator approval is email-based, never a dashboard. A plain email reply
must not authorise anything; only `/creator/requests/{id}/decide` with a valid
signature over the one-time challenge creates authority.

---

## 3. Global access (public)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/access/visitors` | none | Get/create pseudonymous visitor |
| POST | `/access/sessions` | none | Create isolated session; server resolves GeoIP from request IP |
| GET | `/access/sessions/{token}/context` | session | Location + permissions + mode |
| PATCH | `/access/sessions/mode` | session | `{session_token, mode}` focus/recall/create |
| POST | `/access/messages` | session | Store message in own thread only |
| GET | `/access/sessions/{token}/messages` | session | Own messages only |
| POST | `/access/consent` | session | Record consent |
| POST | `/access/memory-permissions` | session | Set memory tier permissions |
| PATCH | `/access/location` | session | Correct region/language/timezone |
| GET | `/access/visitors/{token}/data` | token | Inspect all visitor data (OD-05) |
| PATCH | `/access/visitors/{token}/data` | token | Correct preferences and memory permissions (OD-05) |
| DELETE | `/access/visitors/{token}` | session | Delete all visitor data |

**Isolation invariant:** the server derives `owner_id` from `X-Session-Token` on every request. Client-supplied `visitor_id` is ignored. Repository layer enforces `owner_id` filter on every conversation query.

---

## 4. Conversation and streaming

| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/conversations/` | Threads (owner-scoped) |
| GET | `/conversations/{id}/messages` | Messages (owner-scoped) |
| POST | `/conversations/messages` | Store message |
| POST | `/conversations/{id}/chat` | **Non-streaming** chat fallback |
| POST | `/conversations/{id}/chat/stream` | **SSE streaming chat** (canonical) |
| POST | `/tone/analyze` | Doc 17 tone/influence interpretation (possibilities, not diagnoses) |
| POST | `/tone/discussion` | Discussion analysis with possible tone-shift flags |
| POST/GET | `/tone/records` | Store / list tone analysis evidence |

### SSE event schema (canonical — resolves C-10)

`Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`.

```
event: start
data: {"request_id":"...","model":"nvidia/...","provider":"nvidia"}

event: context
data: {"memories":[...],"mode":"recall","region":"ZA"}

event: delta
data: {"text":"IAM "}

event: delta
data: {"text":"is "}

event: tool
data: {"name":"browser.search","status":"running","id":"..."}

event: done
data: {"finish_reason":"stop","usage":{"tokens_in":12,"tokens_out":48,"cost_usd":0.0001}}

event: error
data: {"code":"provider_unavailable","message":"...","fallback":"qwen3.5-9b"}
```

**Client requirements:** parse `event:` lines; accumulate `delta.text`; handle `error` with automatic retry once using `fallback`; support `AbortController` cancellation; reconnect using `Last-Event-ID` to resume from a retained event.

**WebSocket** is reserved for voice/real-time sessions (`/voice/session`), not text chat.

---

## 5. Intelligence and models

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/models/` | List available models via LiteLLM |
| POST | `/models/chat` | Backward-compatible non-stream proxy |
| POST | `/models/router/initialize` | Register providers |
| POST | `/models/router/discover/nvidia` | Discover free NVIDIA endpoints |
| GET | `/models/router/providers` | List providers |
| GET | `/models/router/models?provider=` | List discovered models |
| POST | `/models/router/select` | `{task_type, capabilities, allow_paid}` → selected model |
| GET | `/models/router/history` | Routing decisions |
| POST | `/models/discovery/{provider}` | Dual-source discovery (provider catalogue + Models.dev metadata); returns registry entries, not verified endpoints |
| POST | `/models/credentials` | Register an encrypted provider connection key (signed authorization required; never returns the secret) |
| GET | `/models/credentials/health?provider=` | Read-only key health summary; no ciphertext or plaintext |
| POST | `/models/credentials/{key_id}/disable` | Disable a connection (signed authorization required) |
| POST | `/models/credentials/{key_id}/rotate` | Rotate an encrypted connection secret (signed authorization required) |
| POST | `/models/credentials/{key_id}/health?healthy=` | Mark a connection healthy/unhealthy for per-key failover |

**Rule:** `allow_paid` defaults false; true requires a signed Creator authorization record.
**Rule (OD-51):** paid inference additionally requires a fail-closed usage decision — signed authorization, a determinable cost and a positive remaining limit. No browser ever receives a credential.
**Vault registration:** `POST /models/credentials` requires an active signed Creator authorization for action `model.provider_key_manage` (create via `POST /creator/requests`, sign the challenge with the OD-03 hardware signer, then `POST /creator/requests/{id}/decide`). Provider-side NVIDIA keys are separate: they live only in LiteLLM config via `os.environ/NVIDIA_API_KEY` / `NVIDIA_API_KEY_1…4` and are never handled by the browser or the IAM vault.
**Rule (OD-51 §4.4):** `POST /models/chat` and `/models/chat/stream` accept optional `delegation_tasks: [{task, model?, role?}]`. Fan-out is bounded to 3 concurrent agents, 120 s per agent, 512 MB per agent and 4 calls per request. Each tasks requires its own signed `model.delegate` authorization; results are independently reviewed by the local primary and only accepted findings are returned as labelled, unverified context. No private memory is sent to specialists.

---

## 6. Memory, knowledge, learning

| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/memory/` | List/store memory (owner-scoped) |
| POST | `/memory/search` | pgvector semantic search |
| POST | `/memory/verify/{id}` | Set verification status |
| GET/POST | `/knowledge/` | Knowledge items with provenance |
| POST | `/knowledge/verify/{id}` | Verify knowledge |
| GET/POST/PATCH | `/languages/` | Language profiles |
| GET/POST/PATCH | `/skills/` | Skills (proficiency registry) |
| GET/POST | `/capabilities/` | Capability registry + assessments |
| POST/GET | `/technology-registry/` | Doc 20 third-party technology registry (records only; no install/execute) |
| GET | `/technology-registry/{id}` | Technology record detail |
| PATCH | `/technology-registry/{id}/state` | Lifecycle transition (no direct researched → integrated) |
| POST | `/technology-registry/{id}/benchmarks` | Record benchmark evidence |
| POST/GET | `/free-nodes/` | Doc 19 free node candidates (usefulness gate; no provisioning) |
| POST | `/free-nodes/{id}/verify-terms` | Record live-verified free-tier evidence |
| PATCH | `/free-nodes/{id}/status` | Lifecycle status (deploy requires verified terms) |
| POST | `/free-nodes/{id}/migration-plan` | Expiry alarm + migration before free allowance lapses |
| GET | `/skill-forge/policy` | Skill classification, permission and transition policy |
| GET | `/skill-forge/gaps` | Capability discovery — suggested native skills |
| GET/POST | `/skill-forge/skills` | List/build skill packages (POST also creates new versions) |
| GET/POST | `/skill-forge/skills/{id}/validate` | Static security + manifest inspection |
| POST | `/skill-forge/skills/{id}/test` | Structural/policy test suite |
| POST | `/skill-forge/skills/{id}/approve` | Creator-only approval gateway |
| POST | `/skill-forge/skills/{id}/publish` | Publish after tests + authority checks |
| POST | `/skill-forge/skills/{id}/activate` | Activate a published skill |
| POST | `/skill-forge/skills/{id}/quarantine` | Isolate a failed or revoked skill |
| POST | `/skill-forge/skills/{id}/rollback` | Restore an archived version |
| GET | `/skill-forge/skills/{id}/versions`, `/audit`, `/tests` | History and evidence |
| GET/POST/DELETE | `/skill-forge/skills/{id}/grants` | Owner-issued scoped permission grants |
| GET | `/skill-forge/skills/{id}/effective-permissions` | Runtime authority check |
| GET | `/cybersecurity/policy` | IAM-enforced defensive-only policy |
| GET/POST | `/cybersecurity/engines` | Register/list external security engines |
| GET/POST | `/cybersecurity/engines/{id}/scopes` | Authorised target allowlist |
| POST | `/cybersecurity/engines/{id}/health` | Read-only engine health check |
| GET/POST | `/cybersecurity/tasks`, `/cybersecurity/engines/{id}/tasks` | List/create gated tasks |
| POST | `/cybersecurity/tasks/{id}/{approve,reject,dispatch,sync,retest}` | Task lifecycle |
| GET | `/cybersecurity/tasks/{id}/findings` | Normalised untrusted findings |
| POST | `/cybersecurity/findings/{id}/remediate` | Defensive remediation guidance |
| POST | `/cybersecurity/tasks/{id}/create-skill` | Skill Forge handoff (gated) |
| GET | `/cybersecurity/audit` | Engine/task audit trail |
| POST | `/capabilities/assess` | Measurable assessment |
| POST | `/reflection/` | Reflection entry |
| GET | `/reflection/principles` | Operating principles |

---

## 7. Autonomy

| Method | Path | Purpose |
|--------|------|---------|
| GET/POST/PATCH | `/autonomy/goals/` | Goals + lifecycle |
| POST/GET | `/autonomy/goals/{id}/plans` | Plans |
| GET/POST/PATCH | `/autonomy/tasks/` | Tasks |
| POST/GET | `/autonomy/tasks/{id}/executions` | Execution records |
| GET/POST | `/autonomy/decisions/` | Decision records |
| GET/POST/PATCH | `/autonomy/tools/` | Tool registry + permissions |
| GET/POST | `/autonomy/schedule/` | Scheduled activities |
| GET | `/autonomy/status` | Worker state |
| GET/POST | `/life/cycle`, `/life/history` | Life management |

---

## 8. Internet and external AI

| Method | Path | Purpose | Gate |
|--------|------|---------|------|
| POST | `/internet/initialize` | Install permission gates | owner |
| GET | `/internet/permissions` | List gates | session |
| POST | `/internet/permissions/check` | Check action | session |
| POST | `/internet/sessions` | Create browsing session | session |
| POST | `/internet/browse` | Navigate/click/type/submit/screenshot | context-gated |
| POST | `/internet/search` | Web search | autonomous |
| POST | `/internet/accounts` | Register online account | **signed Creator authorization** |
| POST | `/internet/publish` | Publish content | **signed Creator authorization** |
| POST | `/internet/monitor` | Add monitored target | session |
| POST | `/internet/files` | Record retrieved file | session |
| GET | `/internet/events` | Activity audit | session |
| POST | `/research/` | Full research workflow | session |
| POST | `/research/search`, `/browse`, `/verify` | Research steps | session |
| GET/POST/PATCH | `/network/agents` | AI agent registry | session |
| POST | `/network/agents/{id}/message` | Communicate with external AI | session + validation |
| GET | `/network/interactions` | Communication audit | session |
| POST | `/network/trust` | Record trust assessment | session |
| GET/POST | `/network/collaborations` | Delegated tasks | **signed Creator authorization if high-impact** |
| POST | `/network/agents/{id}/verify` | Record independent identity verification evidence (self-reported claims never auto-verify) | session |
| POST/GET | `/network/agents/{id}/interviews` | Record / list structured interviews with provenance and risk markers | session |
| GET | `/network/agents/{id}/profile` | AI relationship registry profile (Doc 18 §7) | session |

---

## 9. Multimodal

| Method | Path | Content |
|--------|------|---------|
| POST | `/voice/speech-to-text` | multipart audio |
| POST | `/voice/text-to-speech` | JSON text → base64 audio |
| POST | `/voice/voice-activity` | multipart audio |
| POST | `/vision/understand-image` | multipart image |
| POST | `/vision/analyze-video` | multipart video |

All uploads: size limits, format validation, malware scan, owner association, retention policy.

---

## 10. External presence and economy

| Domain | Paths |
|--------|-------|
| External presence | `/external-presence/website`, `/email`, `/integrations`, `/approvals` |
| Economy | `/economics/opportunities`, `/economics/projects`, `/finance/ledger`, `/finance/budgets` |
| Resilience | `/resilience/health`, `/recovery`, `/backup-verify`, `/incidents`, `/credential-rotate` |

---

## 11. Health and operations

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/health/ready` | Readiness (DB, Redis, model gateway) |
| GET | `/health/live` | Liveness only |
| GET | `/metrics` | Prometheus-format operational metrics |

---

## 12. Security requirements for all endpoints

1. TLS in production; secure cookies for visitor sessions.
2. Rate limits per visitor, per IP-derived key, and global.
3. Input validation via Pydantic schemas on every route.
4. Owner-only routes reject public session tokens.
5. Provider keys never returned in any response.
6. Every mutating request writes to `audit_events`.
7. Authority re-checked at execution time for async work (S-13).
8. CORS restricted to configured frontend origin.

---

## 13. Contract test expectations

For each endpoint: success case; unauthenticated case; wrong-owner case (must 404/403, never leak another visitor's data); validation failure; rate-limit breach; audit event emitted. Isolation tests are mandatory for all visitor-scoped endpoints (S-06).
