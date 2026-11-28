# API Authentication and Rate Limiting

**Status:** Implemented and verified against live PostgreSQL.

## 1. Model

All non-public API routes require a scoped API credential. Credentials are
random `iam_…` keys; only their SHA-256 hash is stored. The plaintext is returned
once at creation. Creator authority (OD-19) is independently enforced by signed
email challenges — an admin API key can call Creator endpoints but cannot create
approval or authorization by itself.

| Scope | Rank | Typical use |
| --- | --- | --- |
| `user` | 1 | Conversations, memory, skills, capabilities, languages, identity, interface |
| `service` | 3 | Internal service/worker calls — same reach as `operator`, distinct audit identity |
| `operator` | 3 | Autonomy, research, voice, vision, world, life, default |
| `admin` | 4 | Skill Forge, cybersecurity, Creator, governance, internet, network, finance, development, setup |

These scopes authenticate backend and service callers. They are **not** browser
roles or login accounts. The frontend is open to use: it holds one user-scope
credential server-side and acts on behalf of visitors, who never authenticate.
Every non-user capability is reached through the email/signed-challenge flow or a
server-side service credential.

Public paths: `/`, `/health`, `/api/v1/docs`, `/api/v1/redoc`,
`/api/v1/openapi.json`, `/api/v1/access/*`, `/api/v1/auth/bootstrap`, and
`/api/v1/creator/gateway/decision` (protected by HMAC instead).

## 2. Files

| Concern | File |
| --- | --- |
| Model | `backend/app/models/auth.py` |
| DDL | `backend/app/db/migrations/007_api_credentials.sql` |
| Path policy | `backend/app/core/auth_policy.py` |
| Rate limiter | `backend/app/core/rate_limit.py` |
| Credential service | `backend/app/services/auth_service.py` |
| Middleware | `backend/app/api/middleware/auth_middleware.py` |
| Routes | `backend/app/api/routes/auth.py` |
| Tests | `backend/tests/test_auth.py`, integration check |

## 3. Bootstrap

1. Set `IAM_BOOTSTRAP_API_KEY` in the deployment environment.
2. `POST /api/v1/auth/bootstrap` with header `X-Bootstrap-Key` and body
   `{"name": "main-admin", "scope": "admin"}`.
3. Store the returned key in the operator's secret manager. It is shown once.
4. Create further keys with `POST /api/v1/auth/credentials` using the admin key.

`AUTH_ENABLED=false` disables the middleware entirely and is intended only for
local debugging — never use it in a deployed environment.

## 4. Endpoints

- `GET /api/v1/auth/me` — current credential
- `POST /api/v1/auth/credentials` — create scoped key (admin)
- `GET /api/v1/auth/credentials` — list keys, hashes never returned (admin)
- `POST /api/v1/auth/credentials/{name}/revoke` — revoke a key (admin)

Send the key as `Authorization: Bearer <key>` or `X-API-Key: <key>`.

## 5. Rate limiting

Sliding window per credential + client IP, default 120 requests per minute.
Exceeding it returns `429` with `Retry-After`.

`RATE_LIMIT_BACKEND=memory` (default) uses in-process state; `redis` uses a shared
Redis sorted-set window across replicas, with automatic fallback to local state if
Redis is temporarily unavailable. The Redis path is exercised by the Postgres
integration check when `REDIS_URL` is provided.

## 6. Verification

- 61 unit tests pass, including path/scope mapping and limiter behaviour.
- The Postgres integration check exercises HTTP end-to-end: unauthenticated
  admin path → 401; admin key → 200; user key on admin path → 403; public health → 200.

## 7. Deployment caveats

- The middleware is only as strong as the deployment boundary for
  `POST /api/v1/creator/gateway/decision` and `/api/v1/auth/bootstrap`; restrict
  both at the network/proxy layer.

## 8. Retired legacy authority path (OD-03/OD-04)

`/api/v1/owner/authorizations` is no longer an authority source. Creation of
standing grants returns `410`; `POST /authorizations/check` always returns
`authorized: false`; `GET /authorizations` is a historical read-only view and
`DELETE` remains available for cleanup. All consequential actions use
`CreatorApprovalService.check_authorization()` with an active Ed25519-signed
Creator authorization scoped to the specific action/target. The autonomy graph
uses `GovernanceService` rather than the retired grants.
- Frontend calls to admin endpoints must supply an appropriately scoped key;
  the current user-facing pages are still placeholders. There is no Creator UI —
  all creator decisions arrive through the signed email gateway.
