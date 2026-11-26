-- OD-02: named legal entity on business projects (model added without a DB ALTER).

ALTER TABLE business_projects ADD COLUMN IF NOT EXISTS legal_entity TEXT;
