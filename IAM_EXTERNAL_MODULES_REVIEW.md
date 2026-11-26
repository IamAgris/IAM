# External Module Review

## Scope

Reviewed the modules that appeared in the tree outside the main implementation
work: P2P transport, Aegis, OEDIE free sandboxes, creator communication, node
registry and economy adapters.

## Findings

- All modules import cleanly. The app registers 442 OpenAPI paths, of which ~34
  belong to P2P/Aegis/sandbox surfaces.
- `P2PTransport` signs envelopes, rejects tampered payloads, duplicate IDs,
  replayed sequences and non-shareable topics. It implements store-and-forward
  for offline peers.
- `AegisEngine` detects prompt injection and sensitive data, verifies scope with
  exact target matching (prefix confusion is denied), and recommends defensive
  remediation only.
- Added `backend/tests/test_p2p_and_aegis.py` (8 tests) covering signature
  round-trip, tampering, replay, duplicate suppression, offensive-topic rejection,
  prompt injection detection, prefix confusion and broad-target denial.
- Added HTTP-level checks to `backend/tests/integration_db_check.py`: Aegis
  analyse/verify-scope, P2P broadcast (allowed and offensive topics), and signed
  sync object publishing with an untrusted publisher.
- Fixed deprecated `datetime.utcnow()` usage in `aegis.py`. No SQLAlchemy
  relationship warnings remain.
- Fixed `AttestationService.publish_object()` sending a non-UUID publisher id to
  a UUID column. It now returns `AttestationError` (HTTP 400) instead of a DBAPI
  error (HTTP 500).

## Verification

- 364 unit tests pass.
- Postgres + Redis integration check exits 0.
- HTTP endpoints for Aegis, P2P broadcast and signed-sync rejection are now
  exercised by the integration check. Node-attestation and WebSocket peer paths
  remain service-level only.

## Remaining

- WebSocket peer sessions and full signed P2P skill-exchange flows remain
  future work; services and primary HTTP routes are covered.
