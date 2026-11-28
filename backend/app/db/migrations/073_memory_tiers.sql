-- OD-45 memory tiers: add an epistemic tier to visitor memory without
-- changing the existing six flat memory_type values. Existing rows default to
-- 'episodic', which is the honest classification for unverified observations.

ALTER TABLE memory_items
    ADD COLUMN IF NOT EXISTS tier TEXT NOT NULL DEFAULT 'episodic';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_memory_tier') THEN
        ALTER TABLE memory_items
            ADD CONSTRAINT ck_memory_tier
            CHECK (tier IN ('working', 'episodic', 'semantic', 'procedural',
                            'relationship', 'self', 'strategic'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_memory_items_tier ON memory_items (tier);
