-- =============================================================================
-- Autonomous live-research monitoring (proposed Doc 32 § autonomous extension).
-- Bounded schedules only; uses the existing ARQ runtime for execution and
-- never grants authority to spend, disclose private data or enter agreements.
-- =============================================================================

CREATE TABLE IF NOT EXISTS live_research_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic TEXT NOT NULL,
    query TEXT NOT NULL,
    interval_minutes INTEGER NOT NULL DEFAULT 60,
    enabled BOOLEAN NOT NULL DEFAULT true,
    owner TEXT NOT NULL DEFAULT 'creator',
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_live_research_interval
        CHECK (interval_minutes BETWEEN 15 AND 10080)
);

CREATE INDEX IF NOT EXISTS ix_live_research_due ON live_research_tasks (enabled, next_run_at);
