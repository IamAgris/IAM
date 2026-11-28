# IAM — Communication Architecture

**Document:** 07 (addendum to Documents 01–06)  
**Version:** 1.0 · 24 November 2026  
**Status:** FROZEN — formal part of IAM architecture  
**Confirmed decisions:** OD-18 (three channels), OD-19 (email-based creator approval), OD-20 (privacy-preserving collective learning), OD-21 (advise not to share sensitive info)

---

## 1. Purpose

IAM uses three separate communication channels, each with a distinct purpose and identity. This replaces a single mixed email account and removes the need for a Creator dashboard. The frontend remains IAM's actual user interface.

---

## 2. Three communication channels

### Channel 1 — Google / Gmail (Operational)

**Purpose:** IAM's ordinary external operations.

- Signing up for external services
- Registering accounts and integrations
- Receiving verification emails
- Password recovery and service notifications
- Communicating with external service providers
- Sending ordinary operational email

This is IAM's **operational email identity**. It is not used for Creator approvals or private user conversations.

### Channel 2 — IAM Domain (Creator authority)

**Purpose:** Exclusively Creator communications.

- Requests for Creator approval
- Protected architecture changes
- Security-policy changes
- Authorisation requests
- Important system decisions
- Security incidents requiring Creator intervention
- Protected release approvals

This is IAM's official **Creator communication channel**. The address is on IAM's own domain (e.g. `creator@iamdomain.com` — illustrative).

### Channel 3 — Private User Communication (Private)

**Purpose:** IAM's private communication environment for individual users.

- Personal conversations
- Private assistance
- User-specific tasks
- Personal learning and preferences
- Private notifications and follow-ups

Each user has an **isolated conversation history and identity**. No cross-user mixing of private data.

---

## 3. Creator approval via email, not a dashboard

The Creator dashboard is **removed**. Approval works through the domain-based email channel:

1. IAM identifies that a protected action requires Creator authorisation.
2. IAM sends an approval request to the verified Creator email address.
3. The email explains exactly what IAM wants to do, why, what will change and the potential consequences.
4. Creator reviews the request.
5. Creator approves or rejects through a **secure approval mechanism linked to the email**.
6. IAM verifies authority — request identity, expiry and required signing credentials.
7. IAM executes or rejects the action.
8. The result is recorded in the protected audit history.

**Critical security rule:** an ordinary email reply must **not** automatically authorise high-impact changes. High-impact actions require cryptographically signed approval challenges or the external hardware signer (OD-03). Email is the communication carrier, not the authority proof.

The frontend is for **users only** — it contains no Creator approval UI.

**Implementation:** `POST /api/v1/creator/requests` sends the explanatory package
through a configurable transport (`log` by default, `smtp` or `http` when configured)
and records it in `creator_email_outbox`. The external signer returns a decision to
`POST /api/v1/creator/gateway/decision`, protected by an HMAC over the raw request body
plus the ED25519 signature over the one-time challenge. An empty gateway secret
disables that endpoint. See `IAM_CREATOR_APPROVAL_SPEC.md`.

---

## 4. Private user communication and collective learning

Three layers, strictly separated:

| Layer | Behaviour |
|-------|-----------|
| **Individual memory** | IAM learns each user's preferences, needs and communication style privately |
| **Shared knowledge** | IAM improves general knowledge from permitted, privacy-protected insights across users |
| **Private conversations** | Messages, personal details, files and history remain isolated |

Example: User A teaches IAM a programming technique. User B asks a programming question. IAM may apply the general technique for User B — but User B must never receive User A's private messages, identity or personal information.

Collective learning must use privacy-preserving processes with appropriate consent and controls. It must **not** simply combine everyone's chat histories into one shared memory.

---

## 5. Mandatory privacy protections

1. Never disclose one user's private information to another.
2. Never reveal private conversations to the Creator without an authorised security or legal reason.
3. Never use private information for unrelated purposes.
4. Keep personal memory separate for each user.
5. Allow users to inspect, correct and delete their personal conversation data, subject to retention obligations.
6. Do not share private information with external services without authorisation.
7. Encrypt stored conversations and communications.
8. **Advise users not to submit sensitive personal information unnecessarily** (passwords, banking details, identity documents) — OD-21. Voluntary sharing remains possible with safeguards.

---

## 6. Shared security and authorisation layer

All three channels sit above a common layer:

**Identity · Encryption · Permissions · Audit · Trust**

- Channel identities are separate and never interchangeable.
- Every message is audited with channel, sender, purpose and risk level.
- Permissions enforce which channel may perform which action.
- Trust decisions apply to Creator approvals and external communications.

---

## 7. Data model implications

Add: `communication_channels`, `operational_accounts`, `creator_requests`, `creator_approvals`, `signed_challenges`, `user_private_messages`, `user_memory_profiles`, `collective_insights` (privacy-preserving, no raw private data), `communication_audit`.

Every private message table is scoped by `visitor_id`/`user_id` and enforces ownership on every query. No private message content enters `shared_knowledge` without privacy-preserving transformation and consent.

---

## 8. Acceptance criteria

1. Operational, Creator and private channels are separate and non-interchangeable.
2. Creator approvals arrive by email on IAM's domain.
3. No Creator dashboard exists in the frontend.
4. High-impact approvals require signed challenges / hardware signer, not plain email replies.
5. Private conversations are isolated per user.
6. Collective learning never exposes one user's private data to another.
7. Users are warned not to share sensitive information unnecessarily.
8. Users can inspect, correct and delete their data.
9. All communications are audited.
10. Encryption applies to stored conversations and communications.
