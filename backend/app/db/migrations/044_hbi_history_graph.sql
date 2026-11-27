-- =============================================================================
-- Document 26 (OD-45): E1 Historical Knowledge Graph persistence
-- =============================================================================

CREATE TABLE IF NOT EXISTS hbi_graph_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_ref TEXT NOT NULL UNIQUE,
    node_type TEXT NOT NULL,
    label TEXT NOT NULL,
    period TEXT,
    region TEXT,
    date_low NUMERIC(10,2),
    date_high NUMERIC(10,2),
    properties JSON NOT NULL DEFAULT '{}'::json,
    evidence_class TEXT NOT NULL DEFAULT 'unverified'
        CHECK (evidence_class IN ('verified','well_supported','contested','unverified','speculation')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hbi_graph_nodes_type ON hbi_graph_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_hbi_graph_nodes_dates ON hbi_graph_nodes(date_low, date_high);

CREATE TABLE IF NOT EXISTS hbi_graph_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    edge_ref TEXT NOT NULL UNIQUE,
    from_ref TEXT NOT NULL,
    to_ref TEXT NOT NULL,
    relation TEXT NOT NULL,
    confidence NUMERIC(3,2) NOT NULL DEFAULT 0 CHECK (confidence BETWEEN 0 AND 1),
    evidence_class TEXT NOT NULL DEFAULT 'unverified',
    properties JSON NOT NULL DEFAULT '{}'::json,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hbi_graph_edges_from ON hbi_graph_edges(from_ref);
CREATE INDEX IF NOT EXISTS idx_hbi_graph_edges_to ON hbi_graph_edges(to_ref);
CREATE INDEX IF NOT EXISTS idx_hbi_graph_edges_relation ON hbi_graph_edges(relation);
