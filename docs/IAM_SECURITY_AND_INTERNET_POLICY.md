# IAM — Security and Internet Access Policy

**Version:** 1.0 · 24 November 2026  
**Status:** Provisional — pending owner decisions  
**Parent:** `IAM_FINAL_CONSOLIDATION.md` (resolves C-06, M-10, S-01…S-14; the original gap analysis is superseded)

---

## 1. Internet access policy (resolves C-06)

**Permitted autonomously (public exploration):**
- Visit publicly accessible websites and read their content.
- Search public search engines.
- Read documentation, papers, news and public data.
- Download permitted public files (subject to scanning).
- Call public APIs that require no credentials.
- Discover new services and AI agents.

**Requires owner authorization (consequential actions):**
- Send messages or emails.
- Spend money or begin paid inference.
- Register accounts.
- Publish content or deploy services.
- Access private/credentialed services.
- Join communities.

**Always prohibited:**
- Bypassing authentication, CAPTCHAs or access controls.
- Circumventing robots.txt or explicit site prohibitions.
- Collecting personal data about private individuals without a lawful basis.
- Using IAM's internet access as an open proxy for public visitors.
- Accessing cloud metadata endpoints or internal networks from browsing tools.

---

## 2. Network security (S-01)

- **SSRF protection:** resolve DNS before connection; reject private, loopback, link-local (169.254.0.0/16), and IPv6 ULA/link-local ranges; re-validate after every redirect.
- **DNS rebinding:** pin the resolved IP for the duration of the request.
- **Egress control:** default-deny egress from execution workers; allowlist required destinations.
- **Metadata protection:** block `169.254.169.254` and cloud metadata hostnames.
- Download size limits and timeouts on all fetches.

---

## 3. Browser security (S-02, S-03, S-08)

- Three browser contexts, never shared:
  - `public` — no credentials, no retained downloads, strict egress.
  - `private` — IAM's authorised accounts, isolated from visitor requests.
  - `isolated` — for external/delegated code, no credentials at all.
- All downloads quarantined and scanned before analysis; never auto-executed.
- Cookies/sessions isolated per context; no credential reuse between contexts.
- Backups encrypted with keys stored separately from backup data.

---

## 4. AI and content security (S-11)

Every untrusted input boundary — web pages, external AI responses, uploaded files, visitor messages — is treated as **data, never instructions**.

Controls:
1. Strip or neutralise instruction-like content before it enters reasoning context.
2. Flag prompt-injection patterns (`ignore previous`, `reveal system prompt`, `disable security`) as high risk.
3. Validate tool requests against the authority ladder before execution.
4. Never copy external content directly into trusted memory; require provenance + verification + confidence.
5. High-impact retention of external knowledge requires owner review.
6. External agents cannot escalate privileges or access IAM private memory.

---

## 5. Credentials (S-05, S-08, S-09)

- Secrets manager: SOPS-encrypted files + Docker secrets initially (OD-07 provisional).
- No credentials in database rows, prompts, logs or frontend bundles.
- Short-lived tokens where supported; rotation schedule per integration.
- Log redaction for keys/tokens.
- Dependency scanning, SBOM, pinned images by digest.

---

## 6. Isolation (S-06, S-13)

- Every visitor-scoped query includes `owner_id` derived from the server-side session token.
- Client-supplied `visitor_id` is ignored.
- Authority re-checked at execution time, not only when queued.
- Isolation contract tests run in CI for all visitor endpoints.
- Audit log is append-only with hash chaining; separate retention from application data.

---

## 7. Financial security

- Monthly ceiling + per-transaction cap; owner-only increases.
- Paid inference disabled by default (`allow_paid=false` at the router).
- Every financial action requires owner authorization and writes an audit event.
- Ledger is double-entry; reconciliation reports on demand.
- IAM cannot create legal entities or accept KYC obligations itself.

---

## 8. Emergency controls (S-14)

Owner-only emergency stop:
1. Halts all autonomous and delegated actions immediately.
2. Closes browser sessions and revokes active tokens.
3. Stops all workers processing the queue.
4. Preserves state for investigation (no data deletion).
5. Writes an audit event with reason and initiator.

Recovery requires explicit owner re-authorization.

---

## 9. Incident response

Detect → classify (low/medium/high/critical) → contain → investigate → eradicate → recover → post-mortem → update controls. All incidents recorded in `incident_records` with resolution and timestamps.

---

## 10. Privacy

- Session memory default; anonymous memory opt-in; accounts optional (OD-05).
- Retention policies configurable; deletion requests honoured.
- GeoIP is an estimate only; user-correctable; never identity.
- Voice recordings not persisted by default.
- Jurisdictions: ZA + EU baseline (OD-09 provisional); assess before expansion.

---

## 11. Testing requirements

| Test | Frequency |
|------|-----------|
| Visitor isolation contract tests | Every build |
| Injection/prompt-injection suite | Every build |
| SSRF/redirect protection tests | Every build |
| Dependency + secret scanning | Every build |
| Backup restore drill | Monthly |
| Disaster recovery drill | Quarterly |
| Load/concurrency test | Before each capacity increase |
| Security review of self-improvement changes | Before every production deployment |
