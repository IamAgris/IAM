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
- Integration check exits 0 with Postgres + Redis; 364 unit tests pass.
