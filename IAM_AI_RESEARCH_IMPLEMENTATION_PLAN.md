# IAM — AI Research and Model Development Implementation Plan

**Status:** Implementation plan for OD-41 (requirements frozen)  
**Source of truth:** `IAM_INDEPENDENT_AI_RESEARCH_DEVELOPMENT_AND_EVOLUTION_ARCHITECTURE.md` (14 engines + section 15)  
**Related:** OD-15/OD-35 (OEDIE/free nodes), OD-36 (SDK/framework research), OD-38 (foundation model), OD-39 (resources), OD-40 (MEFE), `IAM_FREE_SANDBOX_API_ADAPTER_SPEC.md` (Doc 22), `IAM_IMPLEMENTATION_TECHNOLOGY_ADDENDUM.md` (cross-cutting Python + Rust + TypeScript allocation)  
**Rule:** This plan does not add new subsystems. It sequences the frozen capability into deliverables.

---

## 1. Guiding constraints

- Free resources first; no paid compute, upgrades or binding commitments without Creator approval (OD-04/OD-25/OD-41).
- Temporary notebooks are research workers only — never IAM's identity, memory or core intelligence.
- Every experiment is reproducible and every artifact lands in IAM-controlled storage before a session expires.
- Reuse existing components instead of rebuilding them: `backend/app/services/free_sandboxes/` (discovery, adapters, quota, monitor, registration, results), `tests/model_competition/` (benchmark harness), the SDK scaffold in `sdk/`, Skill Forge runtime, and MinIO/S3 storage.
- Hybrid implementation (cross-cutting addendum): Python keeps research, model and FastAPI responsibilities; Rust may be used for infrastructure components **only** behind the same contracts and **only** after the measured-benefit gate (A19). No completed Python component is rewritten to satisfy a language preference.

Priorities: **P0** = foundation/blocking, **P1** = core capability, **P2** = extension/optimisation.

---

## 2. Work packages and dependencies

| ID | Work package | Priority | Depends on | Deliverable |
|----|--------------|----------|------------|-------------|
| WP0 | Research artifact contract | P0 | — | Versioned job/result/checkpoint schemas; S3 layout; immutable experiment IDs |
| WP1 | Credential and secret handling | P0 | WP0 | Encrypted per-platform credentials, scoped expiry, no secrets in notebooks or logs |
| WP2 | Platform quota model | P0 | WP0 | Extend `free_sandboxes/quota.py` with GPU type, VRAM, session limits, quota checks |
| WP3 | Common training-job format | P0 | WP0 | One job spec usable by every adapter (model, dataset, method, hardware, budget, output) |
| WP4 | Research coordinator | P1 | WP0, WP3 | Central service that designs, prioritises, submits and tracks experiments |
| WP5 | Platform adapters | P1 | WP1, WP2, WP3 | Colab (Kaggle as training-only), Lightning AI, HF ZeroGPU adapters behind one interface |
| WP6 | Persistent artifact store | P1 | WP0, WP1 | Checkpoints, datasets, logs, benchmark reports in IAM S3; session-expiry safe |
| WP7 | Benchmark runner | P1 | WP3, WP6 | Reuse `tests/model_competition/` harness; lm-evaluation-harness; custom IAM tasks |
| WP8 | Capability profiles / model introspection | P1 | WP6, WP7 | Per-model measured profile (strengths, limits, hardware, failure modes) |
| WP9 | vLLM serving experiments | P1 | WP5, WP6 | Colab T4+ vLLM server; OpenAI-compatible API smoke; throughput/memory/concurrency report |
| WP10 | Fine-tuning jobs | P1 | WP3, WP5, WP6 | SFT + QLoRA via PEFT/TRL/Unsloth; checkpoints saved to S3 |
| WP11 | Autonomous recovery | P1 | WP4, WP6 | Failure detection, retry, resume from checkpoint, switch platform |
| WP12 | Intelligent scheduling | P2 | WP2, WP4, WP11 | Pick platform by GPU/VRAM/RAM/CPU/storage/quota and workload fit |
| WP13 | Platform lifecycle management | P2 | WP2, WP5 | Discover new platforms, monitor quota changes, retire unsuitable ones |
| WP14 | Model registry and approval gates | P2 | WP6, WP8, WP10 | Versioned releases, validation, Creator gate for protected changes, rollback |
| WP15 | Research memory / continuous improvement | P2 | WP7, WP8, WP14 | Retain failed experiments; feed findings into next experiment design |
| WP16 | Security and isolation | P0 (cross-cutting) | WP1, WP5 | Untrusted-code isolation, download verification, private-data leakage prevention |

Dependency chain: WP0 → WP1/WP2/WP3 → WP4/WP5/WP6 → WP7/WP9/WP10/WP11 → WP8/WP12/WP13/WP14 → WP15.

### 2a. Implementation-language classification (cross-cutting addendum)

This table classifies work packages under `IAM_IMPLEMENTATION_TECHNOLOGY_ADDENDUM.md`. It changes no work package, dependency or acceptance test; a "Rust candidate" is a **permitted implementation**, not a committed rewrite, and is subject to A19/A20.

| WP | Implementation position | Requirement |
|----|-------------------------|-------------|
| WP0 artifact contract | Language-neutral | Schemas and experiment IDs must be defined without Python- or Rust-specific types; both languages can produce/consume them (A18). |
| WP1 credentials | Python (existing) | Rust components never hold credential values or signing material; env-var references and redaction semantics preserved (A18). |
| WP2 quota model | Rust candidate | Quota policy stays single-source; a Rust implementation must produce identical decisions and pass A2. |
| WP3 common job format | Language-neutral | The job spec remains one cross-language contract (A3/A18). |
| WP4 coordinator | Python initially | Orchestration stays in the existing service; Rust only for measured hot paths behind the same API (A19). |
| WP5 platform adapters | Python initially | Adapter interface unchanged; no replacement queue runtime (OD-08). |
| WP6 persistent artifact store | Rust candidate | I/O and digest engine may be Rust; `ArtifactStore` protocol, S3 adapter and integrity metadata unchanged (A5/A18). |
| WP7 benchmark runner | Python | Evaluation logic stays Python; Rust only for transport where measured beneficial. |
| WP8 capability profiles | Python | Measured-value selection logic unchanged (A7). |
| WP9 vLLM serving | Python/serving stack | Rust may be used for integration/transport only, never for model execution. |
| WP10 fine-tuning jobs | Python | PEFT/TRL/Unsloth ecosystem retained (OD-40). |
| WP11 autonomous recovery | Python initially | Rust only behind the same contract; Creator-approval boundary unchanged (A16). |
| WP12 intelligent scheduling | Rust candidate | Natural fit for concurrent, low-jitter scheduling; must satisfy OD-39 and A11/A19. |
| WP13 platform lifecycle | Rust candidate | Monitoring/discovery engine may be Rust; quota semantics unchanged (A12). |
| WP14 registry and gates | Python initially | Signed Creator approval gates stay with the existing services (OD-03/OD-11). |
| WP15 continuous improvement | Python | Research-memory logic stays Python. |
| WP16 security and isolation | Rust candidate | Strong fit for boundary enforcement, but must enforce the full policy of `security.py` (A14/A20). |

---

## 3. Phased sequence

### Phase 0 — Foundations (WP0, WP1, WP2, WP3, WP16) — P0
Define the contracts and safety boundary before any external job runs.

### Phase 1 — Coordinator and first adapters (WP4, WP5, WP6) — P0/P1
One common job submitted to a stub, then to Colab and Kaggle (training only). All outputs persisted.

### Phase 2 — Evaluation (WP7, WP8) — P1
Reproducible benchmarks, comparison store and capability profiles. No model is "better" without evidence.

### Phase 3 — Serving and training (WP9, WP10) — P1
vLLM on Colab T4+ with the locked `Qwen2.5-Coder:3B`; QLoRA fine-tuning jobs on eligible platforms.

### Phase 4 — Autonomy (WP11, WP12, WP13) — P1/P2
Retry/resume/switch, quota-aware scheduling, platform discovery and retirement.

### Phase 5 — Registry and improvement (WP14, WP15) — P2
Approved releases, rollback, and learning across experiments.

---

## 4. Acceptance tests

| ID | Acceptance test | Pass condition |
|----|-----------------|----------------|
| A0 | Artifact contract | A sample job produces versioned input, config, log, checkpoint and result records that survive a simulated session expiry. |
| A1 | Secret isolation | No credential appears in job specs, logs, benchmark output or repository files; credentials expire on schedule. |
| A2 | Quota gate | A job is refused when the adapter reports insufficient GPU/VRAM/session quota; no paid upgrade is ever triggered automatically. |
| A3 | Common job format | The same job spec runs unchanged against two different adapters (stub + one real platform). |
| A4 | Coordinator | Given a task type and complexity, the coordinator records a routing decision and a prioritised experiment ID. |
| A5 | Persistence | After a notebook session ends, code/data/checkpoints/results are retrievable from IAM S3 by experiment ID. |
| A6 | Benchmark reproducibility | Running the same benchmark twice on the same recorded config/hardware produces results within a declared tolerance; failed experiments are retained. |
| A7 | Capability profile | Each evaluated model has a profile with measured strengths, failures, RAM/CPU needs and context limits; selection uses the profile, not the model name. |
| A8 | vLLM serving | On a verified T4+ (compute capability ≥7.5), a vLLM server answers an OpenAI-compatible `/v1/chat/completions` request; throughput, peak VRAM and concurrency are recorded. Kaggle P100 is explicitly rejected for vLLM (capability 6.0 < 7.5). |
| A9 | Fine-tuning | A QLoRA job completes, writes a checkpoint to S3, and post-training benchmarks are compared with the recorded baseline. |
| A10 | Autonomous recovery | An injected mid-job failure is detected; the job resumes from its last checkpoint or is resubmitted to another eligible platform; no Creator prompt for routine recovery. |
| A11 | Intelligent scheduling | Two platforms with different GPU/RAM/quota are offered the same job; the scheduler selects the one matching the declared workload fit and records why. |
| A12 | Platform lifecycle | A simulated quota change marks a provider degraded and prevents new submissions until re-validated. |
| A13 | Registry and rollback | A model version can be approved, deployed and rolled back; protected-core changes require signed Creator approval (OD-03/OD-11/OD-19). |
| A14 | Security and privacy | Downloaded model/dataset hashes are verified; untrusted notebook code runs isolated; no private user data appears in external platform inputs. |
| A15 | Continuous improvement | A failed experiment's diagnosis appears as an input to the next experiment plan. |
| A16 | Autonomy boundary | Routine work completes without Creator prompts; paid/binding/protected actions stop and request Creator authority. |
| A17 | Rust workspace and standards | A Rust workspace builds on x86-64 and ARM64 (OD-22) and on the developer host; `cargo fmt --check`, `cargo clippy -- -D warnings` and `cargo audit` pass in CI; toolchain is pinned. |
| A18 | Python–Rust interoperability | A Rust component and the FastAPI service exchange a versioned, language-neutral job/result message with identical semantics; contract tests pass in both languages; no credential, signing material or private-state access crosses the boundary. |
| A19 | Measured-benefit gate | For every Rust candidate, the incumbent Python baseline and the Rust measurement are recorded on declared hardware with the same config; the candidate is adopted only if it meets a declared latency/throughput/memory target and passes every incumbent acceptance test — otherwise Python is retained and the evidence is kept. |
| A20 | Security and isolation parity | Any Rust isolation or integrity component enforces the same no-core-access / no-default-network policy, hash verification, private-data markers and redaction as `security.py`; A14 still passes unchanged. |

---

## 5. Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| Free GPU unavailable or queued | Multiple adapters; scheduler picks any eligible platform; experiments are idempotent and resumable. |
| Session expires mid-job | Stream checkpoints/logs to IAM S3 (A5); resume from last checkpoint (A10). |
| vLLM compute-capability mismatch | Verify GPU capability ≥7.5 before launch; Kaggle P100 training-only (A8). |
| Accidental paid spend | Hard deny of paid upgrades; quota gate (A2); Creator approval boundary (A16). |
| Licence/terms violation | Live terms/quota verification (OD-35); provenance and licence fields on datasets/models. |
| Untrusted code or data leakage | Isolation and download verification (A14); private conversations never enter training sets (OD-40). |
| Mistaking successful training for quality | Independent quality control (A7, A9); benchmark before promotion. |
| Subsystem proliferation | OD-41 freezes requirements; changes require reopening the decision. |
| Premature Rust rewrite of working Python code | Measured-benefit gate A19; language allocation in §2a; locked interfaces (OD-08, Doc 01 §5) are not replaced. |
| Cross-language contract drift | Schema-first definitions and dual-language contract tests (A18); one implementation per responsibility. |
| Rust component weakens the safety boundary | Isolation parity A20; signing and Creator gates remain in the existing Python services. |

---

## 6. Definition of done

The capability is implemented when P0/P1 work packages WP0–WP11 pass acceptance tests A0–A11, P2 packages WP12–WP15 pass A12–A15, and A16 is verified end to end. Any Rust implementation additionally requires A17–A20. At that point IAM can submit one approved experiment to multiple free platforms, compare results centrally, retain artifacts, recover from failures, and register or roll back a model — autonomously within its authority, with Creator involvement only where explicitly required.

A17–A20 apply prospectively to new infrastructure work; they do not invalidate the completed Python Phase 0–2 results recorded below.

---

## 7. Progress log

### Phase 0 — COMPLETE (25 November 2026)

| Work package | Implementation | Acceptance |
|--------------|----------------|------------|
| WP0 artifact contract | `backend/app/services/ai_research/artifacts.py` — immutable experiment IDs, artifact kinds, deterministic `experiments/{id}/{kind}/{file}` layout, SHA-256, atomic writes, `ArtifactStore` protocol + `FileSystemArtifactStore` | A0 ✅ |
| WP1 credentials | `credentials.py` — env-var references, expiry, value never stored in manifests, `assert_no_credentials`, `redact` | A1 ✅ |
| WP2 quota model | `quotas.py` — GPU name/capability/VRAM, RAM, session and concurrency limits, paid-upgrade refusal, safety margin, ranking | A2 ✅ |
| WP3 common job format | `jobs.py` — `ResearchJob` / `HardwareRequirement` / `ResearchMethod`, validation, stable manifest round-trip | A3 ✅ |
| WP16 isolation/security | `security.py` — integrity digests, isolation policy (no core access, no default network), private-data markers, untrusted output wrapping | A14 ✅ |
| Orchestration | `service.py::prepare_job` — fail-closed validation → isolation → privacy → secret check → persistent manifest | A0–A3, A14 |

Tests: `backend/tests/test_ai_research_phase0.py` — **17 passed**. Full backend suite: **131 passed** (one pre-existing missing `SandboxError` import in `test_free_sandboxes.py` was corrected).

**Deliberately deferred to Phase 1:** the S3 artifact adapter (only the local/file store exists today), real platform adapters, coordinator, result collection, vLLM and training jobs. No paid compute path exists anywhere in Phase 0.

### Phase 1 — COMPLETE (25 November 2026)

| Work package | Implementation | Acceptance |
|--------------|----------------|------------|
| WP4 coordinator | `backend/app/services/ai_research/coordinator.py` — plans, ranks platforms via the GPU-aware quota gate, refuses jobs with no eligible platform, persists the manifest before submission, audits every step, collects results | A4 ✅ |
| WP5 adapters | `adapters.py` — Colab (T4, 7.5, serving-capable), Kaggle (P100, 6.0, **training only**), Lightning AI, HF ZeroGPU (short sessions). All are fail-closed until a driver is injected. | A2/A4 ✅ |
| WP6 artifact store | `s3_store.py` — injectable boto3 S3-compatible store with integrity metadata and key prefixing; same `ArtifactStore` protocol as the file store | A5 ✅ |
| Result collection | `coordinator.collect()` — external output wrapped as untrusted, redacted and persisted as a result artifact | A14 ✅ |

Tests: `backend/tests/test_ai_research_phase1.py` — **8 passed** (A4 submit/audit, A5 survival after simulated session expiry, S3 round-trip/integrity, untrusted result storage, Kaggle serving refusal, no-driver fail-closed, paid platform never selected). Full backend suite: **142 passed**.

**Important limitation:** no live Colab/Kaggle credentials or notebook drivers are configured, so no real external job has been submitted. Adapters refuse to provision until a driver is injected — this is deliberate fail-closed behaviour, not a completed integration. vLLM serving and QLoRA training jobs remain Phase 3 work.

### Phase 2 — COMPLETE (25 November 2026)

| Work package | Implementation | Acceptance |
|--------------|----------------|------------|
| WP7 benchmark runner | `benchmarks.py` — `BenchmarkSpec` / `BenchmarkResult`, custom and pluggable `lm_eval` evaluators, repetitions, score bounds, config/hardware fingerprint, reproducibility tolerance, retention of failed experiments | A6 ✅ |
| WP8 capability profiles | `profiles.py` — `CapabilityProfile` (strengths, limits, hardware, context, languages, known failures, safety, training history, benchmark scores), `CapabilityRegistry.record/profile/select` — selection by **measured** score, never model name or parameter count | A7 ✅ |

Tests: `backend/tests/test_ai_research_phase2.py` — **6 passed** (A6 reproducible runs, tolerance/config-hash rejection, failed-experiment retention; A7 profile construction, name-independent selection, unknown-model and unmet-threshold refusal, low scores recorded as known failures). Full backend suite: **148 passed**.

**Important limitation:** the `lm_eval` path is a driver interface only — no `lm-evaluation-harness` installation or live model evaluation has been performed. Benchmarks were exercised with stub evaluators; capability profiles contain no production model scores yet.

### Phase 3 — COMPLETE (25 November 2026)

| Work package | Implementation | Acceptance |
|--------------|----------------|------------|
| WP9 serving | `serving.py` — `ServingSpec`, vLLM capability gate (>=7.5), Ollama option, `OpenAICompatibleClient` for `/v1/chat/completions`, `ServingExperimentRunner` with health check, latency/throughput/VRAM report and artifact | A8 ✅ |
| WP10 training | `training.py` — `FineTuneSpec` for SFT/LoRA/QLoRA/full/distillation, common-job submission via the coordinator, checkpoint artifact, `validate_improvement` quality gate | A9 ✅ |

Tests: `backend/tests/test_ai_research_phase3.py` — **7 passed** (A8 exercised against a local OpenAI-compatible HTTP stub server: smoke reply, throughput/VRAM report, endpoint shutdown, artifact persistence; P100 rejected for vLLM; Ollama allowed without CUDA capability. A9 QLoRA job build/submission, checkpoint persistence, quality-gate rejection of no improvement, fail-closed validation). Full backend suite: **160 passed**.

**Important limitation:** no real GPU or vLLM binary was used, and no live QLoRA training ran. The OpenAI-compatible client was tested against a local stub server; platform drivers and credentials are still required for real serving/training jobs.

### Phase 4 — COMPLETE (25 November 2026)

| Work package | Implementation | Acceptance |
|--------------|----------------|------------|
| WP11 recovery | `recovery.py` — `JobRecovery` diagnoses failure, retries on another eligible free platform, resumes from a checkpoint reference, audits each attempt, exhausts to `ProviderUnavailable` with no paid fallback | A10 ✅ |
| WP12 scheduling | `scheduler.py` — `WorkloadProfile` (VRAM/RAM/capability/runtime/complexity/preference), rank + best with scored fit and reasons, fail-closed quota gate | A11 ✅ |
| WP13 lifecycle | `lifecycle.py` — discover/monitor/degrade/retire/revalidate platform records with quota history; coordinator accepts `eligible_providers` so degraded providers cannot receive jobs | A12 ✅ |

Tests: `backend/tests/test_ai_research_phase4.py` — **6 passed** (A10 platform switch + checkpoint resume + audit, exhausted recovery without paid fallback; A11 P100 rejected for CUDA workload and no-eligible case; A12 degraded platform blocked until revalidated, repeated degradation retires provider). Full backend suite: **166 passed**.

**Important limitation:** recovery, scheduling and lifecycle were tested against stub adapters, not live platform APIs. Real quota feeds and notebook drivers are still required.

### Phase 5 — COMPLETE (25 November 2026)

| Work package | Implementation | Acceptance |
|--------------|----------------|------------|
| WP14 registry | `registry.py` — `ModelVersion` register → approve → deploy → rollback with persisted artifacts, benchmark/profile evidence requirement, signed Creator approval gate for protected changes | A13 ✅ |
| WP15 research memory | `memory.py` — `ExperimentRecord` persistence, failure/success indexes, `suggest_next()` turning diagnoses and tags into the next experiment's inputs | A15 ✅ |
| Autonomy boundary | `governance.py` — `ActionKind` + `AutonomyGate`; routine work is autonomous, paid/binding/human-only/protected-core actions require `SignedApproval` | A16 ✅ |

Tests: `backend/tests/test_ai_research_phase5.py` — **7 passed** (A13 approve/deploy/rollback, unapproved deployment blocked, protected change requires signed approval; A15 failure diagnosis feeds next plan, empty-history behaviour; A16 routine work without approval, authority actions require signed approval). Full backend suite: **173 passed**.

**Implementation plan status: COMPLETE.** All P0/P1/P2 work packages WP0–WP16 have implementations and all acceptance tests A0–A16 pass in code. One externally changed config default (all adaptive tier aliases now `local-qwen-3b`) was left untouched; the affected test was made independent of config defaults.

**Remaining real-world work (not code):** inject live platform drivers and credentials, install/execute vLLM and QLoRA on eligible GPUs, replace stub evaluators with `lm-evaluation-harness` scores, and populate capability profiles and the model registry with measured production results. Final deployment decisions still belong on the Contabo VPS.

---

## 8. Real-world integration readiness — started (25 November 2026)

Readiness scan:
- No platform credentials (`COLAB_TOKEN`, `KAGGLE_API_TOKEN`, `HF_TOKEN`, `LIGHTNING_API_KEY`, hosted inference keys) are configured in the environment or `.env`.
- `vllm`, `torch`, `transformers` and `lm_eval` are not installed locally.
- Local GPU exists (GTX 1660 Ti, 6 GB, compute capability 7.5) but vLLM is Linux/CUDA and only Python 3.15 on Windows is available — no local serving run was attempted.

Prepared: `research/colab/IAM_vLLM_Qwen_Coder_3B.ipynb` (11 cells) plus `research/colab/README.md`. The notebook checks GPU capability >= 7.5, installs vLLM, serves `Qwen/Qwen2.5-Coder-3B-Instruct` with an OpenAI-compatible API, runs the unchanged IAM coding task, records latency/VRAM/tokens, and uploads to IAM S3 from Colab secrets. It is **authored but not executed**.

---

## 9. Self-improvement release gate (Phase 7, 26 November 2026)

`backend/app/services/ai_research/release_gate.py` joins the existing evidence
and authority pieces: `POST /api/v1/development/models/versions` registers a
candidate with dataset SHA-256, licence, consent and poisoning-scan provenance;
`POST /api/v1/development/models/{model}/versions/{version}/promote` requires two
reproducible `BenchmarkResult` artifacts with a matching config hash, a declared
minimum improvement via `TrainingService.validate_improvement`, complete
provenance and an active signed `CreatorAuthorization`
(`development.model_release`, scoped to `model@version`), then writes the DB
model/evaluation/upgrade records and an audit event. `POST .../rollback` applies
the same signed-authority gate. `ModelRegistry.hydrate()` restores versions and
the active model after restart. Tests: `backend/tests/test_model_release.py`
(6 passed). `backend/app/services/irwm.py` now enforces the OD-39 runtime policy: one
resident model, one in-flight request, a hard RAM ceiling, the core-service
reserve, bounded context, idle unload after keep-alive, and queue/delegate
decisions instead of evicting core services. It is exposed at
`/api/v1/irwm/{status,admit,release,sweep}`; `/models/router/select` can now
pass `task_complexity` and `available_aliases` so adaptive selection is
reachable via API. Tests: `backend/tests/test_irwm.py` (6 passed).
`backend/app/services/model_independence.py` now activates the previously
orphaned `model_comparisons`, `model_portability_exports` and
`fallback_configs` tables: weighted OD-38 scoring, signed primary-model
adoption, private-content-free portability exports (permanent ID, public name,
goal/skill descriptors only) and signed fallback configuration. The previously
hard-coded vision model is now `VISION_MODEL`-configurable. Tests:
`backend/tests/test_model_independence.py` (7 passed). Target-hardware
competition evidence and live serving/training remain externally bound work.

Blockers before live experiments: supply free-platform credentials (or run the notebook manually in Colab), inject notebook drivers into the adapters, and replace stub evaluators with real `lm-evaluation-harness` results. Paid or protected actions still require signed Creator approval (A16).

### Implementation technology note (25 November 2026)

The cross-cutting addendum `IAM_IMPLEMENTATION_TECHNOLOGY_ADDENDUM.md` adopts a hybrid Python + Rust + TypeScript allocation. Research Phases 0–2 above remain Python and are **not** rewritten. Rust candidates in §2a apply from Phase 3 onward and to the base Phase 0/1 build, and each must pass A17–A20 before adoption.

## 10. World model reasoning (Phase 10, 26 November 2026)

`backend/app/services/worldmodel_service.py` and `backend/app/api/routes/worldmodel.py`
activate the existing world-model tables: `GET/POST /api/v1/world/entities`,
`GET/POST /api/v1/world/relationships`, `GET/POST /api/v1/world/cause-effect`,
`GET/POST /api/v1/world/events`, `GET/POST /api/v1/world/capabilities`.

New reasoning endpoints:
- `GET /api/v1/world/entities/{id}` — single entity with properties and confidence.
- `POST /api/v1/world/traverse` — breadth-first traversal of entity relationships
  up to a bounded depth (max 5), with cycle protection.
- `GET /api/v1/world/cause-effect` — all recorded cause-and-effect chains.
- `GET /api/v1/world/events` — all recorded world events with relevance to IAM.
- `POST /api/v1/world/project` — deterministic scenario projection: starting from
  a trigger entity/description, project downstream effects along cause-effect
  chains, multiplying confidence at each hop and ranking outcomes by projected
  confidence. Read-only: no state is mutated.

Tests: `backend/tests/test_worldmodel.py` (7 passed). Target-hardware evidence,
live model serving and real research-platform drivers remain externally bound
work.

### MCP connection — configured, awaiting sign-in

Global OpenCode config was migrated to V2 `mcp.servers` and now includes `colab` (`https://colaboratory.googleapis.com/mcp`) and `kaggle` (`https://kaggle.com/mcp`), preserving `cloudflare`. The `colab` server is live and exposes 10 tools; read-only calls currently return `Unauthorized` until the user completes `/mcps` → colab → Google sign-in. Kaggle is configured but its tools are not yet exposed here.

Mapping and safety rules are documented in `research/mcp/README.md`. Once signed in, the next step is a `ColabMCPDriver` over `tools.colab.*` and a cell-by-cell vLLM serving run from `research/colab/IAM_vLLM_Qwen_Coder_3B.ipynb`. No runtime has been created and no paid tier has been enabled.
