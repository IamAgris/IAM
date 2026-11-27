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
- Integration check exits 0 with Postgres + Redis; 421 unit tests pass.
