-- Add explicit Creator-approval requirement to integration registry (OD-19).
-- Existing rows default to TRUE, the safe/permission-preserving value.

ALTER TABLE integration_registry
    ADD COLUMN IF NOT EXISTS requires_creator_approval BOOLEAN NOT NULL DEFAULT TRUE;
