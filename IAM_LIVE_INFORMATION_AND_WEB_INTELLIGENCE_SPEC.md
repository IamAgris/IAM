# IAM — Live Information & Web Intelligence Policy Specification

**Document:** 34 — **PROPOSED ADDENDUM** (to Documents 11, 14, 23-A, 29 and 31)  
**Version:** 0.2 · 27 November 2026  
**Status:** **PROPOSED — NOT PART OF THE FROZEN BASELINE.** No owner decision has been recorded for this document. It does not amend the authority tables in `ARCHITECTURE_INDEX.md` or `IAM_OWNER_DECISIONS.md`; a navigation-only row was added to the index. Numbered 34/OD-54 because Doc 32/OD-52 and Doc 33/OD-53 were assigned to other decisions.  
**Proposed decision:** OD-54 (not yet recorded — creator approval required)  
**Parent:** `IAM_FINAL_CONSOLIDATION.md`, `IAM_BROWSER_INTELLIGENCE_MASTER_SPEC.md` (Doc 29, OD-49)  
**Related:** Doc 11 (OD-27, UWAIE), Doc 14 (OD-30, global research), Doc 23/23-A (OD-38/OD-46), Doc 29a (Phase 1 plan), Doc 31 (OD-51, multi-provider governance), `IAM_SECURITY_AND_INTERNET_POLICY.md`, `IAM_API_CONTRACTS.md`

> **Scope rule:** This document is an *addendum of behavioural and operational gaps* to the already-frozen browser/web architecture. It does **not** create a fifteenth/sixteenth top-level system, a second browser stack, a second memory store or a new AI identity. Doc 29 remains the authoritative browser and web-research architecture. Where rules overlap, the **stricter** rule applies.

---

## 0. Why this addendum exists

The frozen baseline already contains the browser substrate, research pipeline, security gateway, knowledge bridge and provider independence needed for general web research (Doc 29 §13: 20/20 requirements). The operating gap is narrower and behavioural:

1. The primary model has **no standing instruction** to recognise current-information requests; nothing prevents the generic response *"As an AI language model, I don't have access to real-time news feeds."*
2. There is **no automatic search-trigger classification** or source-first rule.
3. There is no **search-provider management layer for search providers** (OD-51 governs *model* providers only).
4. There is no **research-result cache with freshness TTL or source-reputation record** (`website_knowledge` stores procedural per-site knowledge, not retrieved-evidence records).
5. Citation, uncertainty and conflict-labelling rules are distributed across Doc 14 and Doc 29 §3.4/§6.1 but are not assembled into one output contract.
6. A few acceptance cases (cache reuse, stale results, conflicting reports) are not in Doc 29 §9.

This addendum specifies only those six gaps.

---

## 1. Authority relationships

| Decision | Relationship |
|----------|--------------|
| OD-01, OD-03, OD-11 | Identity, signing and protected core unchanged. |
| OD-04 / OD-25 | Paid search providers require signed Creator authorisation; fail-closed. |
| OD-27 (UWAIE) | Arbitrary user-supplied URLs stay in scope; permission checks unchanged. |
| OD-30 (global research) | Provenance, date and correction rules inherited. |
| **OD-46** | The shared primary is **Qwen2.5-Coder 3B** (`qwen2.5-coder:3b`). All references to "Qwen2.5:3B" in proposals are informal; no reopening of OD-46 is requested. |
| OD-49 (Doc 29) | This addendum adds behaviour on top of BIWOS/Web Research Engine; it does not replace them. |
| OD-51 (Doc 31) | Model-provider isolation and accounting inherited; search-provider management is the missing parallel layer. |
| OD-08 (ARQ) | Any background/scheduled retrieval uses ARQ; no new queue. |

---

## 2. Standing behavioural policy (added to the primary system instructions)

The following must be injected into every primary-model system-instruction set used by the main assistant, specialist agents and autonomous research processes. It is an **always-on IAM operating rule**, not a user-selectable mode.

> **WEB ACCESS AND LIVE INFORMATION POLICY**
>
> IAM must never unnecessarily claim it cannot access real-time information, browse the internet, retrieve news or access current information.
>
> 1. Automatically recognise requests requiring current information.
> 2. Invoke the Web Intelligence Engine whenever online research is appropriate.
> 3. Do not ask users to visit websites themselves when IAM can retrieve the information.
> 4. When a specific source is requested, prioritise that source before expanding the search.
> 5. Retrieve and analyse actual source content, not only search-result descriptions.
> 6. Verify publication dates, relevance and reliability.
> 7. Cross-reference important claims where possible.
> 8. Provide citations and direct source links.
> 9. Clearly communicate uncertainty, conflicting reports and unavailable information.
> 10. Never fabricate search results, articles, dates, quotations or citations.
> 11. If a provider fails, attempt another configured provider when available.
> 12. If all search providers fail, explain the actual technical limitation and offer an alternative.
> 13. Never use generic responses such as "As an AI language model, I don't have access to real-time news feeds."
> 14. Maintain a natural, conversational personality; do not expose internal tool operations unless the user asks.

**Implementation reference:** `backend/app/services/live_information_policy.py` (`WEB_ACCESS_POLICY`, `with_live_policy`), injected by `backend/app/api/routes/models.py::_prepare_messages`.

---

## 3. Automatic search triggers

The engine classifies intent **deterministically before inference**; the model is not trusted to decide whether to browse on its own. The classifier only sets `needs_search`; the Web Research Engine then performs the retrieval.

| Category | Examples | Action |
|----------|----------|--------|
| `latest_news` | "latest news", "headlines", "recent developments" | Search current news |
| `breaking_news` | "breaking", "just in", "developing story" | Search immediately |
| `current_events` | "what's happening", "current events" | Search current sources |
| `latest_technology` | "latest AI model", "new release", "recent paper" | Search recent publications |
| `current_prices` | "current price", "today's exchange rate", "how much is" | Retrieve current pricing |
| `company_developments` | "earnings", "acquisition", "company announcement" | Search announcements |
| `current_laws` | "new law", "regulation", "court ruling" | Retrieve legal sources |
| `sports_results` | "final score", "standings", "match result" | Retrieve results |
| `weather` | "forecast", "temperature", "storm warning" | Retrieve live weather |
| `live_information` | "live", "real-time", "up to date", "as of now" | Search current sources |
| `explicit_search` | "search the web", "look it up", "google it" | Always attempt a web search |
| `historical` | "history of", "in 1999", "who founded" | Answer from stored knowledge; search only when another trigger is present |

**Rules**

- Even if IAM already knows a topic, training knowledge must not be assumed current.
- Mentioning a publisher alone does **not** trigger a search (e.g. "Who founded the BBC?"); it only sets a preferred source once a current-information trigger is present.
- A user-supplied URL sets that host as the preferred source and triggers retrieval.
- Research depth is inferred (`quick`, `standard`, `deep`) and may be overridden by the user.

---

## 4. Source-first retrieval and research depth

1. If a news organisation or domain is named (e.g. SABC News → `sabcnews.com`), search that source first (`site:` query or direct URL).
2. If the source yields insufficient evidence, expand to additional credible sources.
3. Distinguish **search results** from **actually retrieved content**. A snippet is a candidate, not evidence.
4. Depth selection:
   - **Quick** — one question, relevant sources, concise answer.
   - **Standard** — multiple sources and corroboration.
   - **Deep** — planned multi-stage investigation, claim-level evidence, contradiction detection.
5. For SABC-class questions: identify source → search official site → retrieve articles → check dates/timestamps → cross-reference → summarise conversationally → link originals.

### 4.1 Conditional browser escalation (required)

Browser access is **not** enabled globally. `iam_live_info_use_browser` stays `false`
for ordinary conversations. Browser retrieval is activated only when all of the
following hold:

1. a current-information trigger fired; **and**
2. the configured provider returned no *suitable* evidence.

A Wikipedia fallback, an empty result set, or results that do not include the
named publisher's domain are **not suitable evidence** for a live request. They
are never silently substituted for current reporting. Escalation then proceeds:

- named publisher → read the **official publisher website** first (canonical
  news path, then a `www` variant), extracting actual article links and dates;
- official site unreachable or insufficient → `site:<domain>` browser search;
- still insufficient → general browser search across other credible sources;
- no evidence at all → an explicit retrieval limitation, never invented citations.

Navigation links, fragments and empty anchors are excluded from evidence. A
publication date is attached when it appears next to the article title;
otherwise the date is explicitly reported as unavailable.

`iam_live_info_escalate_to_browser` (default `true`) governs this conditional
path. Operators may disable escalation; the model must then be told that live
retrieval was unavailable. Paid search providers are still never invoked
automatically (OD-04/OD-25, `SEARCH_ACTION`).

**Implementation reference:** `_is_suitable_live_evidence`, `_try_browser_search`
and `collect_live_evidence` in `backend/app/services/live_information_policy.py`.

---

## 5. Engine boundary (who does what)

```
Qwen2.5-Coder 3B (OD-46 shared primary)  → decides what information is needed
Web Intelligence Engine                  → classifies intent, plans, discovers sources
Existing search / browser services       → perform discovery, retrieval, extraction
Verification services                    → dates, credibility, corroboration, contradiction
Qwen2.5-Coder 3B                         → analyses retrieved evidence
IAM                                      → formulates and delivers the final answer
```

The engine is a **shared capability** of IAM, available to the main assistant, authorised specialist agents and autonomous research through the Doc 29 §7 internal API. It is not an external identity and not a dependency on a hosted model.

---

## 6. Search-provider management (parallel to OD-51 for model providers)

- Provider-independent adapters; no fixed publisher whitelist for ordinary public-web research.
- Provider discovery, health check, quota/cost tracking and automatic failover.
- **Free-first:** self-hosted or no-key providers preferred (SearXNG, DuckDuckGo HTML where permitted). A real no-key DuckDuckGo HTML adapter is available as `provider="duckduckgo"` in `search_service.py`; it is used after official-site retrieval fails. Wikipedia may supply *background*, but is explicitly **not** live evidence and is excluded from current-information results.
- **Fail-closed paid use:** Brave, Tavily or any paid search API requires signed Creator authorisation (`SEARCH_ACTION`) before use; automatic chat-time retrieval never invokes a paid provider.
- No single provider is IAM's only gateway to the web.
- Respect robots policies, API terms, rate limits and geographic/access restrictions; never bypass authentication, paywalls or access controls without authorisation.

---

## 7. Research cache, freshness and source reputation

- **Evidence records** preserve original URL, publisher, publication/last-modified date, retrieval time, extracted text and claim-level attribution.
- **Freshness TTL** by class: breaking news minutes; current prices/weather/live data short; general reporting hours; stable documentation days. Expired evidence is refreshed, not presented as current.
- **Source reputation** is a signal, never a permission override: original-source status, corroboration count, syndication/duplicate detection, sponsored-content flags and contradiction history.
- Cached research is reused only while within TTL; repeat queries should hit cache rather than re-query providers.
- Cache and reputation records integrate with existing Postgres/pgvector tables; no new vector database is introduced.

**Reference implementation:** `live_evidence_cache` (migration 058, query hash +
TTL: breaking 15 min, current 60 min, standard 360 min, stable 30 days) and
`backend/app/services/live_evidence_cache.py`. Source reputation is read from the
existing IICS `iics_sources` registry; no duplicate reputation store. Cache and
reputation failures are fail-soft and never block research.

---

## 8. Output contract

Every current-information answer must:

1. give a direct answer first;
2. name the source, publication date and clickable URL for each material claim;
3. label each claim as one of: **confirmed**, **independently corroborated**, **single-source reporting**, **unverified claim**, **conflicting**, or **IAM analysis**;
4. state what could not be retrieved and why, without inventing sources;
5. keep a natural conversational tone and not expose internal tool operations unless asked.

---

## 9. Security and governance

All Doc 29 §5.2/§8 controls apply unchanged: prompt-injection defence, SSRF/private-network isolation, sandboxed browser, malware scanning, download restrictions, audit logging and website content treated as **untrusted data, never instructions**. Retrieved page text must be injected as labelled reference data, not as system instructions.

---

## 10. Acceptance tests (additions to Doc 29 §9)

| Test | Expected result |
|------|-----------------|
| Ask for latest SABC news | Retrieves recent SABC articles; official site tried first |
| Supply an arbitrary URL | Attempts retrieval; failure reported truthfully |
| Supply a JavaScript website | Uses browser rendering when enabled |
| Ask for multiple sources | Retrieves and compares sources with dates |
| Request a PDF analysis | Extracts document content |
| Search in another language | Finds and interprets relevant information |
| Search provider fails | Attempts configured fallback |
| Internet unavailable | Clearly identifies the limitation |
| Website contains prompt injection | Ignores malicious instructions |
| Search returns outdated results | Identifies their age |
| Conflicting reports | Explains the disagreement |
| Repeat a recent query | Reuses valid cached research |
| Primary persona asked "can you access real-time news?" | Does not produce the forbidden generic disclaimer |

### 10.1 Mandatory pre-OD-54 retrieval validation

These eight cases must pass before OD-54 is recorded:

1. Ask for the latest SABC news without an API key.
2. Verify that actual SABC articles (URL and extracted body) reach the evidence message.
3. Name a publisher whose site is unavailable.
4. Verify fallback to other credible sources.
5. Ask a current technology question and verify live-web retrieval is used.
6. Supply an arbitrary user-provided URL and verify it becomes the preferred source.
7. Verify historical questions do not trigger browsing.
8. Verify browser failures never produce fabricated citations.

**Reference implementation:** `backend/tests/test_live_information_policy.py` (`LiveRetrievalAcceptanceTests`), `backend/tests/test_live_evidence_cache.py`, and the opt-in real-web check `backend/tests/e2e_live_information_smoke.py` (`IAM_LIVE_E2E=1`). Live runs of 27 November 2026: (1) three real SABC articles with URLs and dates retrieved from the official site while the Wikipedia fallback was rejected; (2) an unavailable named publisher (`example.org`) fell back through the real free HTTP adapter to CNN and UN News; (3) a current-technology query with no named publisher rejected the Wikipedia fallback and retrieved real release-trackers. These are evidence of those runs only, not guarantees of future site availability.

---

## 11. Implementation status (reference, not an architecture decision)

| Clause | Reference implementation |
|--------|--------------------------|
| §2 standing policy | `live_information_policy.py`, injected in `models.py` |
| §3 triggers, §4 source-first and depth | `SearchTriggerClassifier`, official-site retrieval, DEEP follow-up stage |
| §6 provider management | `search_provider_registry.py` (health, quotas, free-first failover), DuckDuckGo HTTP adapter, SearXNG and Tavily adapters; `/api/v1/live-information/providers` |
| §7 cache / freshness / reputation | migration 058, `live_evidence_cache.py`, IICS source/claim registration |
| §8 output contract | `live_evidence_analysis.py` (claim labels, confidence, corroboration, contradictions, injection redaction) |
| §9 security | explicit public-host SSRF guard, injection redaction, untrusted-data labelling |
| Autonomous monitoring | migration 063, `live_research_monitor.py`, `/api/v1/live-information/monitor*` (bounded 15–10080 min, max 50 tasks) |
| Documents / media | `BrowserDocumentService` for PDFs/text, `live_media_service.py` for isolated Tesseract OCR and explicit transcription fail-closed |

User-supplied documents are parsed by `BrowserDocumentService` and non-English
current-information triggers are classified deterministically.

Live validation recorded in the OD-54 sign-off sheet: E-1 SABC official site,
E-2 unavailable-publisher fallback, E-3 Wikipedia rejection without a publisher,
E-4 public PDF extraction, E-5 non-English current query, E-6 JS-rendered SPA,
E-7 real Postgres cache/TTL/IICS lifecycle, E-8 isolated Tesseract OCR,
E-9 self-hosted SearXNG adapter, E-10 explicit transcription fail-closed.
User-supplied images are OCR'd through an isolated Tesseract container and audio
is delegated to IAM's existing voice service; neither produces trusted knowledge.
A successful transcript still requires a configured STT provider.

---

## 12. Change control

This document is proposed. It becomes part of the frozen baseline only after an owner records OD-54 in `IAM_OWNER_DECISIONS.md` and adds the navigation entry to `ARCHITECTURE_INDEX.md`. Until then the code reference implementation is **behavioural only** and claims no new system, no legal/IP authority and no completed Doc 29 implementation phase.
