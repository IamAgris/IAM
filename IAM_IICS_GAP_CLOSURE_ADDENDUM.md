# IAM — IICS Gap Closure Addendum

**Status:** PROPOSED · navigation only · **not** part of the frozen baseline.  
**Date:** 27 November 2026.  
**Purpose:** Close the nine capability gaps identified in the IICS audit without amending any frozen document, owner decision or system count.

---

## 0. Framing and non-negotiables

This addendum is a *pending proposal*. It becomes authority only after a signed owner decision. It does **not**:

- create a new top-level system (`IAM_FINAL_CONSOLIDATION.md` §1/§8/§9; OD-41, OD-45, OD-48, OD-49, OD-50, OD-51);
- invent new owner decisions — OD-47 and OD-52 remain **proposed**, and this addendum does not pre-approve either;
- claim implementation — it states requirements and acceptance criteria only;
- introduce a queue technology — all background work uses the OD-08 ARQ runtime and the existing Doc 29 §7 `iam.browser.*` surface;
- change the local-first rule — Qwen2.5-Coder 3B remains the primary intelligence (OD-46); hosted providers stay optional and subordinate (OD-38, OD-51); internet access must work with every hosted provider disabled (`canonical/IAM_DOC_03` §2);
- require Creator approval for ordinary free use. Free, lawful public access is **autonomous**; permissibility is decided by the existing legal module (OD-31 / OD-48, `POST /gate/check`), not by asking the Creator each time. Approval is reserved for consequential actions — see §2.0.

All closures are organised as modules inside existing systems: system F (Internet and Digital Interaction), system D (Research/Knowledge), system E (Learning/Self-Development), system H (Memory/Workspace), system P (Evaluation) and system 13 (traffic/queues). The audit's "full" areas — search & web browsing (Doc 29 §3.1–3.11) and task orchestration (Doc 29 §3.8/§7.3) — need no new requirement and are inherited unchanged.

---

## 1. Gap closure matrix

| Audit area | Gap to close | Closure module | Host / authority anchor | Owner decision |
|---|---|---|---|---|
| Connectivity & networking | No general egress control, DNS rebinding defence, provider failover policy | `EgressGateway` | Doc 29 §3.12/§5.2; provisional security policy §2 | No new OD; scope of VPN/link layer needs owner ruling |
| Internet research intelligence | No strategy taxonomy, calibrated confidence, TTL/reputation, claim labels, metrics | `ResearchStrategy` + `SourceReputation` | Doc 03 §5; Doc 14 §6/§9; Doc 29 §3.4 | No new OD; OD-52 for trigger/provider clauses remains pending |
| Autonomous online operations | No cross-service action ledger, scheduled research executor, global budget | `OnlineActionLedger` + `ResearchScheduler` | Doc 03 §11–12/§16; OD-27; Doc 29 §3.5/§3.8; OD-37 | No new OD |
| Online learning & knowledge | Research↔training separation not frozen | `PipelineSeparationGate` | Doc 03 §15; OD-40/OD-41; proposed OD-47 §3–§6 | Aligns with OD-47; requires signed OD-47 to become authority |
| Digital media & document | OCR/PDF parsing explicitly open; no A/V, provenance detection | `MediaDocumentAdapters` | Doc 29 §3.1/§3.14; Doc 29a §10 | No new OD |
| Internet security & threat intel | No CVE feeds, DLP, DNSSEC/DoH, proxy policy, unified rotation | `ThreatIntelFeed` + `DLP` + `VaultRotation` | OD-16 (Aegis), OD-34, OD-48, Doc 29 §8/§9 | No new OD; OD-51 §4.5 paid-use ban unchanged |
| Knowledge memory & source mgmt | No rights registry, TTL classes, claim-level evidence, revocation propagation | `SourceRegistry` extension | Doc 01 §3.D; Doc 14 §6; Doc 29 §6/§7.2; OD-48 | OD-47 for rights manifest; otherwise no new OD |
| Internet governance & privacy | No versioned TOS/robots store, DPIA/DSAR lifecycle, DID/VC, transfer engine | `SitePolicyStore` + `PrivacyLifecycle` | Doc 15/OD-31; OD-48 §3.6/§3.7; Doc 29 §5.5 | No new OD |
| Continuous self-improvement & QA | No recurring scored internet QA, regression gate, feedback loop | `InternetQA` suite | OD-41 §15; OD-38/OD-46 release gates; Doc 29 §9 | No new OD; OD-46 signed release unchanged |

**Permission note:** the decisions below are capability requirements, not per-action approvals. Free public research, browsing and retrieval are autonomous once the legal gateway permits them; Creator approval attaches only to consequential actions (§2.0).

---

## 2. Detailed requirements

### 2.0 Permission and approval model — legal gateway first, Creator only for consequential actions

Free does **not** mean unregulated; it means *no Creator approval is needed when the action is lawful and free*. The existing OD-48 Legal Policy Enforcement Gateway (CE-02) is the deterministic, model-independent gatekeeper. The model never grants itself permission and cannot bypass the gateway (`IAM_IP_AND_LEGAL_INTELLIGENCE_MASTER_SPEC.md` §2.3 CE-02, §5.1–5.2, §6, AT-09).

**Decision sequence for every external action:**

1. **Egress check (§2.1):** destination, scheme, resolved address and caps — deterministic.
2. **Legal check (`POST /gate/check`):** `operation`, `resource_id`, `jurisdiction`, `purpose`, `project_id`, `context`. Existing operations `analyse`, `store`, `disclose` cover read→retain→send; an additive `retrieve` operation is proposed for a clean browse/research case, subject to owner approval before the frozen API contract is changed.
3. **Decision from the gateway** — `APPROVED` / `CONDITIONAL` / `BLOCKED` / `QUARANTINED`, with `decision_class`, `rights_evaluated`, `conditions`, `reviewer_required` and `audit_event_id`. Fail closed on `IPLCI_POLICY_UNAVAILABLE`, `IPLCI_UNKNOWN`, `IPLCI_DENIED`, `IPLCI_QUARANTINED`, `IPLCI_REVOKED`, `IPLCI_EXPIRED`.
4. **Creator approval only when triggered** by any of: `reviewer_required: true`; `decision_class HIGH|CRITICAL`; `IPLCI_APPROVAL_REQUIRED`; paid spend or a paid provider; account registration; publishing or external disclosure of private material; authenticated account operations; financial transactions (OD-04/OD-25); or a change to identity, constitution, security policy or protected core (OD-11).
5. **Execute, then verify** (Doc 11 step 6, Doc 29 §3.8): record the `gate/check` audit event and the outcome in the §2.3 ledger. Never report an unverified external action as successful.

**Autonomy table:**

| Action | Gate | Creator approval |
|---|---|---|
| Search public web, read public page/doc, fetch free API within licence/robots/TOS, retain as unverified evidence | Egress + legal `analyse`/`store` | **No** — autonomous when `APPROVED`/`CONDITIONAL` with satisfiable conditions |
| Compare sources, produce a research report from public material | Legal `analyse` + confidence labelling (§2.2) | **No** |
| Cache/resurface a free public source, monitor a public page for changes | Legal `store`, TTL (§2.2/§2.7) | **No** |
| Use a paid search/API tier, paid compute, or any spend | Legal + budget gate (§2.3) | **Yes** — OD-04, OD-51 §4.5 |
| Register an account, publish, send external message, use authenticated account, disclose private data | Legal `disclose` + Creator approval | **Yes** |
| Train on web-derived dataset or promote a model | Legal `train` + signed training/release gate (§2.4, OD-40/OD-46) | **Yes** |
| Change legal/privacy/security policy or protected core | Frozen change control | **Yes** — OD-11, OD-48 §10.4 |

**Rules:** `CONDITIONAL` decisions (attribution required, territory limits, expiry) are binding and carried into the source record (§2.7); the model may not drop them. "Publicly accessible" is never itself permission (OD-48 §1.3.1); the gateway decides. Free-tier and no-cost provider use is preferred and does not become paid use without an approval and budget.

### 2.1 Connectivity & networking — `EgressGateway`

**Gap addressed:** application/network diagnostics exist (Doc 29 §3.12, §4.1–4.5; Doc 11 §7 node failover) but no general egress control plane.

**Requirements:**
1. All outbound requests from research, browse, API-connector and download paths traverse one gateway; the gateway returns a signed decision record (`allow`/`deny` + reason + policy version) written to the audit log.
2. SSRF protection: resolve hostnames before connect, reject loopback, private, link-local, IPv4/IPv6-mapped, metadata (`169.254.169.254`, `metadata.google.internal`) and unspecified addresses. Re-resolve and re-check on every redirect; pin the validated address for the connection to defeat DNS rebinding. Numeric IP literals require explicit allowlist entry.
3. Mandatory TLS certificate and hostname verification; no "verify=false" path. DNS-over-HTTPS/TLS validation where the resolver supports it; DNSSEC validation status recorded as evidence, not assumed.
4. Per-request timeout, redirect cap, byte cap and retry/backoff ceiling. Exceeding any cap is a recorded failure, never a silent retry.
5. Provider/network health: record latency, error rate and availability per search/API provider; feed Doc 29 §3.12 network diagnostics; drive failover without a single-provider dependency.
6. Optional authenticated outbound HTTP/SOCKS proxy, Creator-configured; explicit IPv4/IPv6 dual-stack policy; no implicit IPv6 bypass of IPv4 denylists.

**Explicitly out of scope pending owner ruling:** Wi-Fi/cellular/Bluetooth/NFC/satellite/mesh interfaces, DHCP/routing/VLAN configuration, ISP selection, host VPN lifecycle and WAN failover. These are host/network-administration concerns, not IAM runtime capabilities.

**Acceptance:** SSRF suite covers localhost, `127.0.0.1`, `::1`, `169.254.169.254`, decimal/octal IP encodings, redirect-to-private and DNS rebinding; byte/timeout/redirect caps enforced; TLS verification failure blocks the request; audit record present for every decision.

---

### 2.2 Internet research intelligence — strategy, confidence, TTL, claim labels

**Gap addressed:** Doc 03 §5 step 2 ("develop search strategies") is one line; Doc 14 §9.2 requires only an uncertainty marker.

**Requirements:**
1. **Strategy taxonomy and selection.** Strategies: single-query, query decomposition (sub-questions), source-first (known authoritative domain), iterative refinement, and contradiction-focused. Selection records the chosen strategy, rationale and information gap. Effectiveness feedback from §2.9 QA updates selection policy; update requires review, never autonomous self-authorisation.
2. **Provider policy.** Free-first, health-ranked failover; no provider is the sole gateway. Free public providers are used autonomously after the §2.0 legal check. Paid search/API use is fail-closed unless a signed Creator approval and budget exist (OD-04; proposed OD-52 §6 remains pending).
3. **Calibrated confidence.** Score in `[0,1]` from independent-source count, source reliability record, primary-vs-syndicated status, publication recency and contradiction flag. Calibration is logged and tested. Threshold table: `<0.40` unverified observation, `0.40–0.69` provisional, `≥0.70` verified knowledge. Sub-`0.70` claims may inform free `Research` output only with their label — no Creator approval is needed to read or report them. A `Commit` action relying on a sub-`0.70` claim requires Creator approval and a `reviewer_required` legal decision.
4. **Freshness TTL by class.** Volatile/news 24 h, documentation 30 d, standards/specifications 180 d, stable reference 365 d. Expiry forces recheck before reuse; expiry is visible to the caller.
5. **Claim-level evidence contract.** Every retained claim carries `claim_id`, `source_id`, URL, publication date, `retrieved_at`, page/fragment locator, confidence score and one label: `verified | provisional | unverified | outdated | contradicted | unresolved`.
6. **Research quality metrics.** Corroboration coverage, contradiction rate, source diversity, retrieval latency and strategy success rate, exposed through the existing observability surface (OD-37 §4.14) with no private data in metrics.

**Acceptance:** three-source corroboration test; contradictory-source test with `contradicted` label; TTL-expiry recheck test; confidence calibration drift test; blocked paid-provider test without approval.

---

### 2.3 Autonomous online operations — ledger, scheduler, budget

**Gap addressed:** Doc 29 §7.1 unifies *browser* tasks only; OD-51 §4.4 bounds *model* delegation only.

**Requirements:**
1. **Cross-service action ledger.** One append-only record per external action across browser, search/research, API connectors, external AI and finance: `actor`, `tool`, `target`, `scope`, `permission_source`, `approval_ref`, `idempotency_key`, `status`, `verification_result`, `cost_units`, `timestamp`. Browser tasks keep their Doc 29 §3.8 state machine; the ledger references the task ID, never replaces it.
2. **Scheduled research executor.** A governed ARQ job type bound to research goals and freshness triggers (Doc 03 §16/§23.10, Doc 29 §3.15). One-shot and recurring modes; max concurrency; deadline; cancellation; no new queue; no duplicate side effects on retry.
3. **Global online-action budget.** Per-window limits on action count, bytes downloaded and spend, applied across all services. Fail-closed at the limit; Creator-configurable; current consumption visible in the Creator control centre. Free, legally approved actions below the limit are autonomous — the budget is a ceiling, not an approval gate. Finance actions still require OD-04/OD-25 authority.
4. **Recovery semantics.** Checkpoints for long-running cross-service workflows; resume from checkpoint; never replay an already-verified external side effect; failures are reported as failures (Doc 29 §3.8 rule).

**Acceptance:** approval-gate test; budget-exhaustion test; idempotency test; cancel/resume test; no-false-success test.

---

### 2.4 Online learning & knowledge — pipeline separation gate

**Gap addressed:** research↔training separation exists only in proposed OD-47.

**Requirements:**
1. Three logically separated pipelines: **research/knowledge** (web → memory, read-only), **dataset preparation** (derived artifacts, rights-checked), **training** (signed release only). No direct path from a fetched page to a training dataset.
2. Every dataset record carries an expanded manifest: `source_sha256`, `licence`, `consent_recorded`, `model_training_allowed`, `derivative_allowed`, `expiry`, `territory`, `confidence_label`, `retrieved_at`. Missing or false fields fail closed.
3. Independent training approval: dataset admission and model release are separate signed actions (OD-40 §7, OD-46 §5). Free research that *prepares* a dataset needs no Creator approval; only the training/release decision does. The model may not approve its own use.
4. **Learning curriculum ledger:** knowledge gap, research performed, sources consulted, what was learned, validation result, remaining gap. Prevents repeated research of known material and records why a gap was closed.
5. Revision of a source does not silently rewrite derived knowledge; corrections append immutable revisions (Doc 26) and flag downstream artifacts.

**Acceptance:** attempt to train directly from an unverified web page is refused; manifest round-trip preserves provenance; source revocation flags derived datasets; no training action without a signed release.

**Dependency:** becomes frozen only if OD-47 is signed; until then this section is a design alignment, not an authority claim.

---

### 2.5 Digital media & document intelligence

**Gap addressed:** Doc 29a §10 explicitly leaves OCR and PDF parsing open (only DOM text + local PNG hash/dimensions implemented).

**Requirements:**
1. PDF/DOCX/spreadsheet text extraction with page/sheet-level attribution; extracted text inherits the source evidence contract from §2.2.
2. OCR adapter for scanned documents/images, optional and local-first; layout understanding (tables, reading order, footnotes) recorded as best-effort with confidence, never as verified claim by itself.
3. Metadata/EXIF extraction, document-format conversion and metadata sanitisation before content enters knowledge storage.
4. A/V transcription and video-frame analysis are autonomous when performed locally on free material after the §2.0 legal check; hosted providers require the OD-51/OD-04 gates and must never receive private material (OD-48 AT-11).
5. C2PA/watermark verification and deepfake detection are research-stage indicators: they may annotate evidence but must not be treated as proof of authenticity.
6. Upload/download size caps, malware scan and quarantine on all media (Doc 29 §4.9/§5.2); page/media content remains untrusted data, never instructions.

**Acceptance:** PDF citation test; scanned-OCR test; oversized-file rejection; secret-in-metadata sanitisation test; injection text embedded in an image is not executed as instruction.

---

### 2.6 Internet security & threat intelligence

**Gap addressed:** Aegis has defensive research and egress checks, Doc 06 §4 says "monitor vulnerabilities" generically, but no feed ingestion, DLP or unified rotation exists.

**Requirements:**
1. **External threat-intel feeds.** Allowlisted NVD/OSV/advisory sources; deduplicate by CVE/advisory ID; expiry and trust scoring; map advisories to SBOM/dependency records; emit defensive recommendations only. No offensive tooling, scanning or exploitation (OD-16 §5, OD-34 §14).
2. **DLP.** Classification tags on private data; egress rules across chat, browser upload, email and service APIs; block on classified matches with an audit event. Browser upload controls and Aegis secret detection remain the base; this adds cross-channel policy.
3. **Network stack policy.** DNSSEC/DoH/DoT status recording, explicit IPv6 dual-stack/NAT64 rules, authenticated proxy support, mandatory TLS verification — all implemented through §2.1 rather than a second stack.
4. **Cross-domain credential vault.** Unify model-provider keys (OD-51 §4.1), browser credentials (Doc 29 §5.4) and service credentials under one rotation/expiry policy with scoped access. Keys never enter model context, logs or notes.
5. Threat-intel sharing with trusted nodes stays outbound and privacy-safe (Doc 06 §4/§5); no private memory to an external provider (OD-48 §3.7, OD-51 §6).

**Acceptance:** feed-ingest and dedup test; CVE→dependency mapping test; DLP block test; rotation/expiry test; offensive-capability rejection test; paid NVIDIA usage remains blocked (OD-51 §4.5).

---

### 2.7 Knowledge memory & source management

**Gap addressed:** provenance exists (Doc 14 §6, Doc 29 §7.2) but no rights registry, freshness classes, claim-level evidence or revocation propagation.

**Requirements:**
1. `SourceRegistry` fields: rights set (`read`, `store`, `analyse`, `derive`, `train`, `commercial`), licence, expiry/revocation, territory, reliability score, retrieval history, duplicate/syndication flags, contradiction history.
2. Reuse the §2.2 TTL classes and confidence thresholds; store them once, not in two competing implementations.
3. Claim-level evidence records exactly as specified in §2.2 item 5; source reliability and rights are consulted before any reuse, derivation or training admission.
4. **Revocation propagation.** Revoking or expiring a source marks derived knowledge, derived datasets and trained-model evidence as affected; blocks further use in research, actions and training; retains immutable historical record. Does not silently delete history (Doc 26).
5. Source lifecycle owner and review SLA defined per source class; unowned sources fail closed.

**Acceptance:** revoke-source→derived-artifact flag test; rights-denied training block; duplicate-source detection; claim-to-source round-trip.

---

### 2.8 Internet governance & privacy

**Gap addressed:** Doc 15/OD-31 and OD-48 cover site-level legal behaviour but not versioned policy, full privacy lifecycle or internet-governance intelligence.

**Requirements:**
1. **SitePolicyStore.** Versioned snapshots of terms, robots directives and API terms with timestamp, TTL and change alerts; cached decisions with TTL and the originating `audit_event_id`; this store supplies versioned policy evidence to the §2.0 legal check. `robots.txt` remains a crawling signal, never permission; no CAPTCHA/paywall/access-control bypass (OD-48 §3.6, Doc 29 §5.5).
2. **Privacy lifecycle.** Purpose limitation on collection; DPIA trigger and record; DSAR/erasure workflow with propagation to derived artifacts; consent-withdrawal propagation beyond `website_consent` rows; data-residency tags; breach events recorded in the existing incident model.
3. **Cross-border transfers.** SCC/adequacy/transfer-impact-assessment evidence required before any transfer, including to hosted AI providers; absent evidence blocks transfer (OD-48 AT-11, OD-51 §6).
4. **Identity standards.** Optional W3C DID/Verifiable Credential verification and selective-disclosure proofs; no impersonation of the Creator, no unauthorised account creation, no secrets in logs or model context.
5. **Internet-governance monitoring** (ICANN/IANA, IETF/W3C, RIR and regulator publications) is a *research topic* feeding Doc 15 monitoring — not participation authority, not legal advice, not a basis for autonomous commitments (OD-48 §1.6).

**Acceptance:** TOS-change alert test; robots-as-signal test; DSAR deletion propagation test; transfer-evidence gate test; no-impersonation test.

---

### 2.9 Continuous self-improvement & QA

**Gap addressed:** model QA is strong (OD-38/46/40/41); internet-capability QA is a static checklist, not a recurring scored loop.

**Requirements:**
1. **Recurring scored benchmarks** with numeric thresholds: search precision/freshness, source-attribution accuracy, extraction fidelity, provider failover success, browser-engine regression, robots/TOS decision accuracy, egress/SSRF/injection test pass rate.
2. **Regression stop-gate.** A change to source policy, egress rules, credential handling or media adapters may not deploy if a critical benchmark regresses past threshold. Model changes still require the signed OD-46 release; a benchmark alone never auto-promotes a model (OD-38 §6, OD-40 §7.8).
3. **Feedback loop.** Incidents, Creator corrections and QA failures feed benchmark corpora and control updates; each update carries owner, evidence and rollback plan.
4. **Corpus governance.** Web evaluation snapshots require licence, freshness and contamination checks; private data excluded from metrics and corpora (OD-37 §4.14, OD-48).
5. Benchmarks run on a schedule and on change; results retained as evidence; offline-capable local execution so QA does not depend on hosted providers.

**Acceptance:** baseline run recorded; injected regression blocked by gate; rollback verified; evidence retained; no private data in benchmark output.

---

## 3. Reuse — do not build a second copy

All closures extend existing services; none creates a parallel runtime system:

| Existing module | Reused for |
|---|---|
| `backend/app/services/search_service.py` | provider health, failover (§2.2) |
| `backend/app/services/research_service.py` | strategy, confidence, evidence (§2.2) |
| `backend/app/services/browser_service.py`, `browser_intelligence_service.py` | extraction, media adapters, page evidence (§2.5) |
| `backend/app/services/internetaccess_service.py` | permissions, monitored targets, event history (§2.3) |
| `backend/app/services/autonomous_web_task_service.py`, ARQ workers | scheduled research, ledger (§2.3) |
| `backend/app/services/web_knowledge_service.py`, `memory_service.py` | source registry, claim memory (§2.7) |
| `backend/app/services/aegis.py`, `security_policy.py` | egress decisions, threat intel, DLP (§2.1, §2.6) |
| `backend/app/services/iplci/service.py` | mandatory `/gate/check` permissibility decision (§2.0) |
| `backend/app/services/hbi/http_fetcher.py` | robots/byte-cap precedent, generalised in §2.1 |

---

## 4. Sequencing

1. **Foundation:** §2.1 egress gateway, §2.3 ledger + budget, §2.7 source registry, §2.9 QA harness.
2. **Intelligence:** §2.2 strategy/confidence/TTL, §2.4 pipeline separation gate (pending OD-47).
3. **Depth:** §2.5 media/document adapters, §2.6 threat intel/DLP/vault.
4. **Governance:** §2.8 site policy store and privacy lifecycle.
5. **Closure:** recurring QA thresholds and regression gate active across all prior phases.

No phase is called complete on assumed success; each has its own acceptance evidence.

---

## 5. Owner decisions required

- **OD-47 (proposed):** §2.4 and part of §2.7 become frozen only after a signed decision.
- **OD-52 (proposed):** search triggers, provider management, TTL and claim labels in §2.2 are already drafted there; promote by signed decision rather than duplicating.
- **Scope ruling:** confirm that §2.1 link/physical networking, host VPN lifecycle and ICANN/IETF participation stay out of IAM runtime scope.
- **No system-count change** is requested. Any request to make IICS a top-level system requires a separate gap-analysis-proven omission and signed reopening.
- **Approval interpretation:** the items above are decisions to freeze architecture, **not** per-action Creator approvals. Free lawful use stays autonomous under §2.0; the legal gateway decides permissibility, and Creator approval attaches only to the consequential-action list.

---

## 6. What this addendum does not do

It does not amend `ARCHITECTURE_INDEX.md` authority tables, the Owner Decision Register, `IAM_FINAL_CONSOLIDATION.md`, Doc 29/OD-49 status, or any implementation file. It does not authorise payments, hosted-model dependence, account registration, offensive security work, automatic model promotion, or changes to IAM's identity, constitution or protected core.

---

## 7. Implementation status — foundation layer landed

The addendum remains a **proposal**, not frozen authority. The following foundation code now exists and is the source of truth for what runs:

| Closure | Implemented | Location |
|---|---|---|
| §2.1 egress decisions | URL assessment, SSRF/metadata blocking, DNS rebinding pinning, TLS verification, caps, auditable decision record, bounded redirect re-check | `backend/app/services/iics/egress.py` |
| §2.0 permissions | Combines `InternetAccessService` public-exploration gates with the mandatory OD-48 `/gate/check`; free lawful access autonomous; approval only for consequential actions or fail-closed legal decisions | `backend/app/services/iics/permissions.py` |
| §2.3 ledger + budget | Append-only action records, idempotency keys, scope gate, verification state, windowed action/byte/cost budget | `backend/app/services/iics/ledger.py` |
| §2.7 source registry | Rights, TTL classes, confidence labels, claim evidence, revocation propagation to derived claims | `backend/app/services/iics/source_registry.py` |
| §2.9 QA harness | Scored benchmark cases and regression stop-gate | `backend/app/services/iics/qa.py` |
| API surface | Egress check, authorize, actions, sources, claims and QA endpoints under `/api/v1/iics` | `backend/app/api/routes/iics.py` |
| Persistence | Four tables (`iics_sources`, `iics_claims`, `iics_actions`, `iics_benchmark_results`) | `backend/app/models/iics.py`, `backend/app/db/migrations/057_iics_foundation.sql` |
| §2.3 / Creator control centre — email path | Informational status updates, QA regression alerts and monitoring digests via the existing OD-18/OD-19 email layer; consequential actions raise signed ED25519 challenge requests delivered by email. A plain reply never grants authority. | `backend/app/services/iics/creator_email.py`, `/api/v1/iics/creator/*` |
| §2.2 strategy/confidence | Strategy taxonomy (single, decomposition, source-first, refinement, contradiction), rationale and evidence-weighted confidence calibration | `backend/app/services/iics/search_strategy.py` |
| §2.3 scheduled research | Governed recurring research jobs on the existing ARQ runtime with bounded retries, ledger records and no side-effect replay | `backend/app/services/iics/scheduler.py`, `backend/app/workers/arq_iics_worker.py` |
| §2.5 media/documents | PDF/DOCX page-attributed extraction, optional local OCR, EXIF extraction and metadata sanitisation, hard size caps, untrusted-data labelling | `backend/app/services/iics/media.py` |
| §2.6 security | OSV/NVD advisory parsing, dedup, CVE→SBOM mapping, cross-channel DLP with audit events, credential-reference rotation scheduling. Defensive only (OD-16/OD-34). | `backend/app/services/iics/threat_intel.py` |
| §2.8 governance/privacy | Versioned robots/TOS snapshots with TTL and change detection, DSAR/consent/transfer records with evidence-gated transfer decisions | `backend/app/services/iics/site_policy.py` |
| §2.9 QA persistence | Benchmark runs stored with thresholds and evidence; regression gate compares against the previous stored baseline | `/api/v1/iics/qa/run`, `/api/v1/iics/qa/results` |
| Wiring | Egress enforced in `browser_service` navigation/fetch and both HBI HTTP fetchers; combined legal gate enforced in `InternetAccessService.check_permission`; DLP enforced on browser type/upload and Creator email; IICS tools registered at startup in `ToolRegistry`; IICS ARQ worker added to `docker-compose.yml`; permission denials and QA regressions notify the Creator automatically; threat-feed and site-policy poll jobs registered as ARQ cron jobs | `backend/app/services/iics/tool_registry.py`, `app/workers/arq_iics_worker.py`, `app/main.py`, `docker-compose.yml` |
| Tests | 54 unit tests in `backend/tests/test_iics_foundation.py`; full backend suite 939 passed | — |

Operational closure:
- Migration `057_iics_foundation.sql` has an idempotent applier (`backend/scripts/apply_iics_migration.py`), a one-shot Compose service (`iics-migrate`) and is included in `backend/tests/integration_db_check.py`. Local runs use `create_all`; a deployment must run `docker compose --profile iics run --rm iics-migrate` once.
- Threat-intel feed is configured by default to the public NVD 2.0 API (`IICS_THREAT_FEEDS`, documented in `.env.example`); polling is via the IICS ARQ cron.
- Graphical Creator control centre exists at `/_iics` (`frontend/components/iam/panels/iics-control-panel.tsx`) with egress/permission checks, QA, scheduled jobs, advisories and Creator email actions.
- An opt-in live smoke test is available: `IAM_IICS_SMOKE=1 IAM_API_KEY=<key> python tests/iics_live_smoke.py` (prints `IAM_IICS_OK` only when every check passes).

Free lawful research remains autonomous and does not email the Creator; email notifications are informational, and consequential actions require a signed Creator decision. No further backlog item requires a system-count change.
