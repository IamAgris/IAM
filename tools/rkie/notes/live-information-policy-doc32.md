# Live Information & Web Intelligence (proposed Doc 32)

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

- `IAM_LIVE_INFORMATION_AND_WEB_INTELLIGENCE_SPEC.md` — proposed Doc 32, OD-52 not recorded.
- `backend/app/services/live_information_policy.py` — policy text, deterministic
  `SearchTriggerClassifier`, `LiveEvidence`, `collect_live_evidence` (free providers only).
- `backend/app/api/routes/models.py` — `_prepare_messages` injects policy always and
  evidence on trigger.
- `backend/app/core/config.py` — `iam_live_info_*` settings. Browser stays off by
  default; `iam_live_info_escalate_to_browser=true` enables conditional escalation.
- `backend/tests/test_live_information_policy.py` — 18 tests + 5 subtests, including
  the eight mandatory pre-OD-52 retrieval validation cases.

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
official-site fetch works. Result: 3 real SABC articles with URLs and dates,
Wikipedia rejected, no fabricated citations. Opt-in smoke only — not a guarantee
of future site availability.

## Decisions / constraints

- OD-46 shared primary is **Qwen2.5-Coder 3B**; "Qwen2.5:3B" in proposals is informal.
- Paid search stays fail-closed (OD-04/OD-25, `SEARCH_ACTION`).
- `ARCHITECTURE_INDEX.md` and `IAM_OWNER_DECISIONS.md` intentionally untouched —
  owner must record OD-52 before Doc 32 enters the frozen baseline.

## Verification

`python -m pytest backend/tests -q --cov=app --cov-fail-under=60` — 776 passed, 67.29%.
`python -m ruff check` on changed files — clean.
`python tools/quality/check_mypy_ratchet.py` — no new errors.
