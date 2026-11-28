# Document conflict resolution status — 28 November 2026

Based on `IAM_DOCUMENTATION_INVENTORY_AND_CONFLICT_REPORT.md` (C01–C35) and the
current working tree. `ARCHITECTURE_INDEX.md` authority tables and
`IAM_OWNER_DECISIONS.md` are **not** rewritten here: `AGENTS.md` requires owner
confirmation for source-of-truth tables.

## Resolved by implementation since the report

| Conflict | Resolution | Evidence |
|---|---|---|
| C22 (SOPS declared, no artefacts) | Partly resolved | `.sops.yaml` added; `tools/quality/check_secrets_posture.py` wired into CI. OD-58 Infisical dual-read is a separate confirmed decision. |
| C23 (IRWM not on inference path) | Resolved | `model_inference.py` admits every chat/stream request through IRWM; `test_irwm_inference_gate.py`. |
| C24 (no backup/restore) | Resolved | `backup_service.py` + live DR drill (287/287 tables, RPO/RTO met). |
| C31 (local green / CI red) | Resolved | All GitHub workflows green at `842d162`. |
| C21 (HMAC vs Ed25519 wording) | Documented | `p2p_transport.py` docstring states HMAC transport, not Ed25519; Ed25519 remains node attestation. |

## Owner-gated (no unilateral change)

| Conflict | Why |
|---|---|
| C01, C02, C03, C05 | Decision numbering/counts and canonical system count — owner confirmation required. |
| C04 | Stale primary-model sentences — OD-46 is locked, but updating frozen specs needs an owner-directed editorial pass. |
| C06, C08, C09, C25, C26, C28, C29, C33 | Dated counts and pass claims in authority prose — recount and rewrite only with owner approval. |
| C07 | OD-47/48/52 status wording across specs — owner confirmation already recorded; editorial pass pending. |
| C10, C11, C12, C34 | Implementation-status headers — require linked evidence and an owner-approved status vocabulary. |
| C13–C20, C27, C30, C32, C35 | Scope/status/naming corrections in derived documents — no safety impact, but owner review needed before touching authority text. |

## Rule applied

Derived/operational documents may record dated evidence; authority documents
keep their frozen wording until the owner approves an editorial batch. Do not
"fix" a specification to match code — report the gap.
