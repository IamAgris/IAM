# IAM — Research Acquisition & Legal Intelligence System Specification

**Document:** 27 (proposed addendum to Documents 01–26)  
**Version:** 1.0 · 27 November 2026  
**Status:** **PROPOSED** — awaiting owner confirmation. Does not alter the frozen baseline or any locked decision.  
**Parent:** `IAM_HUMAN_BEHAVIOUR_INTELLIGENCE_SPEC.md` (Doc 26 / OD-45), `IAM_GLOBAL_RESEARCH_AND_KNOWLEDGE_SPEC.md` (Doc 14 / OD-30)  
**Related:** `IAM_FINANCIAL_INTELLIGENCE_AND_ECONOMIC_INDEPENDENCE_SPEC.md` (Doc 25 / OD-44), `IAM_LEGAL_INTELLIGENCE_AND_COMPLIANCE_SPEC.md` (Doc 15), `IAM_SECURITY_AND_INTERNET_POLICY.md`, `IAM_PRIVACY_AND_SECRETS.md`, `tools/rkie/notes/hbi-implementation.md`  
**Proposed decision:** OD-47 (Research Acquisition & Legal Intelligence)  
**Governing principle:** Build IAM around **legal access to knowledge, original research, partnerships and independently developed intelligence** — not around owning unrestricted rights to other people's intellectual property.

---

## 1. Scope and objective

IAM must be able to expand its understanding continuously without depending on a single large licensed dataset. The system covers:

1. Five acquisition routes: open access, research partnerships, direct licensing, public domain and original synthetic data.
2. A permission engine that separates reading, analysis, retention, derivatives, model training and commercial use.
3. Three strictly separated pipelines: knowledge acquisition, knowledge intelligence and model development.
4. A research partnership programme with explicit negotiation of model-training rights.
5. A legal-context registry whose entries are **unverified until reviewed by qualified counsel**.
6. A fail-closed rule: no source enters the training pipeline unless training rights have been independently approved.

This document does **not** provide legal advice. Statements about South African or EU law are owner-supplied context recorded for investigation; they must be verified by qualified counsel before IAM relies on them.

---

## 2. Five acquisition routes

| Route | How it works | Cost | Default posture |
|-------|--------------|------|-----------------|
| Open-access research | Collect works under licences permitting the intended use | Free | Preferred |
| Research partnerships | Negotiate research-use agreements with institutions and researchers | Often free | Strategic priority |
| Direct licensing | Negotiate with publishers, archives and dataset owners | Varies | For restricted but valuable corpora |
| Public-domain materials | Use works with expired or inapplicable copyright | Free | Preferred for history |
| Original synthetic data | Generate IAM-owned scenarios and evaluation examples | Low | Own provenance; still needs approval |

Permission to **read or analyse** material does not imply permission to **store permanently**, **create derivatives**, **train models** or **use commercially**. Each is a separate right.

---

## 3. Three separated pipelines

| Pipeline | Input | Output | Authority |
|----------|-------|--------|-----------|
| **1. Knowledge acquisition** | Permitted publications, records, datasets | Approved research corpus with provenance | Ingestion gate (§6) |
| **2. Knowledge intelligence** | Approved corpus | Concepts, relations, facts, summaries, statistical findings — a searchable knowledge base | Analysis gates; no training rights required |
| **3. Model development** | Only material with independently approved training rights | Training datasets, candidate models | Training approval gate (§7) |

This separation is the central architectural advantage: IAM can learn through retrieval and analysis from a much broader body of research than it is licensed to train on.

Rules:
- A source approved for analysis is **not** thereby approved for training.
- Derived knowledge (facts, summaries, statistics) may be retained where permitted by the source terms; raw copies are not automatically retainable.
- Synthetic scenarios follow their own provenance and ownership rules, recorded in the manifest.
- Pipeline 3 cannot read from Pipeline 1 directly; it reads only from the training-approved subset.

---

## 4. Expanded manifest

Every acquired resource has a manifest record. Required and recommended fields:

| Field | Purpose |
|-------|---------|
| `source_id` | Unique identifier |
| `rights_holder` | Copyright or data owner |
| `licence_id` | Applicable licence identifier |
| `permission_evidence` | Licence, contract, email or written permission reference |
| `acquisition_method` | `open_access`, `partnership`, `direct_license`, `public_domain`, `synthetic` |
| `ingestion_allowed` | Permission to acquire and process |
| `storage_allowed` | Permission to retain |
| `analysis_allowed` | Permission to analyse |
| `derivative_allowed` | Permission to create derived representations |
| `model_training_allowed` | Explicit training permission |
| `commercial_use_allowed` | Commercial-use permission |
| `attribution_required` | Attribution obligations |
| `personal_data_present` | Whether personal information exists |
| `privacy_lawful_basis` | Documented POPIA/GDPR justification |
| `retention_period` | Permitted retention period |
| `territory` | Geographic scope of permission |
| `expiry_date` | Permission expiry |
| `revocation_conditions` | Withdrawal and termination conditions |

The existing Doc 26 manifest blocks (`source`, `licensing`, `permitted_purposes`, `lawful_basis`, `privacy`, `governance`) remain valid and are extended by these fields. Unknown permissions never become `approved`.

---

## 5. Ingestion gate (unchanged posture, extended fields)

The Doc 26 fail-closed gate still applies: licence verification, purpose verification, provenance verification, privacy/lawful-basis verification, restriction verification and approval. Outcomes: `approved`, `rejected`, `pending`. Corpus states: `not_validated`, `validated`, `restricted`.

Additions:
- `derivative_allowed` is checked when a pipeline requests derived artefacts.
- `expiry_date` and `revocation_conditions` are tracked; expired or revoked sources move to `restricted`.
- `territory` is checked against the deployment jurisdiction before ingestion.
- `acquisition_method: synthetic` requires recorded ownership (`rights_holder`) and owner approval, not a third-party licence.

---

## 6. Training approval workflow

Independent approval is mandatory and cannot be granted by the ingestion reviewer.

1. A training request names `source_id`, intended model, purpose and proposed retention.
2. The engine verifies: source is `approved` and not `restricted`; `model_training_allowed` is true; `derivative_allowed` is true; `permission_evidence` exists; no expiry/revocation; permitted purpose includes the intended use; territory applies.
3. An **independent approver** (different from the ingestion `approved_by`) records a decision with basis and timestamp.
4. Only then is the source added to `training_approved_ids()` and readable by Pipeline 3.
5. Every decision is written to the audit history with rules applied.

A source whose training rights lapse is removed from the training-approved set; already-trained models are handled under the model registry and rollback rules (OD-40, Doc 26 §6.14).

---

## 7. Research partnership programme

Targets: universities, psychology departments, behavioural-science laboratories, social-science organisations, independent researchers, historical institutions, non-profit foundations and research participants.

Each partnership request records: organisation, contact reference, requested rights (read, download, derive, retain, train, commercial), proposed safeguards, status (`requested`, `agreed`, `rejected`, `expired`), agreement evidence reference and review date.

Negotiation checklist:
1. Reading and analysis of published research.
2. Download of specified datasets.
3. Creation of derived statistical representations.
4. Retention of approved materials.
5. **Explicit model-training permission.**
6. Commercial use if IAM becomes commercial.
7. Attribution, territory, duration and withdrawal terms.

Researchers may also contribute original summaries, behavioural scenarios and structured datasets under a contribution agreement.

Voluntary participant research requires informed consent, ethics review where required, minimisation, additional safeguards for children's information and a documented retention/deletion policy.

---

## 8. Legal context registry (unverified by default)

Owner-supplied context to investigate, **not** law to rely on:

| Topic | Owner-supplied note | Required verification |
|-------|---------------------|-----------------------|
| South Africa, Copyright Amendment Bill | Constitutional Court judgment of 26 June 2026 upheld proposed fair-use section 12A within the referral and struck down certain educational exceptions; enactment/commencement status is not established by the judgment alone | IP counsel must confirm current operative law before reliance |
| POPIA section 27 | Potential authorisation for processing special personal information for historical, statistical or research purposes subject to public-interest/disproportionate-effort conditions and safeguards | Confirm statutory text, conditions and safeguards with counsel |
| EU Directive 2019/790 Article 4 | Commercial TDM exception for lawfully accessible works where rights holders have not appropriately reserved rights | Confirm territorial applicability and reservations |
| Public availability | Does not remove copyright or POPIA/GDPR obligations | Confirm per source |

Every registry entry carries `status: requires_verification`, `verified_by: null`, `verified_at: null`. An entry becomes `verified` only when counsel records a reference. IAM must never present an unverified entry as a legal conclusion.

---

## 9. Governance and audit

- Permission decisions, training approvals, partnership requests and legal-context verifications are append-only and auditable.
- Dual-use review (Doc 26 §18) still applies; no acquisition route relaxes it.
- Human oversight (Doc 26 §18) still applies to consequential decisions.
- No source enters the training pipeline without independent training approval.
- Restrictions propagate: a restricted source is excluded from both analysis and training.
- Deletion and reprocessing are supported when permissions change.
- OD-45 boundaries remain unchanged; this document adds acquisition governance only.

---

## 10. Acceptance criteria

1. Every acquired resource has a manifest with rights holder, permission evidence and acquisition method.
2. Ingestion is fail-closed; unknown or expired permissions never become approved.
3. Three pipelines are separated; training reads only from separately approved sources.
4. Training approval requires an approver distinct from the ingestion reviewer.
5. Partnership records capture explicit model-training negotiation.
6. Legal-context entries are unverified until counsel records a reference.
7. Restrictions and expiry propagate to analysis and training eligibility.
8. All decisions are auditable with rules applied, approver and timestamp.
9. No earlier decision, system count or authority rule is changed.

---

## 11. Implementation status

Code implementation: `backend/app/services/hbi/permission_engine.py`, expanded manifest schema, training-approval routes and legal-context/partnership registries in `backend/app/services/hbi/`. Verification commands and results are recorded in §17 of Doc 26 and `tools/rkie/notes/hbi-implementation.md`.

---

## 12. Owner decision required (proposed OD-47)

Confirm: (a) the five acquisition routes; (b) three-pipeline separation; (c) independent training approval; (d) expanded manifest fields; (e) partnership programme; (f) legal-context registry as unverified until counsel review; (g) propagation of restrictions to training. Until confirmed, this document is a proposal and changes no locked decision.
