-- =============================================================================
-- Retire the legacy owner-authorization path (OD-19 cleanup)
-- =============================================================================
-- The /api/v1/owner routes, service and model have been removed. All authority
-- now comes from signed Creator email challenges (migration 004).
--
-- This migration preserves historical rows as an inert archive rather than
-- deleting them. Nothing in the application reads this table.

ALTER TABLE IF EXISTS owner_authorizations
    RENAME TO legacy_owner_authorizations;

-- The column on internet_permissions keeps its historical DB name for
-- compatibility; the ORM now exposes it as requires_creator_authorization.
