# IAM Digital Identity & Universal Web Interaction System

**Version:** 1.0 · 26 November 2026  
**Status:** ARCHITECTURE SPECIFICATION  
**Subsystem:** Phase 10 — Digital Identity Infrastructure (DII) + Universal Web Interaction System (UWIS)  
**Scope:** Local-first, API-independent web interaction with signed authority gates, encrypted credential vault, human-assistance intervention, and continuous learning.

---

## 1. Purpose

IAM must be able to operate websites like a human — reading pages, filling forms, registering accounts, authenticating, publishing content, and managing account lifecycles — without depending on every website providing an API. APIs are optional integrations; browser automation is the primary path.

This subsystem provides:
- A **credential vault** for website passwords, passkeys, TOTP secrets and OAuth tokens (encrypted at rest, names-only in logs)
- A **browser automation engine** (Playwright) with multi-engine, multi-tab, multi-session support
- A **human-assistance queue** for CAPTCHA, OTP, biometric and legal-agreement handoffs
- An **autonomous task engine** for multi-step workflows with checkpoints, retries and recovery
- A **website knowledge base** storing login procedures, supported auth methods, known restrictions and prior failures
- A **digital reputation & trust** layer tracking account standing, suspensions and ToS changes
- A **privacy & data governance** layer for cookie/consent management and data-minimisation
- A **Creator Control Centre** dashboard endpoint for account inventory, active tasks, alerts and approvals

---

## 2. Architecture Principles

| Principle | Rule |
|-----------|------|
| **Local-first** | Identity, credentials and security infrastructure remain under IAM's controlled infrastructure |
| **API-independent** | Websites are accessed through normal browser interfaces; APIs are optional |
| **Human-assisted** | When human participation is required (CAPTCHA, biometric, payment), IAM pauses, asks, preserves task state and resumes |
| **Autonomous but accountable** | Routine actions execute within permissions; sensitive actions require explicit signed approval |
| **Continuous learning** | Website knowledge, automation reliability and recovery improve without weakening security |
| **Fail-closed** | No live third-party connection is made without explicit opt-in credentials and signed approval |
| **No secrets in logs/models** | Raw passwords, OTPs, session cookies and private keys are never logged or sent to models |

---

## 3. 20-Module Architecture

| # | Module | Status |
|---|--------|--------|
| 1 | Digital Identity Core | Implemented (genesis ULID, identity genesis record) |
| 2 | Identity Lifecycle Manager | Implemented (genesis, public name, rotation) |
| 3 | Account Management Engine | Implemented (register, rotate, close, social presence) |
| 4 | Password Manager | Implemented (encrypted vault, generate/rotate/reveal) |
| 5 | Passkey Manager | Implemented (WebAuthn registration + assertion) |
| 6 | Authentication Engine | Implemented (TOTP, WebAuthn assertion) |
| 7 | MFA Manager | Implemented (TOTP enrollment/verify/disable, recovery codes) |
| 8 | Credential & Secrets Vault | Implemented (AES-GCM encryption, env-var references) |
| 9 | Session Management Engine | Partial (isolated browser sessions, tab management) |
| 10 | Universal Browser Engine | Implemented (multi-engine, multi-tab, upload/download, visual agent) |
| 11 | Universal Web Intelligence | **This spec** (website understanding, change detection, accessibility, malicious detection) |
| 12 | Mobile Application Interaction | Implemented (ADB tap/swipe/type/screenshot, allowlisted devices) |
| 13 | Autonomous Web Task Engine | **This spec** (multi-step planning, decomposition, checkpoints, parallel agents) |
| 14 | Human Assistance & Intervention | Implemented (levels 1–5, resolve/escalate, audit history) |
| 15 | Digital Reputation & Trust | **This spec** (account standing, suspensions, ToS changes) |
| 16 | Privacy & Data Governance | **This spec** (cookie/consent management, data retention, GDPR awareness) |
| 17 | Website Knowledge Base | **This spec** (per-website login procedures, auth methods, restrictions, prior failures) |
| 18 | Security Intelligence | **This spec** (breach monitoring, suspicious auth detection, compromised sessions) |
| 19 | Device & Infrastructure Manager | Partial (browser/device infrastructure, worker health) |
| 20 | Creator Control Centre | **This spec** (dashboard endpoint: account inventory, tasks, alerts, approvals) |

---

## 4. Database Models

### 4.1 Website Knowledge Base (`website_knowledge`)

Stores per-website learned knowledge: login procedures, auth methods, known restrictions, prior failures, browser compatibility, verification requirements.

### 4.2 Website Sessions (`website_sessions`)

Tracks active browser sessions per website: authentication state, cookie consent, last activity, session expiry.

### 4.3 Account Lifecycle (`website_accounts`)

Extends `online_accounts` with full lifecycle: registration date, verification status, MFA status, recovery method, last login, account status, suspension detection.

### 4.4 Digital Reputation (`digital_reputation`)

Tracks per-website account reputation: verification status, platform warnings, suspensions, ToS/privacy policy change detection, security score, ownership evidence.

### 4.5 Cookie & Consent Records (`website_consent`)

Tracks per-website cookie and tracking consent: cookie categories, consent status, last updated, data-retention preferences.

### 4.6 Security Incidents (`digital_security_incident`)

Tracks security events: credential leaks, suspicious auth attempts, compromised sessions, unauthorised changes, breach monitoring.

### 4.7 Autonomous Tasks (`autonomous_web_task`)

Tracks multi-step web tasks: decomposition, checkpoints, retry logic, dependency management, scheduled execution, progress reporting, cancellation.

### 4.8 Browser Infrastructure (`browser_infrastructure`)

Tracks browser profiles, remote browser workers, mobile devices, health monitoring, resource allocation.

---

## 5. API Surface

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/web/knowledge` | GET/POST | Website knowledge base (create/query known websites) |
| `/api/v1/web/knowledge/{id}` | GET/PATCH/DELETE | Individual knowledge record |
| `/api/v1/web/sessions` | GET/POST | Website sessions (create/list active sessions) |
| `/api/v1/web/sessions/{id}` | GET/DELETE | Session detail/termination |
| `/api/v1/web/accounts` | GET/POST | Account lifecycle (register/list accounts) |
| `/api/v1/web/accounts/{id}` | GET/PATCH/DELETE | Account detail/activation/suspension/closure |
| `/api/v1/web/reputation` | GET | Digital reputation & trust (account standing) |
| `/api/v1/web/reputation/{id}` | GET | Individual reputation detail |
| `/api/v1/web/consent` | GET/POST | Cookie & consent management |
| `/api/v1/web/consent/{id}` | PATCH/DELETE | Individual consent update/revocation |
| `/api/v1/web/security-incidents` | GET/POST | Security incidents (breach monitoring, suspicious auth) |
| `/api/v1/web/security-incidents/{id}` | PATCH | Incident resolution |
| `/api/v1/web/tasks` | GET/POST | Autonomous web tasks (create/list tasks) |
| `/api/v1/web/tasks/{id}` | GET/PATCH/DELETE | Task detail/status/cancellation |
| `/api/v1/web/tasks/{id}/checkpoints` | GET | Task checkpoint history |
| `/api/v1/web/browser` | GET | Browser infrastructure (profiles, workers, health) |
| `/api/v1/web/browser/{id}` | PATCH/DELETE | Browser profile/device management |
| `/api/v1/web/dashboard` | GET | Creator Control Centre dashboard (inventory, tasks, alerts, approvals) |

---

## 6. Security Boundaries

- Raw credentials never stored in plaintext; encrypted with AES-GCM at rest
- Credential reveal/rotate requires signed Creator authorization
- CAPTCHA, biometric, payment and legal-agreement actions route to HAIS (human assistance)
- No live third-party connection without explicit opt-in credentials and signed approval
- All web actions audited with actor, target, timestamp and outcome
- Website knowledge base contains no credentials; only procedural metadata

---

## 7. Implementation Roadmap

| Phase | Module(s) | Dependencies |
|-------|-----------|--------------|
| 10a | Specification + database models | Existing auth, creator approval, world model |
| 10b | Website Knowledge Base + core API routes | Phase 10a |
| 10c | Digital Reputation & Trust + Privacy Governance | Phase 10b |
| 10d | Security Intelligence + Monitoring & Recovery | Phase 10c |
| 10e | Autonomous Web Task Engine (decomposition, checkpoints) | Phase 10b |
| 10f | Browser/Device Infrastructure + Creator Control Centre | Phase 10e |
| 10g | Advanced Authentication Intelligence (OAuth/SAML/SSO framework) | Phase 10b |
| 10h | Full end-to-end validation + documentation | All phases |

---

## 8. Non-Goals (out of scope for this phase)

- Bypassing CAPTCHAs or anti-bot protections (always routes to HAIS)
- Automatically satisfying human-only verification
- Manufacturing identity documents or verification credentials
- Storing raw passwords, private keys or session cookies in logs or models
- Making unauthorised purchases or financial commitments

---
