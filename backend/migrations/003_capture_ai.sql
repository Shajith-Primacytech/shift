CREATE TABLE capture_ai_runs (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id), original_submission TEXT NOT NULL, proposal TEXT, execution TEXT NOT NULL, created_at TEXT NOT NULL, version_id TEXT UNIQUE REFERENCES knowledge_versions(id), reviewed_structure TEXT);
CREATE INDEX capture_ai_owner_time ON capture_ai_runs(owner_id,created_at);
