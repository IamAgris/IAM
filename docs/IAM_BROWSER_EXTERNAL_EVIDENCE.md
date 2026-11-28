# Doc 29 / OD-49 — external evidence record

**Date:** 28 November 2026
**Scope:** the external items that Doc 29 §11 and the completion plan listed as
open after all eight code phases passed. Each line below is a recorded run, not
a status claim.

| Item | Result | Evidence |
|------|--------|----------|
| Signed OD-49 decision artefact | **Signed and verified** | `docs/IAM_OD49_SIGNOFF_SHEET.md` — request `cr_361cd0a2b8f938161d9b42f323a7f246`, ED25519 signature verified, authorization `edc0ca61-df9f-4176-a54a-27cbf11c81a6`. |
| Live browser substrate smoke | **Passed** | `tests/browser_substrate_smoke.py` printed `IAM_BROWSER_P1_OK`: session open, task submitted (202), task id and actor attributed, status `completed`, evidence preserved, captcha target rejected (400), session closed. |
| Live Postgres integration | **Passed** | `backend/tests/integration_db_check.py` applied all migrations including `049_browser_substrate.sql` to a throwaway DB (234 tables) and printed `ALL DATABASE INTEGRATION CHECKS PASSED`, including "browser task run, evidence and attribution persistence". |
| Firefox/WebKit compatibility | **Passed** | `backend/scripts/browser_compatibility_check.py` inside the backend container printed `IAM_BROWSER_COMPAT_OK` — chromium, firefox and webkit all returned HTTP 200 and read the same public page. |
| Tor/onion live drill | **Passed** | Tor 0.4.9.15 started in the backend container; `https://check.torproject.org/api/ip` via SOCKS returned `{"IsTor":true,...}`. IAM's `OnionServiceIntelligence.check_availability` reached a live V3 onion (`status_code 301`). Kill switch engaged → egress denied; released → state cleared. Printed `IAM_TOR_LIVE_DRILL_OK`. |

## Fixes required to obtain this evidence

1. `tests/auth_headers.py` patched only module-level `httpx.get/post`; client-based
   smoke scripts sent no credential. It now also patches `httpx.Client.request`.
2. `tests/browser_substrate_smoke.py` used an empty step target (rejected by the
   egress guard) and stale `expected_text`; both corrected.
3. `UWAIEService.inspect()` did not apply the challenge/egress guard used by task
   execution; a captcha URL was fetched with HTTP 200. It now refuses empty,
   challenge and egress-denied targets before navigation.

## Honest boundaries

- The OD-49 signature was produced by the **local development signer**, not a
  hardware token. OD-03 still requires the operator's hardware signer for
  production authority.
- Availability is not proof of operator identity; the onion note says so.
- The Tor drill used a Tor daemon, not the official Tor Browser binary. Browser
  sessions still fail closed when the official binary is absent.
- No claim is made that the docs' frozen status tables were rewritten; the
  decision register and index remain owner-controlled.
