-- IAM memory embeddings — align the pgvector column with the local embedder.
-- Memory embeddings are generated locally by Ollama (MEMORY_EMBEDDING_MODEL,
-- default nomic-embed-text = 768 dimensions), never by a paid provider. The
-- original VECTOR(1536) column was sized for text-embedding-3-small and caused
-- every memory write to fail with "expected 1536 dimensions, not 768".
-- No embeddings existed at migration time; any pre-existing vectors are
-- dropped and must be regenerated with the configured local model.

ALTER TABLE memory_embeddings
    ALTER COLUMN embedding TYPE vector(768) USING NULL;
