-- =============================================================================
-- Legal entity binding for business projects (OD-02)
-- =============================================================================

ALTER TABLE business_projects
    ADD COLUMN IF NOT EXISTS legal_entity TEXT;
