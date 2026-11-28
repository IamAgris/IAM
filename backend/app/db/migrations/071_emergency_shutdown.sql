-- Repository-wide emergency shutdown state (OD-11 / OD-19).
-- One durable row per scope. 'global' halts every governed subsystem:
-- inference, autonomy, browser and trading. Only a signed Creator
-- authorization may change it; IAM cannot lift its own emergency stop.

CREATE TABLE IF NOT EXISTS emergency_shutdown_state (
    scope TEXT PRIMARY KEY,
    halted BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT,
    actor TEXT,
    authorization_id TEXT,
    engaged_at TIMESTAMPTZ,
    details JSON NOT NULL DEFAULT '{}'::json
);

INSERT INTO emergency_shutdown_state (scope, halted, details)
VALUES ('global', FALSE, '{}'::json)
ON CONFLICT (scope) DO NOTHING;
