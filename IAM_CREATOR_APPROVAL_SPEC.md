# Creator Approval by Email — Implementation Specification

**Status:** Implemented. OD-18/OD-19 are now enforced in code: there is no Creator
dashboard, and email is the carrier — not the proof — of authority.

## 1. Rule

An ordinary email reply never authorises anything. Authority exists only after:

1. IAM creates an approval request containing the exact action, reason, consequences,
   risk level, target and expiry.
2. The request is delivered to the verified Creator email address on IAM's domain.
3. The Creator returns a signature from the external hardware signer (OD-03) over
   `sha256(canonical_challenge_json) + "|" + decision`.
4. IAM verifies the signature against the configured ED25519 public key, checks the
   one-time challenge is unconsumed and unexpired, and only then creates a scoped,
   short-lived `creator_authorizations` record.

## 2. Components

| Concern | File |
| --- | --- |
| Request/challenge/signature/authority service | `backend/app/services/creatorapproval_service.py` |
| Email transports | `backend/app/services/creator_email.py` |
| Inbound gateway auth | `backend/app/services/creator_gateway.py` |
| Models | `backend/app/models/creatorapproval.py` |
| DDL | `backend/app/db/migrations/004_creator_email_approval.sql`, `006_creator_email_outbox.sql` |
| API | `backend/app/api/routes/creatorapproval.py` |
| Tests | `backend/tests/test_creatorapproval.py`, `test_creator_email.py` |

Tables: `creator_requests`, `signed_challenges`, `creator_approvals`,
`creator_authorizations`, `creator_email_outbox`, `communication_audit`.

## 3. Configuration

| Setting | Purpose |
| --- | --- |
| `CREATOR_EMAIL` | Verified Creator address (required to create requests) |
| `CREATOR_EMAIL_DOMAIN` | IAM domain used for the approval channel |
| `CREATOR_PUBLIC_KEY` | ED25519 public key, PEM or base64 raw |
| `CREATOR_SIGNER_ID` | Expected signer identifier |
| `CREATOR_CHALLENGE_TTL_SECONDS` | One-time challenge lifetime (default 3600) |
| `CREATOR_AUTHORIZATION_TTL_SECONDS` | Resulting scoped authorization lifetime (default 3600) |
| `CREATOR_EMAIL_TRANSPORT` | `log` (default, sends nothing), `smtp` or `http` |
| `CREATOR_EMAIL_FROM`, `CREATOR_SMTP_*` | SMTP delivery; password from `CREATOR_SMTP_PASSWORD` |
| `CREATOR_EMAIL_HTTP_URL`, `CREATOR_EMAIL_HTTP_TOKEN` | HTTP email gateway delivery |
| `CREATOR_GATEWAY_SECRET` | HMAC secret for inbound signed decisions; empty disables the gateway |

With no public key configured, all decision attempts fail closed. With no
gateway secret configured, the inbound decision endpoint is disabled. Credentials
are read from the environment and never stored in the database or returned by the API.

## 4. API

Base path: `/api/v1/creator`.

- `GET /policy` — declares `creator_ui: false` and `plain_email_reply_authorises: false`
- `POST /requests` — IAM creates a request; response includes the email package
- `GET /requests`, `GET /requests/{id}` — request inspection
- `POST /requests/{id}/decide` — internal signed decision; `{decision, signature, signer_id}`
- `POST /gateway/decision` — external webhook: HMAC `X-Creator-Signature` over the raw
  body plus the ED25519 challenge signature. Returns 503 when no gateway secret is set.
- `GET /requests/{id}/challenge` — challenge hash, nonce and messages for the external signer
- `POST /requests/{id}/deliver` — retry one queued email
- `GET /outbox`, `POST /outbox/retry` — delivery state and worker retry (CM-10)
- `GET /audit` — all three communication channels are audited
- `POST /authorizations/{id}/revoke` — revocation

This is a backend gateway, not a UI. The frontend remains user-only. The legacy
`/api/v1/owner` routes, service and model were removed in this cleanup; migration
005 renames the old table to `legacy_owner_authorizations` so historical rows are
preserved as an inert archive rather than deleted.

## 5. Consumers

| Consumer | Action type | Authority check |
| --- | --- | --- |
| Skill Forge `POST /skills/{id}/approve` | `skillforge.publish` | `request_approval()` sends email; `publish()` checks signed authorization |
| Skill Forge `POST /skills/{id}/grants` | `skillforge.publish` scoped grant | Must be reached through the signed gateway |
| Cybersecurity `POST /engines` | `cybersecurity.engine_register` (4) | Signed authorization required |
| Cybersecurity `POST /engines/{id}/scopes` | `cybersecurity.scope_register` (3/4) | Signed authorization required |
| Cybersecurity `POST /tasks/{id}/approve` | `cybersecurity.task_approve` (3/4) | Signed authorization required |
| Cybersecurity `POST /tasks/{id}/reject` | `cybersecurity.task_reject` (3) | Signed authorization required |
| Cybersecurity task create/dispatch | `security_testing` (3/4) | Signed authorization required |

`approved_by` is the verified signer ID, never the literal string `"owner"`.

## 6. Verification

```
cd backend
python -m unittest discover -s tests -p 'test_*.py' -q
```

52 unit tests pass, covering deterministic payloads, nonce binding, signature
reuse rejection, gateway HMAC validation and the default log transport. The
Postgres integration check additionally verifies outbox delivery, signer
challenge retrieval and signed decisions against a real database (137 tables).

## 7. Remaining work

1. Configure a real Creator domain email transport (`smtp` or `http`) and set
   `CREATOR_GATEWAY_SECRET` in the deployment environment.
2. Connect the physical/external signer to `POST /gateway/decision`, signing
   `"<challenge_hash>|approved"` or `"<challenge_hash>|rejected"`.
3. Restrict `/gateway/decision` and `/authorizations/{id}/revoke` at the
   deployment boundary to the gateway's network identity.
4. Add a periodic worker that calls `POST /outbox/retry` for failed deliveries.
