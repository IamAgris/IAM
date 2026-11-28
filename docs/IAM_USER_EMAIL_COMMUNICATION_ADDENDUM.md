# Opt-in Email Carrier for Private User Communication — Addendum

**Document:** 39 · **Owner decision:** OD-59  
**Status:** CONFIRMED — owner confirmation 28 November 2026. Part of the frozen baseline.  
**Date:** 28 November 2026  
**Extends:** Document 07 / OD-18 (three communication channels), OD-21 (sensitive information guidance)  
**Does not alter:** OD-01 identity, OD-03 signing, OD-11 protected core, OD-19 Creator approval, OD-42 Creator channels

---

## 1. Purpose

The owner directed that private user communication (OD-18 Channel 3) **may also be
carried by email, but only when the user explicitly gives IAM their email address
to chat there**. This addendum defines that opt-in carrier. It does not change the
in-app private conversation channel, which remains the default and the primary
interface.

Owner confirmation authorises this design and its implementation. All feature
flags remain default-off until the dedicated address and credentials are supplied.

## 2. Channel identities stay separate

| Channel | Identity | Purpose |
|---------|----------|---------|
| 1 — Operational | Google / Gmail account | Signups, service notifications, external providers |
| 2 — Creator authority | Verified address on IAM's domain (e.g. `creator@iamagris.co.za`) | Approval requests and signed decisions only |
| 3 — Private user (default) | In-app, per-user isolated conversation | Personal conversations and private assistance |
| 3 — Private user (optional carrier) | **Distinct** IAM-domain address (e.g. `chat@iamagris.co.za`) | Email chat, only for opted-in users |

The Channel 3 email address **must not** be the Creator address or the operational
Gmail address. Channel identities are never interchangeable (Doc 07 §6). The
illustrative `chat@` name requires owner confirmation before it is used.

## 3. Opt-in and consent

1. Email chat is **default-off**. No user is emailed until they opt in.
2. The user must explicitly supply their email address and state that they want
   to chat with IAM by email. Silence, a signature on an unrelated form, or an
   address scraped from another system is not consent.
3. Opt-in is per user (`visitor_id`), recorded with timestamp and purpose.
4. The user may withdraw at any time. On withdrawal, outbound email stops; the
   user may additionally request deletion of the stored address and history,
   subject to retention obligations (Doc 07 §5.5, §8.8).
5. The OD-21 warning is shown at opt-in: do not send passwords, banking details
   or identity documents unnecessarily.

## 4. Binding and authentication — email is not identity proof

An inbound `From:` header is trivially forged. Therefore:

1. The supplied address is **unverified** until the user completes a verification
   loop: IAM sends a single-use, short-lived, random token to that address, and
   the user returns it through the in-app session or the signed webhook.
2. Only a **verified** address may be bound to a `visitor_id`. Changing the address
   starts a new verification; the old binding is not carried over automatically.
3. Inbound email that fails verification is logged and discarded; it never enters
   a user's conversation history and never triggers an action.
4. A verified email address grants no authority. It cannot approve, decide, sign,
   change architecture or access another user's data. OD-19 is unchanged.

## 5. Inbound path — provider forwards to a webhook

1. The operator configures the email provider to forward opted-in user messages
   to an IAM webhook endpoint. The endpoint is protected by an HMAC signature over
   the raw body using a dedicated secret, plus provider allowlisting; an unsigned
   or unrecognised request is rejected.
2. The webhook verifies the sender binding from §4, applies rate and size limits,
   and strips or sandboxes attachments. HTML is converted to plain text; no remote
   content is fetched or executed.
3. Each accepted message is written to the **same per-user private history** as an
   in-app message, scoped by `visitor_id` with ownership checked on every read.
4. Inbound email never bypasses the user-facing permission model. It is a message,
   not a command.

## 6. Outbound delivery

1. Outbound replies use the dedicated Channel 3 IAM-domain identity from §2.
2. Each message is addressed to one verified user. Batch or group addressing is
   forbidden; a user must never receive another user's content.
3. Transport uses STARTTLS (or TLS) with a dedicated credential; the credential is
   held as a secret and never logged or returned by an API.
4. Delivery state is recorded for retry and dead-letter handling, mirroring the
   existing outbox pattern but in a separate table.
5. The frontend remains the user interface. Email is a transport for conversation,
   not a second UI and not a Creator surface.

## 7. Privacy, audit and boundaries

- Per-user isolation applies identically to in-app and email messages.
- No email content enters `shared_knowledge` without privacy-preserving
  transformation and consent (Doc 07 §4).
- Every inbound and outbound message is audited with channel `private_user`,
  direction, actor, purpose and `details.transport = "email"` in
  `communication_audit`; the existing `details` JSON column avoids a schema change.
- Encrypted at rest and in transit.
- No private information is revealed to the Creator without an authorised
  security or legal reason (Doc 07 §5.2).
- This addendum creates no new top-level system, no new AI identity and no new
  authority path. It is a carrier inside the existing memory, identity and
  communication systems.

## 8. Configuration surface (proposed, all default-off)

| Name | Default | Meaning |
|------|---------|---------|
| `USER_EMAIL_ENABLED` | `false` | Master switch; no external call while false |
| `USER_EMAIL_FROM` | empty | Dedicated IAM-domain sending identity |
| `USER_EMAIL_SMTP_HOST` / `_PORT` / `_USER` / `_PASSWORD` | empty / 587 / empty / empty | Outbound carrier credentials |
| `USER_EMAIL_WEBHOOK_SECRET` | empty | HMAC secret for inbound forwards; empty disables the endpoint |
| `USER_EMAIL_DOMAIN` | empty | Allowed domain for opt-in addresses |

No credential value is ever placed in a specification, note, log or API response.

## 9. Acceptance criteria

1. Email chat is impossible until the user opts in and verifies their address.
2. An unverified or spoofed `From:` cannot create or read a user conversation.
3. Two users can never see each other's email or in-app messages.
4. Withdrawal stops outbound email and supports address/history deletion.
5. No email message carries or grants authority; OD-19 remains intact.
6. Every accepted message is audited with `private_user` + `details.transport`.
7. The Creator address and operational Gmail are never used by this channel.
8. All feature flags default-off; no external request occurs before configuration.

## 10. Implementation status

**IMPLEMENTED, DEFAULT-OFF.** The carrier exists but performs no external action
until configured. Implementation evidence:

| Concern | Location |
|---------|----------|
| Config (`USER_EMAIL_*`) | `backend/app/core/config.py` |
| Opt-in / outbox / dedupe models | `backend/app/models/user_email.py` |
| Migration 072 | `backend/app/db/migrations/072_user_email_communication.sql`, `MIGRATION_ORDER.json` |
| Service (opt-in, verify, opt-out, send, receive, retry) | `backend/app/services/user_email_service.py` |
| Endpoints + HMAC webhook | `backend/app/api/routes/user_email.py`, `backend/app/main.py` |
| Container env pass-through | `docker-compose.yml`, `.env.example` |
| Tests | `backend/tests/test_user_email.py` (11 passed) |

Outbound uses the existing AES-GCM `CryptoService`; messages land in the
existing `VisitorMessage` thread via `GlobalAccessService`, and every event is
audited as `private_user` with `details.transport = "email"`. The default address
is `chat@iamagris.co.za`. Still required from the operator: SMTP credentials and
`USER_EMAIL_WEBHOOK_SECRET`, then `USER_EMAIL_ENABLED=true`.
