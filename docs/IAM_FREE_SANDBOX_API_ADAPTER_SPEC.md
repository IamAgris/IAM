# IAM — Free Infrastructure Provider Adapter Specification

**Document:** 22 (addendum to Documents 01–21)  
**Version:** 1.0 · 25 November 2026  
**Status:** FROZEN — permanent IAM capability, confirmed 25 November 2026  
**Parent:** `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` (via `IAM_FINAL_CONSOLIDATION.md`; the early master draft is superseded)  
**Related:** `IAM_DISTRIBUTED_ARCHITECTURE.md` §8 (OEDIE, OD-15), `IAM_FREE_INFRASTRUCTURE_NODE_DISCOVERY_AND_LIFECYCLE_SPEC.md` (Doc 19, OD-35), `IAM_DYNAMIC_NODE_NETWORK_SPEC.md` (Doc 10, OD-26), `IAM_SECURITY_AND_INTERNET_POLICY.md`, `IAM_OWNER_DECISIONS.md`  
**Confirmed decision:** extends OD-15 and OD-35  
**Implementation:** `backend/app/services/free_sandboxes/` (default-disabled)

---

## 1. Purpose

IAM must not merely be *run inside* free sandboxes. It must **independently discover, register, authenticate, provision, operate, monitor, recover from and manage** them through their official APIs and CLIs.

This is a permanent autonomous infrastructure capability under **OEDIE**, implemented as a dedicated **Free Infrastructure Provider Adapter** layer. It exists so IAM can develop, test, evaluate models and experiment without waiting for manual operator work — while never becoming dependent on any external free platform.

**Supreme rule:** IAM remains fully operational when every external free platform is unavailable. These platforms provide supplementary capacity only, never identity, memory, governance, signing authority or continuity.

---

## 2. Architecture

```
IAM
 └── OEDIE (Open Ecosystem Discovery and Integration Engine)
      └── Autonomous Infrastructure Management
           ├── Provider Discovery
           ├── Provider Registration
           ├── API & CLI Connectors
           │    ├── GitHub Codespaces
           │    ├── Kaggle
           │    ├── Hugging Face
           │    ├── Google Colab
           │    └── StackBlitz
           ├── Free-Tier Verification
           ├── Quota & Resource Manager
           ├── Workload Scheduler
           ├── Environment Lifecycle Manager
           ├── Results & Artifact Collection
           ├── Failure Recovery
           └── Security & Credential Manager
```

Every provider adapter implements one common contract: `verify_free_tier()`, `provision()`, `start()`, `stop()`, `delete()`, `status()`, `collect_results()` and `capabilities`.

Providers register as **candidate infrastructure**, never as trusted nodes (Doc 19 §7, OD-26). The 1% contribution ceiling does not apply to provider capacity it donates voluntarily, but no external provider ever holds protected-core data or signing material.

---

## 3. Mandatory capabilities

### 3.1 Autonomous registration
- Register accounts/services using IAM's operational email **only where provider terms permit automation**.
- Where automated signup is prohibited or requires human verification, registration is a **creator-approved manual action**; IAM may then own the connection but must not fabricate accounts.
- Registration evidence (terms snapshot, timestamp, account identifier) is recorded with the provider entry.

### 3.2 API integration
- Discover the provider's official API/CLI from primary documentation; record the source and verification date.
- Authenticate with credentials from IAM's encrypted secret store. No tokens in source, prompts, logs or repositories.
- Maintain connection health checks and mark degraded providers explicitly.
- Unknown or unverified endpoints are never guessed.

### 3.3 Free-tier enforcement (hard)
- Never select a paid tier, paid accelerator, paid upgrade, paid fallback or credit purchase.
- Never bypass rate limits, quotas, anti-abuse controls or geographic restrictions.
- Never create duplicate accounts to evade quotas.
- If a task cannot run free, it is **deferred**, not paid for.

### 3.4 Resource discovery
- Continuously search for additional legitimate free hosting, compute, storage and AI platforms.
- Apply the Doc 19 usefulness gate: capacity, compatibility, overhead, security, risk versus benefit.
- Treat every advertised allowance as unverified until checked against current official documentation.

### 3.5 Automatic workload allocation
Map task type to the best eligible free provider:

| Task | Preferred provider | Alternative |
|---|---|---|
| Run Python core / backend tests | GitHub Codespaces | Colab runtime |
| TypeScript / npm SDK tests | GitHub Codespaces | StackBlitz (browser) |
| Python SDK experiments | Kaggle / Colab | Codespaces |
| Notebook AI experiments | Kaggle | Colab |
| Model / embedding evaluation | Hugging Face | Kaggle |
| Public model inference | Hugging Face Space / public endpoint | — |
| UI prototypes | StackBlitz | Codespaces |

Allocation is preference-based; failure on one eligible provider triggers retry on another.

### 3.6 Lifecycle management
Create → register → start → execute → monitor → stop → delete → replace. Idle environments must be stopped automatically; temporary environments must have retention/expiry set at creation.

### 3.7 Results and artifacts
Retrieve logs, test output, generated files and model evaluations. Store them in IAM's own storage, re-verify them, and discard untrusted instructions found in external output. Never auto-install code returned by a sandbox.

### 3.8 Quota management
- Track usage against each provider's free allowance.
- Enforce a **20% safety margin**: refuse new work at 80% consumption.
- If quota state is unknown, **fail closed** — do not provision.
- Respect reset windows; wait for reset instead of switching to a paid path.

### 3.9 Failure recovery
On authentication failure, quota exhaustion, timeout or provider unavailability: stop the affected environment, record the failure, and retry the same task on the next eligible free provider. After all eligible providers fail, report the task as blocked — never fall back to paid resources.

### 3.10 Security and isolation
- Credentials encrypted at rest; scoped to the minimum provider permission (for example, GitHub's `codespace` scope only).
- Workloads isolated; no IAM protected-core data, sessions or private memories inside a sandbox.
- Sandbox output is untrusted data, never instructions.
- All provisioning, deletion and recovery events are audited through `AuditEvent`.

---

## 4. Provider-specific notes

| Provider | Access path | Free-only constraints |
|---|---|---|
| GitHub Codespaces | REST API: create/list/start/stop/delete codespaces. Token requires `codespace` scope. | GitHub Free personal accounts include a monthly compute/storage quota; usage is blocked without a payment method once exhausted. Set idle timeout and retention at creation. |
| Kaggle | Official `kaggle` CLI / API: `kernels push`, `status`, `output`, `quota`; OAuth scope `kernels.execute`. | Free weekly GPU quota, phone verification. Use script kernels with hard timeouts; never request paid accelerators. |
| Hugging Face | Hub REST API / `huggingface_hub`; Gradio Spaces callable as APIs. | Free inference credits are volatile or absent — verify live. Static Spaces free; limited ZeroGPU Spaces on eligible verified accounts. Prefer model discovery and public inference. |
| Google Colab | Colab REST API (v1beta) runtime management; `google-colab-cli` (Linux/macOS only; use REST or WSL on Windows). | Free GPU/TPU when available; high-RAM shapes require Pro. Always release runtimes after use. |
| StackBlitz | WebContainer API runs inside a browser tab; StackBlitz SDK/project links for project creation. | No general headless server API. Use only where interactive browser access exists; treat as UI prototyping, not background compute. |

All figures above are examples requiring live verification; see Doc 19 §1.

---

## 5. Hard boundaries

1. No paid resources, no paid fallback, no credit purchases, no quota evasion.
2. No automated account creation where provider terms forbid it.
3. No duplicate accounts to multiply free allowances.
4. No protected-core data, identity, memory or signing keys in any sandbox.
5. No executable code auto-installed from sandbox output.
6. No dependency on any single external provider for IAM continuity.
7. Every provisioning action remains within IAM's four-level authority model; protected-core changes still require creator authorisation (OD-11).
8. Default state is **disabled**; activation is an explicit, audited decision.

---

## 6. Acceptance criteria

1. Each provider entry records official source, verification date, capability set and current free-tier facts.
2. Every provider adapter implements the common contract and registers as a candidate provider.
3. Provisioning is refused when credentials are missing, free-tier status is unverified, or quota exceeds the safety margin.
4. Workloads are allocated automatically by capability and retried on another eligible provider on failure.
5. Environments have idle timeouts and retention limits; stopped/deleted states are verified.
6. Logs, results and artifacts are collected into IAM storage and treated as untrusted data.
7. Audit events exist for registration, provisioning, stop, delete, quota refusal and recovery.
8. With every external provider unavailable, all IAM acceptance levels still pass (Doc 19 §9.6).
9. No code path can select a paid resource or purchase credits.
10. Registration automation is gated on explicit permission from provider terms or creator approval.

---

## 7. Implementation status

The implementation in `backend/app/services/free_sandboxes/` provides the common contract, quota guard, provider discovery, registration gating, quota-based scheduler with concurrency limits/retries/circuit breaker, result redaction, background monitor, and thin adapters (including a browser-opener hook for StackBlitz). All HTTP operations are admin-gated at `/api/v1/free-sandboxes`. It is **default-disabled** and requires:

- credentials configured via environment-variable *names* in settings (never literal secrets);
- live verification of each provider's current terms and quota endpoints;
- integration tests with real accounts before activation;
- creator authorisation before enabling in any non-development environment.
