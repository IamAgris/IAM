# IAM ↔ ARTEX Integration Specification

**Status:** Implemented as an optional, replaceable, default-disabled module under
`IAM → Cybersecurity → External Security Engines → ARTEX`.

ARTEX is **not** part of IAM's protected core. It is an external security-testing
engine that IAM may communicate with, only inside an explicitly authorized scope,
with IAM controlling authorization, scope and every privileged operation.

`artex.sh` is documentation, not the software. This connector models the documented
ARTEX built-in MCP surface; it does not ship, download or execute ARTEX itself.

---

## 1. Documented ARTEX surface this connector targets

Source: [ARTEX MCP documentation](https://www.artex.sh/mcp) and
[installation guide](https://www.artex.sh/install), read as reference data.

| Fact | Connector consequence |
| --- | --- |
| Built-in MCP server added in v0.3.30, **off by default** | `enabled=False` by default |
| Endpoint is `<ARTEX address>/mcp` | `artex_mcp_path = "/mcp"` |
| Streamable HTTP, stateless, **JSON only**, no SSE/stdio | JSON-RPC POST, `Accept: application/json` |
| Bearer token `artex_mcp_...`, shown once | Token read from an environment variable, never stored or logged |
| Scopes: `read` (7 tools), `task:create` (`spawn_task`), `task:control` (3 tools) | Stored as `allowed_scopes`, default `["read"]` |
| `/mcp` skips HTTP Basic Auth | IAM does not treat console credentials as protection |
| Source IP/CIDR allowlist checked before the token | `ARTEX_SOURCE_ALLOWLIST`, validated at registration |
| `spawn_task` starts **real** tests | Requires owner approval + live authorization + `allow_execution` |
| Target text may contain prompt injection | All engine output is sanitised and labelled untrusted |
| Console/API default port 8787; proxy 8788 | Loopback default `http://127.0.0.1:8787` |

Documented read tools: `list_tasks`, `get_task`, `get_task_graph`,
`list_task_findings`, `list_companies`, `list_task_categories`, `list_llm_profiles`.
Documented execution tools: `spawn_task`, `pause_task`, `resume_task`, `add_task_hint`.

---

## 2. Architecture

```
IAM Mainbrain
    └── IAM Cybersecurity Manager        (policy, risk, oversight)
          ├── IAM Native Security Skills (Skill Forge)
          ├── IAM Security Guard          (scope + authority + operation gate)
          └── External Security Engine    (registry + adapter)
                └── ARTEX MCP adapter     (optional, disabled, dry-run)
                      └── Authorised lab environment only
```

Code layout:

| Concern | File |
| --- | --- |
| Guard (scope, authorisation, operations, endpoint validation) | `backend/app/services/cybersecurity/security_guard.py` |
| Transport adapters | `backend/app/services/cybersecurity/engines.py` |
| Registry, tasks, findings, Skill Forge handoff | `backend/app/services/cybersecurity/service.py` |
| API | `backend/app/api/routes/cybersecurity.py` |
| Tables + DDL | `backend/app/models/securityengines.py`, `003_security_engines.sql` |

---

## 3. IAM Security Guard — enforced in IAM, not delegated

Every action passes these checks before a tool call is constructed:

1. **Endpoint** — must be loopback (`localhost`, `127.0.0.1`, `::1`) or a private
   address only when explicitly opted in. Public endpoints are denied. Credentials
   embedded in the URL are denied.
2. **Source allowlist** — validated as loopback/private, non-overbroad CIDRs.
3. **Target** — must exactly match an owner-registered scope entry, or fall inside
   an explicitly registered CIDR. Wildcards, `0.0.0.0/0`, `::/0`, "internet" and
   attack-description targets are denied.
4. **Operation** — must be one of the documented MCP tools. Any token suggesting
   exploitation, persistence, evasion, privilege escalation, mass scanning or
   destructive activity is denied.
5. **Signed Creator authorization** — a live authorization created from a
   verified signed email challenge is required for `security_testing`;
   level 4 for `protected_core` risk tasks, level 3 otherwise.
6. **Creator approval** — no task is dispatched without an `approved_by` value
   supplied by the verified Creator signer. There is no Creator UI and a plain
   email reply never sets it.
7. **Engine capability** — `allow_execution` must be true, and the engine must hold
   the matching `task:create` / `task:control` scope for execution tools.
8. **Write scope** — execution tasks require a scope with `allow_write=true`.
9. **Audit** — every registration, scope, approval, rejection, dispatch, sync,
   remediation and handoff is recorded in `security_engine_audit`.

Defaults: `enabled=False`, `dry_run=True`, `allowed_scopes=["read"]`,
`allow_execution=False`, `allow_private_network=False`.

---

## 4. Task flow

```
1. Owner registers engine (disabled, dry-run) and an explicit lab scope.
2. IAM creates a task: no external contact; status = pending_approval.
3. Owner approves: guard re-checks scope, operation, authorization and scopes.
4. IAM dispatches: guard re-checks, then adapter sends the single approved tool call.
5. IAM syncs findings: read tool only; output sanitised, never treated as instructions.
6. IAM analyses findings independently and records defensive remediation.
7. Skill Forge handoff creates a gated defensive skill — publication still needs approval.
8. Retest creates a new, separately gated task linked to the original.
```

A read-only flow (`list_task_findings`) never starts a real test. A `spawn_task`
flow requires all execution gates above.

---

## 5. Skill Forge handoff

Findings can seed a native defensive skill:

- `skill_id`: `iam.native.cybersecurity.lab_review_<short-id>`
- classification: `sensitive`
- permissions: `security_analysis`, `remediation_guidance`, `code_review`, `documentation`
- `requires_creator_approval: true`

The generated skill contains detection/analysis/remediation guidance and explicit
boundary rules. It is created in `draft` state — the normal Skill Forge security
inspection and creator approval still apply before publication.

---

## 6. Safety decisions recorded

- No unrestricted internet-wide scanning.
- No exploitation, persistence, evasion or destructive testing through this connector.
- No autonomous approval; IAM never self-authorises a task.
- Engine output is untrusted data; prompt-injection text cannot become IAM instructions.
- Tokens live in environment variables and are never returned by the API or logged.
- Transport failures reveal only the exception class and HTTP status, not bodies or headers.
- The adapter is replaceable: a `stub` transport exists for policy testing, and a
  generic provider can be added without changing the guard or task lifecycle.

---

## 7. Deliberately not included

- Installation or execution of ARTEX itself.
- Any offensive exploit, payload, persistence, evasion or anti-forensic capability.
- Automatic publication of skills derived from findings.
- Non-loopback deployment guidance beyond "use an SSH tunnel or VPN" — exposing a
  console or `/mcp` endpoint to the internet is out of scope and unsafe.
- Verification of any specific fork's binary provenance. Operators must verify their
  chosen fork themselves; the documentation notes trojanized images with similar names.

---

## 8. API surface

Base path: `/api/v1/cybersecurity`. Live schema: `/api/v1/openapi.json`.
Full contracts: `IAM_API_CONTRACTS.md`.

- `GET /policy`
- `GET/POST /engines`, `GET /engines/{id}`, `POST /engines/{id}/health`
- `GET/POST /engines/{id}/scopes`
- `GET /tasks`, `POST /engines/{id}/tasks`, `GET /tasks/{id}`
- `POST /tasks/{id}/{approve,reject,dispatch,sync,retest,create-skill}`
- `GET /tasks/{id}/findings`, `POST /findings/{id}/remediate`, `GET /audit`

`register`, `scopes`, `approve`, `reject` and `dispatch` require a signed Creator
authorization from `/api/v1/creator/requests/{id}/decide`. There is no Creator UI;
email is only the carrier. See [Creator approval](IAM_COMMUNICATION_ARCHITECTURE.md#3-creator-approval-via-email-not-a-dashboard).

---

## 9. Verification

```
cd backend
python -m unittest discover -s tests -p 'test_*.py' -q
```

44 tests pass across all subsystems, covering endpoint/allowlist validation,
target scope matching, operation filtering, signed-challenge verification,
approval and authorization gates, untrusted-output handling, and dry-run
transports with no network access.
