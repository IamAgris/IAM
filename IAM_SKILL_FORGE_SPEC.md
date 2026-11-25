# IAM Skill Forge — Implementation Specification

**Status:** Phase 1 (Foundation) and the core of Phase 2 (Security & Testing) implemented.
Phases 3–5 are scaffolded behind the same interfaces and remain future work.

Skill Forge is a permanent IAM core subsystem for creating, testing, versioning and
circulating IAM's own specialist capabilities. It is deliberately separate from the
legacy `/api/v1/skills` proficiency registry, which records *what IAM has learned*;
Skill Forge manages *capabilities IAM can invoke*.

A skill adds reusable instructions, resources and scripts. It does **not** retrain or
upgrade IAM's underlying model.

---

## 1. Components and where they live

| Component | Implementation |
| --- | --- |
| Skill Forge Engine | `backend/app/services/skillforge/engine.py` |
| Capability Discovery | `SkillForgeService.discover_gaps()` (uses `capability_definitions` + assessments) |
| Skill Architect / Builder | `SkillBuildRequest` + `engine.build()` / `engine.create_version()` |
| Skill Testing Engine | `engine.run_tests()` + `skillforge_test_results` |
| Security Validator | `backend/app/services/skillforge/security.py` |
| Skill Registry | `backend/app/models/skillforge.py` → `skillforge_packages` |
| Skill Runtime authority | `PermissionManager.effective_permissions()` / `can_use_network()` / `can_use_filesystem()` |
| Version Manager | `skillforge_versions` + `archived/<skill-id>/<version>/` |
| Skill Learning Engine | Scaffold — feedback/test results feed future improvement passes |
| Creator Approval Gateway | `SkillForgeService.approve()` / `grant()` / `revoke()` |
| Audit trail | `skillforge_audit_events` (append-only by convention) |

On-disk store: `iam/skills/` (configurable via `SKILLFORGE_ROOT`).

```
iam/skills/
├── native/<category>/<name>/   IAM's own skills
├── imported/<provider>/...     verified external skills
├── pending/                    unverified imported candidates
├── quarantine/                 failed / suspicious / revoked skills
└── archived/<skill-id>/<version>/  immutable snapshots for rollback
```

Each package contains `SKILL.md`, `manifest.json`, `permissions.json`, and
`resources/`, `scripts/`, `tests/` directories.

---

## 2. Lifecycle and state machine

```
draft ──> testing ──> pending_approval ──> published ──> active
  │           │             │                 │           │
  └───────────┴─────────────┴─────────────────┴───────────┘
                     quarantine / archived (any state)
```

Transitions are enforced by `PermissionManager.require_transition()`. A skill can
never jump from `draft` to `active`. Invalid or suspicious packages are quarantined
automatically by `validate()`.

Operations:

1. **Identify** a gap via `GET /skill-forge/gaps`.
2. **Build** with `POST /skill-forge/skills` (also used to register a higher version).
3. **Inspect** with `POST /skills/{id}/validate` — manifest + static security scan.
4. **Test** with `POST /skills/{id}/test` — structural and policy tests.
5. **Approve** (privileged classes only) with `POST /skills/{id}/approve`.
6. **Publish** with `POST /skills/{id}/publish`.
7. **Activate** with `POST /skills/{id}/activate`.
8. **Monitor / improve** — versions, test history, audit, quarantine and rollback.

---

## 3. Classification and permissions

| Level | Class | Approval |
| --- | --- | --- |
| 1 | `personal` — knowledge, reasoning, ordinary workflows | IAM can create and publish |
| 2 | `operational` — approved tools and automation | IAM can create; permission checks apply |
| 3 | `sensitive` — security, infrastructure, financial or external operations | Explicit creator approval |
| 4 | `protected_core` — identity, constitution, core architecture | Creator-only authorisation |

Enforcement rules (all implemented):

- A manifest is **descriptive only**. Authority comes from `PermissionManager`,
  signed Creator authorizations (`creator_authorizations`) and
  `skillforge_permission_grants`. There is no Creator UI; OD-19 approvals travel
  by IAM-domain email and are proven by an ED25519 signature over a one-time challenge.
- `protected_core` skills cannot be authored by IAM (`created_by` must be `creator`).
- Sensitive and protected-core skills must declare `requires_creator_approval=true`.
- Publishing a level-3 skill requires a verified signed Creator authorization for
  `skillforge.publish`; level-4 uses the same signed flow at level 4. A plain
  email reply never authorises publication.
- Privileged permissions (`security_analysis`, `external_communication`, etc.) are
  stripped from runtime authority unless an owner has issued a matching grant.
- Network access is never implied by the manifest flag alone.
- Imported skills are staged in `pending/` and promoted only on publication.
- Quarantined skills cannot be tested or activated.
- Every state change writes an audit event; every version is checksummed and archived.

---

## 4. Static security inspection

`SecurityValidator` scans text files without executing them. Blocking findings
prevent build/validation and force quarantine. Detected patterns:

- prompt injection and role override
- self-escalation ("grant yourself", "bypass approval", "modify protected core")
- hardcoded credentials and private keys
- destructive shell commands and pipe-to-shell downloads
- dynamic code execution and OS privilege requests

Skill file paths are re-validated against the skill root before every write, so a
crafted manifest cannot escape `iam/skills/`.

---

## 5. Data model

| Table | Purpose |
| --- | --- |
| `skillforge_packages` | One row per skill, current version and status |
| `skillforge_versions` | Immutable version snapshots and checksums |
| `skillforge_test_results` | Evidence from each test run |
| `skillforge_audit_events` | Append-only state-change trail |
| `skillforge_permission_grants` | Owner-issued, skill-scoped grants outside the skill |

See `backend/app/db/migrations/002_skillforge.sql` for the PostgreSQL DDL.
Development startup uses `Base.metadata.create_all()`.

---

## 6. API surface

Base path: `/api/v1/skill-forge`. Full contracts are in `IAM_API_CONTRACTS.md`;
the live schema is generated at `/api/v1/openapi.json`.

- `GET /policy`, `GET /gaps`
- `GET/POST /skills`, `GET /skills/{id}`
- `POST /skills/{id}/{validate,test,approve,publish,activate,quarantine,rollback}`
- `GET /skills/{id}/{versions,audit,tests,grants,effective-permissions}`
- `POST /skills/{id}/grants`, `DELETE /skills/{id}/grants/{permission}`

`POST /skills/{id}/approve` only **sends the Creator email request** (no approval
is granted there). Publication requires a signed authorization created by
`/api/v1/creator/requests/{id}/decide`. `grants` must likewise be reached only
through the signed-email gateway. No Creator UI exists (OD-19).

---

## 7. Roadmap status

| Phase | Status |
| --- | --- |
| 1 — Foundation: registry, manifest, folder structure, builder, validation, versions | **Done** |
| 2 — Security & testing: permissions, static inspection, tests, quarantine, rollback | **Core done** |
| 3 — Autonomous development: automated design, improvement, duplicate detection | Scaffold (`discover_gaps`, version/tests hooks) |
| 4 — External ecosystem: OpenAI/NVIDIA/Google/xAI (Grok) and community skill adapters with verification | Folder + origin/provider support; adapters not implemented. External skill packages (e.g. xAI/Grok skills) are candidate sources — see Doc 18 §15 |
| 5 — IAM network: P2P skill exchange, signed releases, trust policy | Not implemented |

### Remaining work

1. ~~Sandboxed execution for skill scripts~~ — implemented in `IAM_SKILL_RUNTIME_SPEC.md`
   (disabled by default, stub adapter, optional no-network Docker adapter).
2. ~~Skill Runtime consuming `effective_permissions()`~~ — implemented; next step is
   testing the Docker adapter against a real skill script in a controlled environment.
3. Provider-specific import adapters and signature verification, including external skill/agent package ecosystems such as xAI/Grok skills. Verify all provider URLs, package formats and directory conventions live; do not freeze source-material claims as facts.
4. Feedback-driven Skill Learning Engine and duplicate/conflict detection.
5. User-facing Marlow view of the Forge lifecycle (not a Creator approval UI).
6. ~~Email transport wiring~~ — implemented; deployment still needs credentials and
   the signer callback pointed at `/api/v1/creator/gateway/decide`.

---

## 8. Non-negotiable rules

1. IAM can create, edit and test its own ordinary skills without per-step approval.
2. IAM cannot authorise protected-core changes — creator-only.
3. Skills cannot override IAM's constitution or security policy.
4. Imported skills are untrusted until verified and promoted.
5. Skills cannot silently acquire permissions; grants live outside the package.
6. Every skill has version history and an audit trail.
7. Failed or suspicious skills are isolated and disabled.
8. No skill can bypass creator approval by invoking another skill.
9. Skill execution authority is enforced independently of model instructions.
10. IAM can disable, revoke or roll back any skill.
11. External skill packages (including xAI/Grok skills) are untrusted until verified: no blind installation, no script execution without security review, no permissions implied by the manifest, and original author/licence/source must be preserved.

---

## 9. Verification

Unit tests: `backend/tests/test_skillforge.py` (20 tests, no database required).
The full suite includes signed-challenge and cybersecurity guard tests (44 total).

```
cd backend
python -m unittest discover -s tests -p test_skillforge.py -v
```
