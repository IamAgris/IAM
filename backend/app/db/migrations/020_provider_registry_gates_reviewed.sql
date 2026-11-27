-- Financial intelligence provider gates: model added gates_reviewed without a DB ALTER.

ALTER TABLE provider_registry_entries ADD COLUMN IF NOT EXISTS gates_reviewed BOOLEAN NOT NULL DEFAULT FALSE;
