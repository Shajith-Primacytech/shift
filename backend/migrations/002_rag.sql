CREATE TABLE rag_generations (version_id TEXT PRIMARY KEY REFERENCES knowledge_versions(id), fingerprint TEXT NOT NULL, embedding_key TEXT NOT NULL);
CREATE TABLE chunk_embeddings (chunk_id TEXT PRIMARY KEY REFERENCES knowledge_chunks(id) ON DELETE CASCADE, embedding_key TEXT NOT NULL, vector BLOB NOT NULL);
CREATE VIRTUAL TABLE rag_fts USING fts5(chunk_id UNINDEXED, version_id UNINDEXED, content);
