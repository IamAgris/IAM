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
