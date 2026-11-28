# OD-49 — signed Creator decision artefact

**Decision:** OD-49 — Browser Intelligence & Web Operations (BIWOS + TIPS)
**Status:** SIGNED AND VERIFIED — 28 November 2026
**Authority basis:** OD-03 / OD-19 / OD-42 — ED25519 signature over a one-time challenge. A config flag is not a decision.

## Signed decision record

| Field | Value |
|---|---|
| Request ID | `cr_361cd0a2b8f938161d9b42f323a7f246` |
| Action type | `architecture.decision.confirm` |
| Target | `OD-49` |
| Risk level | 4 |
| Status | `approved` |
| Signature verified | `true` |
| Authorization ID | `edc0ca61-df9f-4176-a54a-27cbf11c81a6` |
| Challenge hash | `48140218509dc10d813cc787c910f4f7bd9888dcbfc62a9a012e4bb4d6e726d2` |
| Signature (base64) | `b4TK3CAvvkdNYfcpAQzx/R0cyhAI+Hfdx/t9tkbh+Hs68IK+yMAv0Ab7/uFrz15ghY2l9PNmE1mRTf8gIatJDA==` |
| Signer ID | `creator-dev-signer` |
| Channel | `creator_file` |
| Requested | `2026-11-28T19:47:52.619204+00:00` |
| Resolved | `2026-11-28T19:47:52.880336+00:00` |

The signature was produced by the local Creator signer over
`<challenge_hash>|approved` and verified by `CreatorApprovalService` through the
official `/api/v1/creator/requests/{id}/decide` endpoint. IAM did not self-approve.

## Scope confirmed

BIWOS and TIPS are permanent core capabilities organised as four logical
components inside existing systems — not four deployments and not a new
top-level system. The eight-phase implementation plan in Document 29 is
confirmed under the existing permission matrix and Creator gates.

## Evidence that this signoff is not a capability claim

- Doc 29 phases P1–P8 are code-complete with passing unit tests.
- Live browser substrate smoke passed (`IAM_BROWSER_P1_OK`) — session, task,
  evidence, captcha rejection and session close.
- Live Postgres integration passed for browser substrate tables.
- Still open: real Tor Browser/onion availability and leak drills, live
  Postgres data migration on the production stack, Firefox/WebKit compatibility,
  adversarial fixtures. No phase is marked operationally complete by this sheet.

## Note on the signer

`creator-dev-signer` is the local development signer recorded in this checkout.
It is not a hardware token. For production, OD-03 requires the operator's
hardware signer / external signing service; this artefact proves the flow works
and the decision is signed, not that a specific physical device was used.
