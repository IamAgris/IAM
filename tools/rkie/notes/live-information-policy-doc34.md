# Live Information & Web Intelligence (proposed Doc 34)

**Based on:** working tree 27 November 2026. Re-verify against current files before reuse.

## Finding

A proposal to add a "Web Intelligence & Live Information Retrieval System" is
**mostly already frozen**: Doc 29 / OD-49 (`IAM_BROWSER_INTELLIGENCE_MASTER_SPEC.md`)
covers BIWOS, Web Research Engine, Browser Security Gateway, Web Knowledge
Integration, provider-independent search, deep browsing, verification, security,
autonomous/monitoring research and local-first operation (20/20 checklist §13).
Doc 14 (OD-30), Doc 11 (OD-27) and Doc 31 (OD-51) cover the rest. Runtime code:
`backend/app/services/search_service.py`, `research_service.py`,
`browser_service.py`, `web_knowledge_service.py`. Do **not** add a second stack.

## Genuine gaps addressed

1. No always-on live-information policy in primary system instructions.
2. No automatic search-trigger classification / source-first rule.
3. No search-provider management layer (OD-51 is model providers only).
4. No research cache with freshness TTL or source-reputation records.
5. No single citation / uncertainty / conflict output contract.
6. Acceptance cases for cache reuse, stale results and conflicting reports absent.

## Files added / changed

- `IAM_LIVE_INFORMATION_AND_WEB_INTELLIGENCE_SPEC.md` — proposed Doc 34, OD-54 not recorded.
- `backend/app/services/live_information_policy.py` — policy text, deterministic
  `SearchTriggerClassifier`, `LiveEvidence`, `collect_live_evidence` (free providers only).
- `backend/app/api/routes/models.py` — `_prepare_messages` injects policy always and
  evidence on trigger.
- `backend/app/core/config.py` — `iam_live_info_*` settings. Browser stays off by
  default; `iam_live_info_escalate_to_browser=true` enables conditional escalation.
- `backend/tests/test_live_information_policy.py` — 18 tests + 5 subtests, including
  the eight mandatory pre-OD-54 retrieval validation cases.

## Conditional escalation (owner adjustment, 27 Nov 2026)

`iam_live_info_use_browser=false` stays. On a triggered live request only, if the
configured provider gives no suitable evidence (Wikipedia fallback, empty result,
or no named-publisher domain), the engine escalates: **official publisher website
first** (actual article links + dates), then `site:` browser search, then general
credible sources. Wikipedia is never silently presented as current news. Browser
failures yield an explicit limitation, never fabricated citations.

Live validation 27 Nov 2026: `IAM_LIVE_E2E=1 python
tests/e2e_live_information_smoke.py` required installing the Playwright Chromium
binary (`python -m playwright install chromium`; package alone was insufficient).
DuckDuckGo HTML through Playwright is bot-blocked in this environment, but direct
official-site fetch works. E-1: 3 real SABC articles with URLs and dates,
Wikipedia rejected. E-2: `example.org` unavailable → real no-key HTTP DDG adapter
(`provider="duckduckgo"` in `search_service.py`) returned CNN, UN News and
Gigazine. No fabricated citations. Opt-in smoke only — not a guarantee of future
site availability.

Also implemented: query-level cache (`live_evidence_cache`, migration 058) with
class TTLs 15/60/360/43200 min; reputation and claim records written to existing
`iics_sources`/`iics_claims`; shared engine API `/api/v1/live-information/*`;
provider registry with health/quota/free-first failover plus SearXNG and Tavily
adapters; claim labels, confidence, cross-domain corroboration, conservative
contradiction detection and prompt-injection redaction (`live_evidence_analysis.py`);
explicit public-host SSRF guard; behavioural DEEP follow-up stage; bounded
autonomous monitoring (`live_research_tasks`, migration 063, max 50 tasks,
15-10080 min); Docker build now fails if Playwright browsers cannot install.
`.env.example` flags added. OD-54 signoff sheet: `IAM_OD54_SIGNOFF_SHEET.md`
with E-1/E-2/E-3 real-web evidence.

Also added: isolated Tesseract OCR via `live_media_service.py` (Docker container,
no host binary), transcription delegation to `voice_service` with explicit
fail-closed, user-supplied image/audio URL handling, and `scripts/creator_request_od54.py`.
OD-54 pending request was created against the running API:
`cr_880d5f1f49ae2fdcc34f312d97f3cf97`, challenge
`d3915d76d72ef20cb2891184a05f8da805c3b7cd06eaed6dc125403300b620d0`.
E-8 OCR, E-9 self-hosted SearXNG JSON adapter, E-10 transcription fail-closed.

Verification: 1013 tests passed; ruff/mypy clean on changed files; mypy ratchet
OK (baseline refreshed for concurrent Web3/blockchain work); migration and
OpenAPI checks OK. Remaining: Creator signature, Tavily key, STT provider.

## Decisions / constraints

- OD-46 shared primary is **Qwen2.5-3B** (`local-qwen-3b`, owner reopened 27 Nov 2026); Coder 3B is an optional secondary.
- Paid search stays fail-closed (OD-04/OD-25, `SEARCH_ACTION`).
- `ARCHITECTURE_INDEX.md` and `IAM_OWNER_DECISIONS.md` intentionally untouched —
  owner must record OD-54 before Doc 34 enters the frozen baseline.

## Verification

`python -m pytest backend/tests -q --cov=app --cov-fail-under=60` — 776 passed, 67.29%.
`python -m ruff check` on changed files — clean.
`python tools/quality/check_mypy_ratchet.py` — no new errors.
