# IAM — OD-54 one-page sign-off sheet

**Version:** 1.0 · 27 November 2026  
**Status:** **PROPOSAL FOR OWNER REVIEW — no decision is made by this sheet.** A chat message, a checked box in a Markdown file and an unsigned request are not authority. OD-54 becomes effective only after `CreatorApprovalService.decide()` verifies an ED25519 signature from the configured Creator signer over a one-time challenge (OD-03/OD-42).  
**Source document:** `IAM_LIVE_INFORMATION_AND_WEB_INTELLIGENCE_SPEC.md` (proposed Document 34).  
**Identifier note:** OD-52 and Document 32 were subsequently assigned to the Universal Model Provider orchestration decision, and OD-53/Document 33 to Financial Intelligence Amendment A; OD-55/Document 35 is the current Web3 proposal. This proposal therefore uses the next free identifiers: **OD-54 / Document 34**. This is a coordination correction, not a change to any locked decision.  
**Evidence rule for this sheet:** **no mock data and no patched provider responses are accepted as evidence.** Only the real-web smoke run recorded in section C is cited. Unit tests that patch search or browser services are regression checks only and are deliberately excluded from this sign-off.

---

## A. Companion decisions — recommended defaults

| Ref | Question | Recommended default | Effect if accepted | Owner response |
|---|---|---|---|---|
| OD-54 | Approve Document 34 as an addendum | **Yes — proposed addendum only** | Adds always-on live-information policy, automatic triggers, conditional escalation, output contract and acceptance gates to Doc 29/OD-49. No new top-level system, identity, memory store or model. | ☐ Accept ☐ Reject ☐ Discuss |
| OD-54-a | Global browser access | **No — remains off** | `iam_live_info_use_browser=false` stays. Browser is used only after a triggered live request has no suitable evidence. | ☐ Accept ☐ Reject ☐ Discuss |
| OD-54-b | Paid search providers | **Fail-closed** | No automatic paid search. Brave/Tavily use requires signed Creator authorisation (`SEARCH_ACTION`) under OD-04/OD-25. | ☐ Accept ☐ Reject ☐ Discuss |
| OD-54-c | Publisher whitelist | **None for public research** | Any public website may be researched. A named publisher is *prioritised*, never exclusive: official site → `site:` search → other credible sources. | ☐ Accept ☐ Reject ☐ Discuss |
| OD-54-d | Cache / freshness / source reputation | **Approve in scope, implement later** | Doc 34 §7 is an implementation requirement using existing Postgres/pgvector; no new vector database and no claim of implementation. | ☐ Accept ☐ Reject ☐ Discuss |
| OD-54-e | Search-engine fallback readiness | **Validated with a real no-key HTTP adapter** | DuckDuckGo HTML through Playwright is bot-blocked on this host, so a no-key HTTP adapter was added to `search_service`. Real fallback to other credible sources is recorded as E-2. | ☐ Accept ☐ Reject ☐ Discuss |

---

## B. Exact proposed decision text for the register

Paste into `IAM_OWNER_DECISIONS.md` only after the signature is verified:

> **OD-54 — Live Information & Web Intelligence policy.**
> Approve Document 34 (`IAM_LIVE_INFORMATION_AND_WEB_INTELLIGENCE_SPEC.md`) as a **proposed addendum** to Documents 11, 14, 23-A, 29 and 31. It establishes an always-on Web Access and Live Information Policy in the primary system instructions; deterministic, model-independent recognition of current-information requests; source-first retrieval with no publisher whitelist; conditional browser escalation (browser off for ordinary conversations, enabled only when a triggered request has no suitable evidence); a citation, uncertainty and conflict output contract; search-provider management that is free-first and fail-closed for paid use; and research cache, freshness and source-reputation requirements. Wikipedia fallback and empty results are never presented as live evidence; browser failure produces an explicit limitation and never fabricated citations. Web content remains untrusted data, never instructions. This is a shared capability of IAM's existing browser and research systems, not a new top-level system, AI identity, memory store, model or general browser enablement. It does not alter the shared primary model (OD-46: Qwen2.5-Coder 3B), Doc 29/OD-49, OD-27, OD-30, OD-38, OD-39, OD-41, OD-51, identity (OD-01), signing (OD-03), financial authority (OD-04/OD-25) or protected core (OD-11). No implementation, security validation or Doc 29 phase completion is claimed by this decision. **A chat message is not authority; confirmation requires a verified ED25519 signature over a one-time challenge.**

---

## C. Real-web evidence relied upon by this sheet

| Ref | Date/time (UTC) | Command | Observed result |
|-----|-----------------|---------|-----------------|
| E-1 | 2026-11-27 04:24:46 | `IAM_LIVE_E2E=1 python tests/e2e_live_information_smoke.py` (from `backend/`) | Real no-key `search_service` returned the Wikipedia fallback; it was rejected as unsuitable. Escalation fired to the real official SABC site. Three actual SABC articles retrieved with URLs and publication dates. Wikipedia URL excluded from evidence. No fabricated citation. Exit 0. |

**E-1 retrieved articles (verbatim titles and dates from the live run):**

1. "Madlanga Commission hears about Naicker's alleged drug operations" — 27 November 2026, 5:43 AM — `https://www.sabcnews.com/sabcnews/commission-hears-about-clive-naickers-alleged-drug-operations/`
2. "Bishop Zondo's rape trial postponed to March next year" — 27 November 2026, 6:07 AM — `https://www.sabcnews.com/sabcnews/bishop-zondos-rape-trial-postponed-to-march-next-year/`
3. "Mbeki says Mlambo-Ngcuka had qualities to be President" — 26 November 2026, 8:05 PM — `https://www.sabcnews.com/sabcnews/mbeki-says-mlambo-ngcuka-had-qualities-to-be-president/`

**Conditions of E-1:**

- The search provider was **not patched**. No API key is configured on this host, so `search_service.search()` genuinely returned `provider: wikipedia` with three Wikipedia results; none were accepted as live evidence.
- The browser stack was real. Playwright's Chromium binary was installed for this run (`python -m playwright install chromium`, v1255); the package alone was insufficient.
- Only two operating flags were overridden for the test: browser-first `false`, conditional escalation `true`. No page content, article, date or URL was injected.
- The smoke is opt-in and time-bounded (`IAM_LIVE_E2E_TIMEOUT`, default 60s). It is evidence of **that run only**, not a guarantee of future site availability.

| E-2 | 2026-11-27 04:44:29 | `IAM_LIVE_E2E_QUERY='Latest news from example.org'` + `IAM_LIVE_E2E=1 python tests/e2e_live_information_smoke.py` | Named publisher `example.org` yielded no article links; browser `site:` search returned zero results; the real no-key HTTP adapter retrieved three other sources (CNN, UN News, Gigazine). Provider `duckduckgo-http`; Wikipedia excluded; exit 0. |

**E-2 retrieved sources (verbatim from the live run):** "Breaking News, Latest News and Videos | CNN" (`https://www.cnn.com/`); "Latest News | 1 UN News" (`https://news.un.org/en/news`); "example.com, famous for being 'almost completely empty,' has undergone ..." (`https://gigazine.net/gsc_news/en/20261007-example-com`). E-2 used the same real provider and real browser; only the query and the two operating flags differed.

| E-3 | 2026-11-27 11:04:08 | `IAM_LIVE_E2E_QUERY='What is the latest AI model release?'` + `IAM_LIVE_E2E=1 python tests/e2e_live_information_smoke.py` | Real no-key Wikipedia fallback rejected on a query with **no named publisher**; real HTTP adapter returned three current AI-release sources. Every result carries a claim label, confidence and corroboration count. Exit 0. |

**E-3 retrieved sources (verbatim):** "AI Release Tracker — AI Model Release Timeline" (`https://aireleasetracker.com/`); "AI Updates Today (November 2026) - Latest AI Model Releases" (`https://llm-stats.com/llm-updates`); "New AI model releases" (`https://artificialwatch.com/releases`).

| E-4 | 2026-11-27 11:47:33 | `IAM_LIVE_E2E_QUERY='search the web for https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf'` + smoke | User-supplied public PDF fetched and parsed locally (`document-extraction`, `kind: pdf`), text "Dummy PDF file". Exit 0. |
| E-5 | 2026-11-27 11:49:01 | `IAM_LIVE_E2E_QUERY='SABC nuus vandag'` + smoke | Non-English current-information trigger fired; real official SABC site retrieved three articles with dates. Exit 0. |
| E-6 | 2026-11-27 13:49:24 | `IAM_BROWSER_E2E_URL='https://react.dev/'` + `IAM_BROWSER_E2E=1 python tests/e2e_browser_smoke.py` | JS-rendered SPA opened in real Chromium; title "React" and rendered body text extracted. Exit 0. |
| E-7 | 2026-11-27 (this session) | Real Postgres integration against the running `aura-postgres` container (localhost:5434) | Cache store → hit (`+cache`) → TTL expiry → `None`; IICS source and one claim created. Validation rows deleted afterwards. |

**Database evidence:** `backend/tests/test_live_evidence_db.py` verifies cache store, hit, TTL expiry and IICS registration against a real aiosqlite engine; E-7 repeats the same lifecycle against deployed Postgres. Paid-search fail-closed is verified by a deterministic policy test; no paid call was made.

---

## D. Not live-validated — must not be claimed as validated

| Item | Reason |
|------|--------|
| OCR of scanned images | `pytesseract` is installed but no Tesseract binary was verified on this host; no image was extracted or transcribed. |
| Audio/video multimedia understanding | No transcription engine is installed; no media content was processed. |
| SearXNG adapter | Implemented; the public instance tried (`searx.be`) did not return JSON, and no self-hosted endpoint is configured here. |
| Tavily adapter | Implemented; no API key, so it returns an explicit error and is excluded from automatic chains. No live paid call was made. |

---

## E. Sign-off checklist

- ☐ Owner has read proposed Document 34.
- ☐ Owner has accepted or rejected each companion decision in section A.
- ☐ Owner has reviewed real-web evidence E-1 to E-7 and the unresolved items in section D.
- ☐ Creator signer is available and its public key matches `CREATOR_PUBLIC_KEY`.
- ☐ A pending approval request is prepared with `python scripts/creator_request_od54.py` (no signature yet) for action `architecture.decision.confirm` / target `OD-54`.
- ☐ Creator signs the one-time challenge with the external hardware signer.
- ☐ `CreatorApprovalService.decide()` verifies `signer_id`, expiry and ED25519 signature.
- ☐ **Only then:** add OD-54 to `IAM_OWNER_DECISIONS.md` and a navigation row to `ARCHITECTURE_INDEX.md`.
- ☐ **Only then:** change Document 34 status from PROPOSED to CONFIRMED.

Until those steps are complete, `ARCHITECTURE_INDEX.md` and `IAM_OWNER_DECISIONS.md` remain untouched, and Doc 34 remains a proposal.

---

## F. Reproduce the real-web evidence (read-only)

```powershell
cd D:\AI\project-aura\backend
$env:IAM_LIVE_E2E = '1'
python tests/e2e_live_information_smoke.py
```

The command retrieves public pages only, uses no credentials and sends no private IAM data. A non-zero exit with a printed retrieval note is a truthful failure, not a pass.
