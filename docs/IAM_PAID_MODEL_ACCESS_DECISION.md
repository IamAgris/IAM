# IAM — Paid Hosted Model Access Decision Request

**Document:** 37 (companion to Documents 23-A / 31 / 32; previously numbered 36)  
**Version:** 1.0 · 27 November 2026  
**Status:** **PROPOSED — awaiting owner decision. Paid access is NOT enabled.**  
**Parent:** `ARCHITECTURE_INDEX.md`, `IAM_OWNER_DECISIONS.md`  
**Related:** `IAM_PRIMARY_MODEL_UNIFICATION_SPEC.md` (Doc 23-A / OD-46), `IAM_MULTI_MODEL_INTELLIGENCE_GOVERNANCE_SPEC.md` (Doc 31 / OD-51), `IAM_UNIVERSAL_MODEL_PROVIDER_ORCHESTRATION_SPEC.md` (Doc 32 / OD-52)  
**Proposed decision:** **OD-57** — controlled paid hosted-model access. **Not confirmed.** OD-56 is locked to Financial Intelligence Amendment A; OD-53/54/55 are assigned to other proposals.  

---

## 1. Current position

Paid endpoints are blocked by three independent controls, all of which remain in force:

1. **OD-04** — zero standing budget; every expenditure requires an owner approval request signed through the OD-03 hardware signer.
2. **OD-51 §4.3** — fail-closed usage accounting: without signed authorisation, determinable pricing and a positive remaining limit, no paid request is made.
3. **OD-52** — free-only discovery and availability filtering; paid models are not registered as executable aliases.

This document does **not** authorise any paid request and does not change any of those controls.

## 2. What would need to be decided

| Clause | Required decision |
|--------|-------------------|
| Provider scope | Which providers may ever be used for paid work (NVIDIA first, or none) |
| Model allowlist | Explicit model IDs, discovered from the provider catalogue, never an open-ended "all paid models" |
| Budget | Monthly ceiling, per-request cap and per-key limits under OD-04 |
| Authorisation | Which actions require signed approval before each paid call |
| Pricing source | Only provider catalogue cost fields; unknown pricing stays blocked |
| Privacy | No private memory, conversations, credentials or confidential project data to paid endpoints |
| Audit | Model, provider, key fingerprint, role, purpose, tokens and cost recorded per request |
| Reversal | Immediate disable switch and logged reason |

## 3. Implementation gates (only after confirmation)

- `DiscoveredModel.access_type` must be `paid` **and** the model must be on the confirmed allowlist.
- `ModelUsageService.preflight()` must return `allowed=True` with a signed authorisation, deterministic `cost_input_per_1m`/`cost_output_per_1m` and a positive remaining limit.
- Registration through LiteLLM `/model/new` must use the same single provider credential reference, never a literal key.
- Paid availability probes are forbidden; only free endpoints are probed by `EndpointAvailabilityMonitor`.
- A rejection must be logged with reason and must never fall back to "allow".

## 4. Preservation

Nothing here changes IAM's identity, shared local primary, LiteLLM gateway, single-sphere frontend, no-browser-credentials rule, no automatic model promotion, or hosted access to private memory. No frozen OD decision is altered by this proposal.

## 5. Decision record

| Item | Decision |
|------|----------|
| Paid NVIDIA access | ❌ **NOT AUTHORISED** — current standing position |
| OD-57 | ⏳ **PROPOSED** — owner confirmation required |
| Any paid API call | Blocked until OD-57 confirmed *and* a signed per-expenditure approval exists |
