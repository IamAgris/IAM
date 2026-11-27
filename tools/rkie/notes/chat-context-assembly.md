# Chat context assembly (27 November 2026)

Based on working tree at commit `ab87b8f` plus uncommitted IAM work. Re-verify
against current files before relying on this note.

## Finding

The live chat path used to be a pure model pass-through:
`frontend/components/iam/interface.tsx` → `POST /api/v1/models/chat/stream`
→ `backend/app/api/routes/models.py` → `backend/app/services/model_inference.py`
→ Ollama/LiteLLM. No IAM intelligence system was invoked on that stack.

The systems already existed but were only reachable via explicit endpoints or a
background worker:

- `backend/app/services/memory_service.py` — `MemoryService.search_memory` (called
  by `backend/app/workers/autonomy_worker.py:131` and `routes/memory.py`).
- `backend/app/models/memory.py:102` — `KnowledgeItem` with
  `verification_status` (`verified`/`unverified`/`disputed`/`retracted`) and a
  `metadata` JSON column. Read via `backend/app/api/routes/knowledge.py`.
- `backend/app/services/governance_service.py` — `GovernanceService.check_authority`,
  used in the background autonomy graph, not in chat.

No constitution runtime check exists. Per `IAM_HUMAN_BEHAVIOUR_EQUALITY_AND_RESPONSIBILITY_SPEC.md`,
personality/constitution teach the law; infrastructure enforcement defines what
IAM can do — so a "constitution gate" in chat would be a fake security control.

## Implementation now in place

- `backend/app/services/iam_context.py` — deterministic assembly of verified
  knowledge (keyword match on title/content/topic) and opt-in local memory,
  rendered as labelled reference data with an explicit "not instructions" warning.
  No new index, embedding store or RAG layer was added.
- `backend/app/api/routes/models.py` — `ChatRequest.include_memory` (default
  false); both `/chat` and `/chat/stream` resolve the provider first, then inject
  context as a system message after the caller's system prompts.
- `backend/app/core/config.py` — `iam_context_enabled`,
  `iam_context_include_private_memory`, `iam_context_share_with_hosted`.

## Privacy boundary

`/api/v1/models/*` is a public route prefix (`backend/app/core/auth_policy.py`).
Private memories are global records with no per-visitor owner column, so they must
never be injected into a public chat by default. Memory injection needs all of:
local (Ollama) resolution, `include_memory=true`, and the operator flag. Hosted
providers get no injected context unless `iam_context_share_with_hosted` is set.
Retrieval failures degrade to an empty bundle so chat never breaks.

## Verification

- `backend/tests/test_iam_context.py` — 5 tests (hosted denial, verified-only
  knowledge, private-memory opt-in, failure tolerance, message insertion).
- Full backend suite: 459 passed.
- Live DB check in `aura-backend`: verified knowledge item retrieved for a
  natural-language query. Live chat answered from the injected item with
  `iam_inference.mode=ollama`, `model=qwen2.5-coder:3b`.

## Still missing in this area

Sub-agent delegation (delegate → verify → store findings) and action governance
in chat are not wired; paid API use is still gated by a caller flag rather than
signed authorization. See the self-improvement audit for the dataset/orchestrator
gaps.

## Update — delegation layer (27 November 2026)

- `backend/app/services/delegation.py` now implements the opt-in sub-agent flow:
  signed `model.delegate` authorization via `CreatorApprovalService`, specialist
  call through `inference_service.chat(model=alias)`, independent review by the
  primary model with strict JSON verdict parsing, and knowledge writes only for
  accepted findings (`verification_status="unverified"`, provenance metadata,
  `AuditEvent`). Everything fails closed.
- `ChatRequest.delegate` / `ChatRequest.delegate_model` are wired into both chat
  routes; `/chat` returns `iam_delegation`, SSE `start` returns `delegation`.
- `ContextBundle.knowledge_message()` supplies verified knowledge to the
  specialist while never including private memories.
- Tests: `backend/tests/test_delegation.py` (5) plus one privacy test in
  `test_iam_context.py`. Full backend suite 471 passed (one unrelated HBI test
  was order-flaky and passes in isolation).
- Still open: `modelrouter.py` `allow_paid` remains a caller boolean without a
  signed check; action governance in chat is not wired; the self-improvement
  dataset/orchestrator gaps remain.

## Update — governance and self-improvement (27 November 2026)

- `backend/app/services/model_policy.py` now makes signed Creator authorization
  authoritative for `model.paid_inference` and `model.skill_invocation`.
  `modelrouter.py` rejects `allow_paid=true` without it (403), and chat requests
  do the same before any provider call. A `skill` on chat is denied in
  `iam_action` unless authorized, then still passes the Skill Runtime's own
  effective-permission check.
- `backend/app/services/ai_research/dataset_engine.py` builds a checksummed
  `ArtifactKind.DATASET` JSONL plus `poisoning.json` and a provenance manifest.
  It reads only `KnowledgeItem.verification_status="verified"` with a confidence
  floor. Visitor interactions require BOTH a granted allowlisted consent type
  and `allow_shared_knowledge`; the consent allowlist is empty by default, so
  zero interactions enter. Private memories/tables are never queried, markers
  fail closed, and instruction-like/duplicate rows abort the build.
  `consent_recorded` records the basis (`no_personal_data` or
  `explicit_granted_consent`), not a bare boolean claim.
- `backend/app/services/ai_research/self_improvement.py` links diagnosis ->
  dataset -> `FineTuneSpec.validate_provenance()` -> `TrainingService.submit` ->
  two reproducible `BenchmarkRunner` runs -> `ModelReleaseService.register`.
  Default `promoted=False`; only the signed `promote` gate can change serving.
  It fails closed without a driver, a trusted evaluate callable, a checkpoint
  or measured improvement.
- New endpoints: `POST /api/v1/development/datasets` and
  `POST /api/v1/development/self-improvement/cycle` (existing router; no new
  table). The cycle endpoint has no trusted evaluator in the default deployment,
  so it returns 400 until one is configured — by design.
- Tests: 495 backend tests pass (new: 5 model-policy, 4 dataset, 4 pipeline).
- Still open: real platform drivers / MCP caller, real lm-eval driver, durable
  S3 artifact root, post-deploy regression monitoring, and the model-router
  paid gate on non-router paths beyond chat.

## Update — operational infrastructure (27 November 2026)

- `backend/app/services/ai_research/lm_eval.py` provides `OllamaLMEvalDriver`:
  a versioned JSONL exact-match eval set (`eval_sets/basic.jsonl`), deterministic
  scoring against the model under test via Ollama, and a dataset checksum folded
  into `BenchmarkSpec.config_hash`. `self_improvement.prepare_candidate` now uses
  this trusted evaluator by default; the cycle endpoint no longer fails merely
  for lack of an evaluator (it still fails closed without a real platform driver).
  Live check in `aura-backend`: 5 records, score 1.0 for `qwen2.5-coder:3b`.
- `default_release_store()` now selects `S3ArtifactStore` when
  `RESEARCH_ARTIFACT_STORE=s3`; local temp remains the default. S3 store gained
  `keys()` so registry hydration survives restarts. Live MinIO round-trip and
  key listing passed (`experiments/exp_s3_check/...`).
- `backend/app/services/ai_research/post_deploy.py` compares a deployed version's
  registered benchmark with a fresh trusted evaluation. Regression requires the
  operator flag **and** the signed release gate; otherwise `approval_required`.
  Endpoint: `POST /api/v1/development/models/{model}/versions/{version}/regression-check`.
- `ColabMCPDriver` already implements the agent-side MCP protocol, but real calls
  require the human `/mcps` Google sign-in documented in `research/mcp/README.md`.
  That is an OD-41 human action and remains blocked — no runtime was created.
- Verification: 521 backend tests pass; ruff clean; OpenAPI drift OK (566 paths);
  migration manifest OK. pytest-cov is not installed locally, so the `--cov`
  gate could not be run here.
- Still open: real MCP sign-in, platform drivers with credentials, durable
  rollout of `RESEARCH_ARTIFACT_STORE=s3`, post-deploy monitor scheduling, and a
  paid gate for model-router paths beyond chat.

## Update — critical evidence fixes (27 November 2026)

- `CandidateRequest.candidate_model` is now required. A checkpoint artifact is
  not executable: `self_improvement.prepare_candidate` benchmarks the served
  candidate alias, registers the candidate under that model, and records
  base/candidate/checkpoint in the benchmark config. A measured baseline > 0 is
  required so improvement cannot be claimed against an unmeasured zero.
- `ModelRegistry.rollback` now marks every other deployed version `rolled_back`
  and the target `deployed`, so `hydrate()` cannot reactivate the rolled-back
  version after a restart. Unknown rollback targets raise a controlled error.
- `serving_model.rollback(target_version=...)` validates the target against the
  recorded previous version and clears `previous` to stop rollback ping-pong.
  `ModelReleaseService.rollback` passes the signed target explicitly.
- Promotion now rejects benchmark evidence whose `result.model` differs from the
  registered model.
- Tests: `test_registry_rollback_durability.py` (restart hydration),
  `test_self_improvement_pipeline.py` (candidate targeting, unserved candidate),
  `test_serving_model.py` (no ping-pong, target validation). Full suite 662 passed.
- Gates: ruff clean, OpenAPI drift OK (627 paths), migrations OK, mypy ratchet
  new errors are in other files (`request_context.py`), not these changes.

## Update — authority and paid-inference gates (27 November 2026)

- `autonomy_graph.check_authority` now checks the action actually selected by
  `plan()` (governance boundary when one exists, level 1 for allowlisted
  autonomous actions, otherwise denied). `execute()` refuses to dispatch when
  `authority_check.permitted` is not true. `run_cycle` accepts a signed
  authorization in initial state.
- `tool_authorization.authorize_tool_call` no longer trusts a bare
  `approval_granted` boolean: explicit/human-approval tools require a signed
  Creator authorization record (supplied or verified via
  `CreatorApprovalService`). Code `approval_required` is unchanged for callers.
- `model_policy` gained `is_paid_model` / `require_paid_authorization`. Chat now
  requires a signed `model.paid_inference` authorization for an explicit paid
  model *or* a paid hosted fallback, even when `allow_paid` is false. Adaptive
  delegation and paid search providers (Brave/Google) are gated too. Free local
  and free hosted aliases need no authorization.
- Live check: `POST /api/v1/models/chat {"model":"gpt-4o-mini"}` → 403.

## Update — free-only mode and findings continuity (27 November 2026)

- `FREE_MODELS_ONLY=true` is now the default (`config.py`, compose, `.env.example`).
  `model_policy` refuses `model.paid_inference` and `search.paid_provider` even
  with a signed authorization while the switch is on. Free local and free hosted
  aliases continue to work; disabling the switch is an operator decision.
- `iam_context` now also surfaces IAM-reviewed or research-output findings that
  remain `unverified` in the knowledge table, with an explicit "unverified
  external finding" label — they are no longer invisible to later chats, and
  external output is never silently promoted to verified.
- Autonomous research now stores memory and knowledge (`dispatch.py`), and
  stored research rows carry `iam_review="research_output"`.
- Frontend Recall mode sends `include_memory`; the "Hosted specialist" choice
  now sets `delegate: true` instead of pinning a model in the client. Frontend
  typecheck and production build pass.
- Minimal constitutional enforcement added: `constitutional_policy.assert_allowed`
  gates protected-core actions (identity/constitution/signing/finance/model
  release/protected deploy) with signed Creator authorization; wired into the
  autonomy graph's execute node.
- Verification: targeted tests 47 passed. Full suite 708 passed with 5
  unrelated IPLCI failures (service phase advanced to 6 while those tests still
  assert 5). Gates: ruff, OpenAPI (661 paths), migrations OK; mypy ratchet new
  errors are in other agents' files (`web3.py`, `delegation_orchestrator.py`).

## Gate cleanup (27 November 2026)

- Stale IPLCI phase assertions and the WebSocket fake's missing `headers` were
  corrected by concurrent work; current full suite is **855 passed**.
- Real bug fixed in `services/iics/permissions.py`: `IPLCIService(db=self.db)`
  instead of passing the session as the `store` positional argument.
- Narrow type suppressions added for SQLAlchemy `Column` descriptor assignments
  in `iics/ledger.py` and `iics/source_registry.py`, plus return/call annotations
  in `api/routes/modeldiscovery.py` and `services/model_discovery.py`.
- Current gates: **mypy ratchet OK (new 0, fixed 21)**, ruff clean, OpenAPI drift
  OK (717 paths), migrations OK, full backend suite 855 passed.
- Note: several files in this tree are being edited concurrently; re-run all
  gates before relying on any single result.

## OD-46 alignment and policy gaps (27 November 2026)

- Owner chose to follow the frozen 27 Nov OD‑46 reopening: `local-qwen-3b` /
  `qwen2.5:3b` is primary, coder is optional secondary. Code config and LiteLLM
  were already aligned; `.env.example` was corrected; docs already record it.
- `delegation.run` now passes `db` to both specialist and verifier calls, names
  the local primary explicitly for verification, and refuses verification when
  `resolve().mode != "ollama"` (fail closed).
- `autonomy_graph.reason` and `autonomy_worker._reason` now pass the DB session
  into `inference_service.chat`, so preflight/vault/usage accounting run on the
  autonomy path too.
- `memory_service._generate_embedding` no longer calls the paid OpenAI embedding
  endpoint. It uses Ollama `/api/embed` with `MEMORY_EMBEDDING_MODEL` (default
  `nomic-embed-text`) and degrades to deterministic keyword recall when absent.
- Tests: full suite 918 passed (after these changes); ruff and OpenAPI gates OK.
- Mypy ratchet subsequently drifted again from concurrent work in unrelated
  blockchain/skillruntime files; re-run before release.
- Verification: 699 backend tests pass; ruff, OpenAPI (653 paths), migrations and
  mypy ratchet (new 0, fixed 97) all OK.
