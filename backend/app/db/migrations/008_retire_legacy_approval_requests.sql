-- =============================================================================
-- Retire the legacy in-app approval-request flow (OD-19)
-- =============================================================================
-- External-presence integrations now use Creator email requests and signed
-- challenges via creator_requests / creator_authorizations. Preserve old rows
-- as an inert archive instead of deleting them.

ALTER TABLE IF EXISTS approval_requests
    RENAME TO legacy_approval_requests;
