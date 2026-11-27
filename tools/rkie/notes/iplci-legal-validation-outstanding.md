# IPLCI — legal validation outstanding

**Date:** 2026-11-27 · **Based on:** working tree at the IPLCI P6 implementation
**Re-verify before reuse:** run `tools/rkie/Check-IndexFreshness.ps1`.

## Scope of this note

Document 28 `IAM_IP_AND_LEGAL_INTELLIGENCE_MASTER_SPEC.md` (OD-48) is implemented
in code through phases P1–P6. This note records what **code cannot complete**.
It is untrusted context, not legal advice.

## Not performed by code

1. **Jurisdiction-specific legal validation.** Law entries in
   `backend/app/services/iplci/jurisdiction.py` and entries created through
   `/api/v1/iplci/jurisdiction/rules` remain `requires_verification`. POPIA,
   GDPR, UK GDPR, EU AI Act, US state privacy law, DMCA and copyright
   exceptions must be confirmed against current official sources by qualified
   counsel before reliance.
2. **Official register verification.** Trademark, patent and design results
   from `ip_rights.py` are deterministic risk signals from operator-supplied
   records. No live CIPC/WIPO/EUIPO/USPTO/UK IPO/EUR-Lex search or register
   extract has been performed.
3. **Freedom-to-operate opinions.** `check_patent_fto` explicitly requires a
   qualified patent professional for implement/make/use/sell/import decisions.
4. **Content originality / similarity detection** (IL-11) is not implemented;
   publication gating checks rights status only.
5. **Trade secret registry, AI liability, DRM, open-data governance and full
   liability/insurance intelligence** (IL-05, IL-18, IL-20) remain open.
6. **Universal activation.** The signed policy bootstrap exists at
   `backend/app/db/migrations/062_iplci_policy_bootstrap.sql`, and
   `IPLCIContextMiddleware` propagates `X-IPLCI-*` headers. External entry
   points must supply those headers (see `sdk/PROTOCOL.md`) before governed
   operations are assessed.

## Where evidence lives

- Rights assessments and gateway decisions: `ip_legal_assessments`,
  `ip_legal_risk_decisions`, `ip_legal_audit_events`.
- Provenance and lineage: `ip_legal_sources`, `ip_legal_dataset_provenance`,
  `ip_legal_model_lineages`, `ip_legal_training_approvals`.
- Legal verification: `ip_legal_knowledge_verifications`,
  `ip_legal_official_sources` (status `requires_verification` until counsel
  records a reference).
- Governance activation: `ip_legal_policies` (human signer and approval
  reference; protected rules immutable without a new signed policy).

## Verification commands used

`python -m pytest backend/tests -q`, `python -m ruff check backend`,
`python tools/api/check_migrations.py`, `python tools/api/print_openapi.py --check`,
`python tools/quality/check_mypy_ratchet.py`.
