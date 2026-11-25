# Skill Runtime Specification

**Status:** Implemented, disabled by default, verified against live PostgreSQL.

Skill Forge creates, tests, versions and gates packages. Skill Runtime is the
separate component that actually invokes them. It never trusts the package's own
instructions: authority comes from `effective_permissions()`, owner-issued grants,
the package checksum and the IAM Security Guard rules.

## 1. Defaults

| Setting | Default | Effect |
| --- | --- | --- |
| `SKILL_RUNTIME_ENABLED` | `false` | No invocation is possible until explicitly enabled |
| `SKILL_RUNTIME_ADAPTER` | `stub` | Simulates execution; nothing is run |
| `SKILL_RUNTIME_IMAGE` | `python:3.12-alpine` | Image used only by the Docker adapter |
| `SKILL_RUNTIME_TIMEOUT_SECONDS` | `30` | Hard per-invocation timeout |
| `SKILL_RUNTIME_MEMORY` / `SKILL_RUNTIME_CPUS` | `256m` / `0.5` | Container resource caps |

Network-enabled execution is **not supported** in this deployment; a skill with a
network grant is refused at invocation.

## 2. Gates applied before execution

1. Runtime is enabled.
2. Package exists and is `active`.
3. Requested permission is present in `effective_permissions()` (manifest ∩ grants ∩ policy).
4. No network access is requested.
5. On-disk checksum matches the registered checksum (tamper detection).
6. Scripts must be relative paths under `scripts/`, must exist inside the package,
   and pass a fresh security inspection.
7. Every invocation — allowed, denied or failed — is written to
   `skill_runtime_executions`.

Denials return HTTP 403 and are audited with the reason.

## 3. Adapters

- **stub** — returns a simulated result; used for policy testing.
- **docker** — runs one script in a disposable container:
  `--network none`, `--read-only`, non-root user, `no-new-privileges`,
  `--pids-limit 64`, memory/CPU caps and a timeout. The skill directory is mounted
  read-only at `/skill`. Arguments are passed as a bounded JSON environment variable.

A new transport can be added by implementing `SkillRuntimeAdapter` without
changing the policy gates.

## 4. Files

| Concern | File |
| --- | --- |
| Service and gates | `backend/app/services/skillruntime/service.py` |
| Adapters | `backend/app/services/skillruntime/adapters.py` |
| Model / DDL | `backend/app/models/skillruntime.py`, `009_skill_runtime.sql` |
| API | `backend/app/api/routes/skillruntime.py` |
| Tests | `backend/tests/test_skill_runtime.py`, integration check |

## 5. API

Base path `/api/v1/skill-runtime` (admin scope):

- `GET /policy`
- `GET /capabilities/{skill_id}`
- `POST /invoke` — `{skill_id, permission, script?, arguments?}`
- `GET /executions?skill_id=`

## 6. Verification

- 65 unit tests pass (including script traversal rejection and container flags).
- Postgres integration: gated invocation succeeded; an ungranted permission was
  denied and recorded. Full suite exits 0 with 141 tables.

## 7. Remaining work

1. Enable the Docker adapter in a controlled environment and test a real skill script.
2. Add a narrowly scoped, explicitly configured isolated network for skills that
   legitimately need network access.
3. Stream execution logs to the audit trail rather than storing truncated output.
4. Add per-skill invocation limits to `RateLimiter`.
