# IAM — Cross-Cutting Implementation Technology Addendum

**Version:** 1.0 · 25 November 2026  
**Status:** CONFIRMED — cross-cutting implementation direction  
**Decision register:** This addendum is **not** a new owner decision. It does not create OD-42 and does not reopen or modify OD-01…OD-41.  
**Source of truth:** `ARCHITECTURE_INDEX.md`, `IAM_FINAL_CONSOLIDATION.md`, `IAM_OWNER_DECISIONS.md`, `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` §5

---

## 1. Purpose

IAM is a **hybrid Python + Rust + TypeScript system**. Python remains the language of AI research, model development and the existing FastAPI service layer; Rust is adopted for performance-sensitive, security-sensitive and concurrent infrastructure components; TypeScript remains the web and SDK client language.

This addendum records *how components are implemented*. It does not change *what IAM does*, its systems, its authority boundaries or any locked decision.

---

## 2. Timing and scope — important

- The base build is still at the "pre-implementation complete, ready for Phase 0/1 build" point recorded in `README.md`; the hybrid strategy is adopted **before that build**, so no base component has to be rewritten.
- The OD-41 research programme is a separate sequence: `IAM_AI_RESEARCH_IMPLEMENTATION_PLAN.md` §7 records research Phase 0–2 as **COMPLETE in Python** (17 + 8 + 6 tests passing). Those deliverables stay in Python. Rust applies **prospectively** to Phases 3–5, to new infrastructure work and to the base Phase 0/1 build.
- **No working component is rewritten in Rust simply because Rust is available.** Replacement requires the measured-benefit gate in §6.

---

## 3. Language allocation

| Area | Language | Rationale |
|------|----------|-----------|
| Core runtime and system services | Rust | Memory safety without GC; predictable resource use |
| Resource and workload scheduler | Rust | Concurrent scheduling, low jitter, bounded memory (OD-39) |
| Distributed node communication | Rust | Efficient, predictable distributed execution |
| P2P networking | Rust | Concurrency and security-sensitive transport |
| Security and isolation components | Rust | Strong boundary enforcement, no-core-access isolation |
| Storage and file-processing engines | Rust | High-throughput I/O, bounded memory on low-resource nodes |
| High-performance inference integration | Rust where beneficial | Transport/serving glue only; never the model itself |
| Python ML training and fine-tuning | Python | PEFT/TRL/Unsloth ecosystem (OD-40) |
| FastAPI backend | Python initially | Locked in `canonical/IAM_DOC_01` §5; remains the interface layer |
| AI research and experimentation | Python | Research ecosystem, reproducibility, speed of iteration |
| Web interface | TypeScript | Locked in `canonical/IAM_DOC_01` §5 (Next.js) |
| SDK | Python and TypeScript | Existing `sdk/` protocol and clients remain canonical |

**Rule:** research and model logic stay in Python; system infrastructure may be Rust. Both communicate through versioned, language-neutral contracts (§5).

---

## 4. Compatibility with locked decisions

| Constraint | Source | Effect of this addendum |
|------------|--------|-------------------------|
| Web interface = Next.js + TypeScript | `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` §5 | Unchanged |
| Backend = Python + FastAPI | `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` §5 | Unchanged; Rust components sit behind the API |
| Queue runtime = ARQ (async Redis) | OD-08; `IAM_INFRASTRUCTURE_TRAFFIC_AND_DISTRIBUTED_PROCESSING_SPEC.md` §5 | Unchanged. Rust must not introduce a replacement queue runtime; it may produce/consume ARQ-compatible jobs |
| Agent orchestration = LangGraph; model gateway = LiteLLM | `canonical/IAM_DOC_01` §5 | Unchanged |
| Foundation model, MEFE, resource manager requirements | OD-38 / OD-39 / OD-40 | Unchanged; none names an implementation language |
| Distributed research requirements frozen | OD-41 | Unchanged; no new subsystem is created |
| Identity, signing, financial authority, protected core | OD-01 / OD-03 / OD-04 / OD-25 / OD-11 | Unchanged. Rust components are subject to the same Creator-approval and signed-approval gates |
| Free-first, no paid upgrade without approval | OD-04 / OD-25 / OD-41 | Unchanged; Rust tooling and CI must use free tiers only |

Because the register is frozen at 53 decisions, any future change to a locked decision still requires explicit owner reopening under `IAM_OWNER_DECISIONS.md` "Change control (frozen)".

---

## 5. Python–Rust interoperability contract

1. **Schema first.** All messages between layers are defined in language-neutral, versioned schemas derived from `sdk/PROTOCOL.md` and the job/artifact contracts in `backend/app/services/ai_research/`. No Python or Rust-specific types cross the boundary.
2. **Defined boundaries only:** HTTP/OpenAPI endpoints (FastAPI ↔ Rust services), the existing ARQ/Redis queue for jobs, and FFI bindings where in-process calls are required. No direct access to another layer's private state or database tables.
3. **Fail closed.** Every Rust component inherits the existing safety policy: integrity digests, isolation (no core access, no default network), private-data markers and secret redaction equivalent to `backend/app/services/ai_research/security.py`.
4. **Identity and authority flow through the existing services.** Rust components never hold signing material or approve protected-core changes; those remain with the Python services and external signer (OD-03).
5. **One implementation per responsibility.** A capability is implemented once, in one language, and exposed through its contract — never duplicated in both languages to "keep options open".

---

## 6. Adoption rule (measurable benefit)

Rust is adopted where it provides **measured** benefit, not because it is faster or newer.

For every candidate component:

1. Record the incumbent Python implementation and its baseline (latency, throughput, peak RSS/VRAM, correctness) on declared hardware.
2. Implement the Rust candidate behind the **same contract** and run the **same acceptance tests**.
3. Adopt only if the Rust candidate meets a declared target and passes every incumbent acceptance test. Otherwise retain Python and keep the benchmark evidence.
4. A change to any locked component (§4) still requires the owner to reopen the decision; this addendum never grants that authority.
5. Toolchain and cross-platform support (x86-64 and ARM64 per OD-22, plus the developer's Windows host) must be demonstrated before adoption.

---

## 7. Actions before the base Phase 0/1 build

| # | Action | Evidence |
|---|--------|----------|
| 1 | Establish a Rust workspace and coding standards | `Cargo.toml` workspace, pinned toolchain, `rustfmt`/`clippy -D warnings`, `cargo audit`, documented conventions |
| 2 | Define Python–Rust interoperability | Versioned schemas, boundary contract tests, FFI/queue/API smoke tests (§5) |
| 3 | Classify existing and planned components | Allocation table in §3 plus per-work-package classification in `IAM_AI_RESEARCH_IMPLEMENTATION_PLAN.md` §2a |
| 4 | Benchmark before replacing any working component | Baseline + candidate measurement recorded per the §6 gate (acceptance A19) |
| 5 | Add Rust requirements to work packages and acceptance tests | `IAM_AI_RESEARCH_IMPLEMENTATION_PLAN.md` §2a and acceptance tests A17–A20 |

---

## 8. Relationship to other documents

- `IAM_OWNER_DECISIONS.md` — frozen at 53 decisions; this addendum changes none of them.
- `IAM_AI_RESEARCH_IMPLEMENTATION_PLAN.md` — work-package classification and acceptance tests A17–A20.
- `IAM_RESOURCE_AND_WORKLOAD_MANAGER_SPEC.md` (OD-39) and `IAM_INFRASTRUCTURE_TRAFFIC_AND_DISTRIBUTED_PROCESSING_SPEC.md` (OD-37) — Rust candidates for scheduler and distributed transport, subject to §6.
- `sdk/PROTOCOL.md` — canonical language-neutral protocol.
- `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` §5 — initial technology architecture, unchanged by this addendum.
