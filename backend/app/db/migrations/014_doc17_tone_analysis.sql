-- Doc 17 / OD-33: tone and influence analysis evidence records.

CREATE TABLE IF NOT EXISTS tone_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type TEXT NOT NULL DEFAULT 'text',
    content_summary TEXT NOT NULL,
    tone TEXT NOT NULL DEFAULT 'neutral',
    register TEXT NOT NULL DEFAULT 'informal',
    sentiment NUMERIC(3, 2) NOT NULL DEFAULT 0.0,
    confidence NUMERIC(3, 2) NOT NULL DEFAULT 0.0,
    signals JSONB NOT NULL DEFAULT '[]'::jsonb,
    manipulation_indicators JSONB NOT NULL DEFAULT '[]'::jsonb,
    interpretations JSONB NOT NULL DEFAULT '[]'::jsonb,
    caveat TEXT NOT NULL DEFAULT 'Possible interpretations from text alone, not psychological diagnoses.',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_tone_source_type CHECK (source_type IN ('message', 'article', 'post', 'comment', 'discussion', 'text')),
    CONSTRAINT ck_tone_confidence CHECK (confidence BETWEEN 0 AND 1),
    CONSTRAINT ck_tone_sentiment CHECK (sentiment BETWEEN -1 AND 1)
);
CREATE INDEX IF NOT EXISTS ix_tone_analyses_created_at ON tone_analyses (created_at DESC);
