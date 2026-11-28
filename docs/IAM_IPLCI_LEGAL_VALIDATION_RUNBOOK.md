# IAM IPLCI — Legal Validation Runbook

**Status:** engineering handoff document · 27 November 2026  
**Authority:** OD-48 (confirmed) · Document 28 `IAM_IP_AND_LEGAL_INTELLIGENCE_MASTER_SPEC.md`  
**Related:** `tools/rkie/notes/iplci-legal-validation-outstanding.md`  
**Principle:** code can prove completion; it cannot supply legal authority.

---

## 1. Purpose

This runbook is the controlled handoff from IAM engineering to qualified legal review. It defines exactly what must be done before IAM's legal governance can be called complete, who may do it, and how the system records it.

No engineer, agent, model or plugin may mark a validation task verified. Only a named, qualified reviewer may do so through `/api/v1/iplci/validation/tasks/{id}/verify`.

---

## 2. Roles

| Role | May do | May not do |
|------|--------|------------|
| Creator / owner | Sign or replace the active policy; assign counsel | Delegate signing to an agent identity |
| Qualified counsel (named) | Open tasks, attach official evidence, verify within competence | Verify outside jurisdiction or competence; use a placeholder reference |
| IAM agents / models | Research, prepare drafts, attach proposed evidence links | Verify a task, sign a policy, waive rights, accept settlements |
| CI | Run AT-01…AT-12 and publish readiness evidence | Mark legal questions settled |

---

## 3. Prerequisites (already installed)

1. Signed policy `production-1` — `backend/app/db/migrations/062_iplci_policy_bootstrap.sql` (`signed_by=creator`, approval `OD-48-creator-confirmation`).
2. Validation task store — `064_iplci_validation.sql`.
3. Seeded counsel checklist — `065_iplci_validation_seed.sql` (16 tasks across ZA, EU, UK, US and cross-border).
4. Context propagation — `IPLCIContextMiddleware` and `X-IPLCI-*` headers (`sdk/PROTOCOL.md`, `frontend/lib/api.ts`).
5. Adversarial suite — `backend/tests/test_iplci_p6.py` (AT-01…AT-12).

---

## 4. Procedure

For each seeded task in `GET /api/v1/iplci/validation/tasks`:

1. **Confirm scope.** Read `domain`, `subject`, `jurisdiction` and `question`. If the question is outside the reviewer's competence, leave it pending and assign a competent reviewer.
2. **Retrieve the primary source.** Use the `official_source_url` as a starting point, not as proof. Retrieve the current text from the official register, gazette or court database. Record the exact provision, version, publication date and commencement date.
3. **Attach evidence.** `POST /api/v1/iplci/validation/tasks/{id}/evidence` with an `evidence_ref` that resolves to the stored official document. A search-engine summary, a blog, or an AI answer is **not** acceptable evidence.
4. **Record the source.** If the authority is new, register it at `POST /api/v1/iplci/official-sources` with `verified_by` set to the reviewer.
5. **Verify.** `POST /api/v1/iplci/validation/tasks/{id}/verify` with the reviewer's real reference, `provision_ref`, and `valid_until` where the law is time-limited. IAM/agent identities are refused.
6. **Handle change.** If the law, licence or ownership changes, call `POST /api/v1/iplci/reassessment/check` and reopen affected tasks. A verified task past `valid_until` is not proof.

---

## 5. Acceptance criteria for "legally complete"

`GET /api/v1/iplci/validation/readiness` must return:

- `complete: true`
- `policy_valid: true`
- `verified_tasks` equal to the total seeded and opened tasks
- every official source carrying a `verified_by` value
- no `blockers`

Additionally:

- AT-01…AT-12 pass in CI.
- No high-risk operation relies on a `requires_verification` legal-context entry.
- The gateway already refuses `commercialise`, publish/`distribute`, `disclose` and training with `IPLCI_LEGAL_VALIDATION_INCOMPLETE` until the criteria above are met. Study, reading and analysis are intentionally unaffected.
- Professional opinions required for FTO, major licensing, litigation and ownership disputes have been obtained outside IAM and referenced as evidence.

---

## 6. What "complete" does and does not mean

**Means:** IAM has an auditable chain from every legal conclusion to an official provision, a named reviewer and a review date; the system refuses to report completion until that chain exists.

**Does not mean:** IAM is qualified to give legal advice, any particular activity is lawful in all jurisdictions, or that a model's reasoning is a legal opinion. Jurisdiction-specific validity remains a human, professional determination.

---

## 7. Maintenance

- Re-run `readiness` after any policy, law, licence or ownership change.
- Re-verify tasks at `valid_until` or at least annually.
- Keep evidence immutable under legal hold (`/api/v1/iplci/legal-holds`); disputes must never silently delete review material.
- New jurisdictions require new seeded tasks and counsel before IAM operates there.
