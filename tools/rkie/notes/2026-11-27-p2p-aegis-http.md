# Note: P2P/Aegis verification (27 November 2026)

Based on the current checkout; re-verify before reuse.

- `backend/app/services/p2p_transport.py` — signed envelopes via HMAC fallback,
  replay/duplicate/offensive-topic rejection, store-and-forward.
- `backend/app/services/aegis.py` — defensive analysis and exact scope matching;
  deprecated `datetime.utcnow()` calls replaced with timezone-aware `now()`.
- `backend/app/services/attestation_service.py` — `publish_object()` validated
  `publisher_node_id` as a UUID before querying `node_attestations`; an invalid id
  previously caused a DBAPIError (HTTP 500), now `AttestationError` (HTTP 400).
- Tests: `backend/tests/test_p2p_and_aegis.py` (service-level, 8 tests) and
  HTTP-level checks in `backend/tests/integration_db_check.py`.
- Signed P2P skill exchange added (`services/skill_exchange_service.py`, routes
  in `routes/p2p.py`, model `p2p_skills.py`, migration 012). Fixed outbound seq
  collision in `p2p_transport.py` and invalid `pending` status in
  `SkillForgeService.create()` for imported skills.
- WebSocket peer route covered by a fake-socket unit test (`WebSocketRouteTests`).
- CI workflow `.github/workflows/ci.yml` parses with three jobs: backend-unit,
  backend-integration, frontend (not yet executed on GitHub).
- UWAIE WP-01/WP-02 slice: `services/browser_engine_adapters.py`, per-session
  contexts in `services/browser_service.py`, config flags in `core/config.py`.
- Geospatial backend rendering: `GET /api/v1/geo/render` returns escaped SVG.
- Fixed environment-dependent production-DSN assertion in `tests/test_backup_service.py`.
- Doc 29 Phase 1 browser envelope wired at `routes/browser.py`; ARQ browser
  worker at `workers/arq_browser_worker.py`; opt-in live smoke
  `tests/e2e_browser_smoke.py`; Dockerfile installs Chromium/Firefox/WebKit.
- Targeted browser tests pass (13), integration check exits 0, and the full
  unit suite now passes (637 tests). Earlier external failures were resolved
  outside this work; re-verify before reusing.
