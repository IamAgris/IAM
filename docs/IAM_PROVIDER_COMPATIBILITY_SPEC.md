# IAM — Universal Provider Compatibility Layer (engineering requirement)

**Version:** 1.0 · 28 November 2026
**Status:** Owner-directed engineering requirement. Derived implementation
specification; **not** a new owner decision, not a new top-level system, not a
dependency on any development tool.
**Authority parent:** `ARCHITECTURE_INDEX.md` → OD-38/OD-46/OD-52,
`IAM_UNIVERSAL_MODEL_PROVIDER_ORCHESTRATION_SPEC.md` (Doc 32),
`IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md`.

---

## 1. Principle

IAM's local-first identity, memory, orchestration and authority are independent
of any model provider. A hosted model is a secondary intelligence resource and
must never receive its own privileged execution path.

Provider compatibility is a **subsystem**, not an API endpoint. IAM studies the
engineering pattern used by external tools but implements it independently: no
installation of, dependency on, or routing through any development agent.

One canonical tool ecosystem. One governance boundary. Per-model communication
compatibility.

## 2. Components

| # | IAM component | Responsibility | Implementation |
|---|---------------|----------------|----------------|
| 1 | Universal provider interface | Common local/hosted connection contract | `providers/base.py`, `model_inference.py` |
| 2 | Provider adapters | Auth, model IDs, request formatting, response normalisation | `providers/nvidia.py`, `providers/models_dev.py`, `infra/litellm/config.yaml` |
| 3 | Model capability registry | Per-model tool/reasoning/streaming/modality facts | `DiscoveredModel` fields; `provider_compat/profiles.py` |
| 4 | Request compatibility engine | Schema translation, parameter filtering, naming, reasoning fields | `provider_compat/request.py` |
| 5 | Universal tool parser | Streaming and non-streaming function-call assembly and validation | `provider_compat/tool_calls.py` |
| 6 | Universal tool orchestrator | Discovery, authorisation, execution, result handling | `iam_tool_manifest.py`, `iam_tool_executor.py`, `tool_authorization.py` |
| 7 | Conversation continuation | Preserve tool-call IDs, assistant message and reasoning across turns | `model_inference.py` (chat + stream loops) |
| 8 | Provider diagnostics | Compatibility tests, recorded failures, regression traces | `provider_compat/diagnostics.py` → `audit_events` |

## 3. Required behaviour

### 3.1 Capability detection
- Never assume two models from one provider share capabilities.
- Static profiles describe known protocol behaviour; live catalogue fields
  (`tool_calling`, `reasoning`, `restrictions`) override defaults when tested.
- A profile describes communication only. It never grants authority.

### 3.2 Request compatibility
- IAM owns one canonical tool definition (`iam_tool_manifest.py`).
- Each model profile selects the wire form: dotted names for Ollama,
  provider-safe names for OpenAI-compatible gateways.
- Unsupported parameters are removed **only when explicitly recorded** for that
  model (e.g. `prompt_cache_key`). No blind post-error parameter stripping.
- Token-limit field names and reasoning fields are profile-controlled.
- Provider tool-call IDs are normalised to strings and the original ID is sent
  back on the tool-result message.

### 3.3 Tool execution
- The provider never executes tools. All calls go through `ToolRegistry`,
  `authorize_tool_call` and `iam_tool_executor`, regardless of model.
- Tool arguments are untrusted data; canonical schemas validate required fields
  and types before execution.
- Consequential and approval-bearing actions remain on their governed routes.

### 3.4 Streaming
- Deltas are accumulated until the name and arguments are complete and parse.
- Multiple simultaneous calls are assembled independently.
- Incomplete or malformed calls are never executed.
- Tool-loop rounds are bounded; timeouts and cancellation are enforced.

### 3.5 Failure handling
- A rejected tool schema is recorded as `provider.compatibility` audit evidence.
- If a provider forces a tools-free retry, `compatibility.tools_fallback` is
  reported explicitly. A tools-free response must never be reported as a
  successful tool execution.

## 4. Implementation status (28 November 2026)

| Requirement | Status |
|---|---|
| Profiles + live catalogue override | Implemented |
| Schema translation + required fields | Implemented |
| Unsupported-parameter filtering | Implemented (declared rules only) |
| Tool-call ID normalisation / preservation | Implemented |
| Reasoning-field preservation (chat + stream) | Implemented |
| Non-streaming tool-call parsing | Implemented |
| Streaming delta assembly | Implemented (unit-tested) |
| Multiple / duplicate / incomplete call handling | Implemented (unit-tested) |
| Tool-result conversation continuation | Implemented |
| Shared `authorize_tool_call` for all models | Implemented |
| Explicit tools-fallback reporting | Implemented |
| Compatibility diagnostics to audit | Implemented |
| Parallel tool calls | Bounded `asyncio.gather` when `profile.parallel_tool_calls` is true; results re-paired to original tool-call IDs in order. **Live proof: 2 calls in one streamed turn, both executed, distinct IDs.** |
| Forced tool selection | `force_tool` on `chat()`/`stream()`, translated through the profile and profile-gated (`supports_forced_tools`); used for live stream proof. |
| Automatic compatibility probe suite | Implemented: `provider_compat/probes.py`, admin-only `POST /api/v1/provider-compat/probe` with bounded retries; results persisted to `DiscoveredModel.test_result` and `audit_events`. **Clean live pass 5/5** for `nvidia-nemotron-3.5-lightning`. |
| Four-tool live matrix (Qwen + NVIDIA) | Script `tests/provider_compatibility_acceptance.py`. Final run **8/8 PASS** — all four tools on both providers, with capacity-aware preflight and bounded retries. Two transient NVIDIA retries were reported, not hidden. |

## 5. Live evidence (28 November 2026)

- Qwen `qwen2.5:3b`: `name_style=dotted`,
  `tools_executed=[{"name":"tone.analyze","error":null}]`.
- NVIDIA `nvidia-nemotron-3.5-lightning`: `name_style=safe`,
  `tools_executed=[{"name":"tone_analyze","error":null}]`.
- Both traces show `tool_registry` / `tool_permissions` queries before execution.
- `tests/provider_compatibility_acceptance.py` runs the same tools against both
  providers and compares `name_style`, executed names, errors and fallback state.
  Final full matrix: **8/8 PASS** (four tools × two providers). An earlier run
  had Qwen `network.inspect` timeout and `finance.research.read` IRWM 503
  (`model exceeds the hard ceiling or core-service RAM reserve`). Those were
  resource conditions, not compatibility or authorisation failures. The harness
  now waits for `GET /api/v1/irwm/status` capacity and retries boundedly rather
  than bypassing OD-39; two NVIDIA retries in the final run were reported.
- Clean full probe run (`POST /api/v1/provider-compat/probe` with 2 retries,
  60s backoff): **5/5 accepted** — `basic_inference`, `tool_schema`,
  `forced_tool`, `streaming_tool`, `parallel_tool_calls` (`observed_calls=2`).
- Live streaming: NVIDIA streamed a forced `tone_analyze` call; IAM emitted
  `tool_executed {"tools":[{"name":"tone_analyze","executed":true}],"count":1}`
  with the authorization queries in the SQL trace. A second streamed turn
  emitted two tool calls; IAM emitted `tool_executed ... count=2` with distinct
  `tool_call_id` values and both `executed:true`.
- Root cause of the first NVIDIA failure was recorded: OpenAI-compatible
  gateways reject dots in function names; IAM now translates wire names through
  the profile-driven request builder rather than a one-off rename.

## 6. Acceptance checklist (production readiness)

- [x] Provider authentication and OpenAI-compatible adapter
- [x] Model-specific capability profile
- [x] Model-specific JSON schema translation
- [x] Unsupported parameter filtering
- [x] Tool-call ID normalisation
- [x] Reasoning field preservation
- [x] Non-streaming tool-call parsing
- [x] Streaming tool-call assembly proven live (`tool_executed` SSE event)
- [x] Multiple simultaneous tool calls proven live (2 calls, distinct IDs)
- [x] Tool-result conversation continuation
- [x] Shared `authorize_tool_call` enforcement
- [x] Inactive/unauthorised tool rejection
- [x] Timeout and bounded retry controls
- [x] No-tools fallback explicitly reported
- [x] Four core tools individually tested live on both providers (8/8)
- [x] Provider regression tests in CI (`quality-gates.yml` job
      `provider-compatibility`, plus `continuous-assurance.yml` deterministic gates)

This document is a repository-accurate description of implemented behaviour and
open gaps. It does not amend any owner decision or freeze a new system.
