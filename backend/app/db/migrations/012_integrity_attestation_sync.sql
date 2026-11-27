-- Protected-core integrity, node attestation and signed sync (OD-05, OD-11, OD-13, OD-26)

CREATE TABLE IF NOT EXISTS integrity_manifests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version TEXT NOT NULL,
    root_hash TEXT NOT NULL,
    manifest JSONB NOT NULL,
    signed_by TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_integrity_manifests_root_hash ON integrity_manifests (root_hash);

CREATE TABLE IF NOT EXISTS node_attestations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID NOT NULL REFERENCES registered_nodes(id) ON DELETE CASCADE,
    public_key TEXT NOT NULL,
    core_hash TEXT NOT NULL,
    platform_hash TEXT,
    signature TEXT NOT NULL,
    payload JSONB NOT NULL,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    result TEXT NOT NULL DEFAULT 'candidate',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_node_attestation_result
        CHECK (result IN ('candidate', 'restricted', 'trusted', 'revoked'))
);
CREATE INDEX IF NOT EXISTS ix_node_attestations_node_id ON node_attestations (node_id);

CREATE TABLE IF NOT EXISTS sync_objects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publisher_node_id UUID NOT NULL REFERENCES registered_nodes(id) ON DELETE CASCADE,
    object_type TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    payload JSONB NOT NULL,
    signature TEXT NOT NULL,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_sync_objects_publisher ON sync_objects (publisher_node_id);
CREATE INDEX IF NOT EXISTS ix_sync_objects_content_hash ON sync_objects (content_hash);
