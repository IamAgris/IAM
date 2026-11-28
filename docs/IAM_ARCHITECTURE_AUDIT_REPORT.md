# IAM Architecture Audit Report

> **HISTORICAL SNAPSHOT — NOT CURRENT STATUS.** This audit was written when the register held 26–32 decisions. It is retained as evidence of a point-in-time consistency check. Current authority: `ARCHITECTURE_INDEX.md`, `IAM_FINAL_CONSOLIDATION.md`, `IAM_OWNER_DECISIONS.md`; current implementation status: `IAM_ARCHITECTURE_COMPLETION_AUDIT.md`.

**Date:** 25 November 2026  
**Scope:** All 26 architecture documents, 26 owner decisions, 7 resolved specs  
**Method:** Automated consistency scan (`audit_architecture.py`) + manual review of findings  
**Purpose:** Verify the "frozen architecture" claim — all conflicts found and resolved.

---

## 1. Verdict

**The frozen architecture claim is now TRUE.** The audit found and resolved 6 real consistency issues. No architectural contradictions remained — the issues were documentation hygiene (duplicate authorities, stale status text, broken references, naming ambiguity).

---

## 2. Findings & resolutions

| # | Finding | Severity | Resolution |
|---|---------|----------|------------|
| 1 | **Two competing master documents** — `MASTER_SPECIFICATION.md` and `IAM_MASTER_ARCHITECTURE.md` both claimed master/architecture-locked status | HIGH | Created `ARCHITECTURE_INDEX.md` as authoritative entry point; marked `MASTER_SPECIFICATION.md` SUPERSEDED; `IAM_FINAL_CONSOLIDATION.md` is the master |
| 2 | **Stale decision register** — said "Awaiting owner confirmation", "accept all defaults", "all ten decisions", OD-01…OD-10 while 26 decisions were locked at that time | HIGH | Rewrote header to "ALL 26 DECISIONS LOCKED" (since superseded by the current 32-decision register); replaced "How to confirm" with frozen change-control section |
| 3 | **README stale status** — "Phases 0–5 implemented, 6–10 specified" while all 5 acceptance levels passed; "Marlow interface" as current identity | MEDIUM | Updated to frozen status + all 5 levels passed; clarified IAM is displayed identity, Marlow is source filename |
| 4 | **Broken canonical references** — README linked `IAM_DOC_0X.md` without `canonical/` prefix | MEDIUM | Fixed all 4 paths to `canonical/...` |
| 5 | **Document number collision** — `IAM_BLOCKCHAIN_AND_BANKING.md` and `IAM_DYNAMIC_NODE_NETWORK_SPEC.md` both numbered Document 09 | MEDIUM | Renumbered dynamic node spec to Document 10; updated index and consolidation |
| 6 | **Naming ambiguity** — "AURA" codename and "Marlow" referenced as interface name | LOW | Documented in `ARCHITECTURE_INDEX.md`: AURA = engineering codename only; IAM = permanent identity; Marlow = supplied HTML filename. Canonical supplied docs left verbatim (correctly frozen). |

---

## 3. Non-issues confirmed

- **"32 decisions" count** — consistent after OD-29…OD-32 were added (header, index, consolidation and README all say 32; OD-01…OD-32 all present)
- **OD-26 dynamic node network** — verified consistent with protected core (OD-11), restricted reporting (OD-13), hardware adaptation (OD-22); no auto-promotion of unverified code; 1% contribution is owner-confirmed and disclosed
- **OD-27 / OD-28** — capability decisions recorded in `IAM_OWNER_DECISIONS.md` and indexed as Documents 11 and 12
- **OD-29…OD-32** — SDK/CLI, global research, legal intelligence and geospatial decisions recorded and indexed as Documents 13–16; SDK scaffold under `sdk/`
- **"Marlow" in canonical docs** — intentional; those are verbatim frozen supplied documents
- **"Marlow" in superseded drafts** — historical, harmless
- **AURA in README** — engineering codename, now explicitly labelled as such

---

## 4. Current authoritative structure

```
ARCHITECTURE_INDEX.md          ← START HERE (entry point)
IAM_FINAL_CONSOLIDATION.md     ← master architecture + gap analysis
IAM_OWNER_DECISIONS.md         ← 32 locked decisions
canonical/IAM_DOC_01-04        ← frozen supplied documents
IAM_DISTRIBUTED_ARCHITECTURE.md    (05)
IAM_WHITEHAT_AND_WORKSPACE.md      (06)
IAM_COMMUNICATION_ARCHITECTURE.md  (07)
IAM_HARDWARE_ADAPTATION.md         (08)
IAM_BLOCKCHAIN_AND_BANKING.md      (09)
IAM_DYNAMIC_NODE_NETWORK_SPEC.md   (10)
IAM_UNIVERSAL_WEBSITE_INTERACTION_SPEC.md (11)
IAM_AI_ASSISTANT_INTEROPERABILITY_SPEC.md (12)
IAM_DEVELOPER_SDK_AND_CLI_SPEC.md  (13)
IAM_GLOBAL_RESEARCH_AND_KNOWLEDGE_SPEC.md (14)
IAM_LEGAL_INTELLIGENCE_AND_COMPLIANCE_SPEC.md (15)
IAM_GEOSPATIAL_INTELLIGENCE_AND_LIVE_MAPPING_SPEC.md (16)
sdk/                               (SDK/CLI scaffolds)
IAM_OPEN_SPECS_RESOLVED.md         (A-G resolved)
IAM_DATABASE_DESIGN.md / IAM_API_CONTRACTS.md / IAM_SECURITY_AND_INTERNET_POLICY.md
```

Superseded (historical only): `MASTER_SPECIFICATION.md`, `IAM_MASTER_ARCHITECTURE.md`, `IAM_*_SPEC.md` derived drafts, `IAM_ARCHITECTURE_GAP_ANALYSIS.md`, `IAM_DISTRIBUTED_GAP_ANALYSIS.md`.

---

## 5. Final assessment

The architecture is internally consistent and correctly documented. All 5 acceptance levels pass on the running stack. The frozen claim is accurate.

**Implemented since this audit:** scoped API credentials and auth middleware, node registry with enforced 1% resource ceiling, protected-core measurement with explicitly approved known-good manifests, Ed25519 node attestation with trust transitions (candidate → trusted/restricted/revoked), signed sync objects, model-backed autonomy reasoning with honest fallback, core-authorised S3 storage, the first UWAIE slice (frontend inspection, permission-gated execution, outcome verification, credential-free workflow learning), public-records/vital/estate research with provenance, confidence, access gates and correction history (OD-30), autonomous legal intelligence with government-source monitoring and the eight-stage law-change lifecycle with authorisation gates (OD-31), geospatial knowledge with replaceable map providers, GeoJSON import/export, live-feed freshness, offline tile caching and location privacy (OD-32), evidence-based human public-presence research with cross-source verification, probabilistic identity matching and privacy boundaries (OD-30/PPIICE), and an internal AI-assistant interoperability lab with official-document research, isolated replication experiments and approval-gated adoption (OD-28), plus acceptance-test authentication (`IAM_API_KEY`).

**Remaining work is implementation of specified-but-not-built subsystems** (live peer-to-peer transport and store-and-forward routing beyond signed sync objects, hardware-backed platform measurements, full UWAIE multi-browser/visual-learning stack, a rendered interactive map UI in the frontend, hardware signer, real bank/thirdweb adapters), not architecture design.
