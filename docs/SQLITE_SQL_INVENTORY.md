# SHIFT SQLite schema and SQL inventory

Design evidence only. Generated 2026-10-18 from source text; no database was opened, application module imported, or private environment read.

Scope: all database execute/executemany/executescript call sites under backend/app and backend/tests, plus every checked-in SQLite migration. Bare Python helper functions named execute are not database calls. Dynamic SQL is retained as a source expression, never evaluated.

Source commit: `74d538b991c3c31b8cba853be68777ff8bd334f0`. Line numbers refer to this snapshot.

## Checked-in migrations

### backend/migrations/001_storage.sql

SHA-256: `767577638980739bb6c74cb7aaf272f785fb4322c34b9c9ce4986032c5f66029`

```sql
CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('technician','supervisor')), password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires_at INTEGER NOT NULL);
CREATE TABLE login_attempts (key TEXT NOT NULL, attempted_at INTEGER NOT NULL);
CREATE INDEX login_attempt_time ON login_attempts(key, attempted_at);
CREATE TABLE machines (id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE knowledge_records (id TEXT PRIMARY KEY, owner_id TEXT REFERENCES users(id), created_at TEXT NOT NULL);
CREATE TABLE knowledge_versions (id TEXT PRIMARY KEY, record_id TEXT NOT NULL REFERENCES knowledge_records(id), revision INTEGER NOT NULL, machine_id TEXT NOT NULL REFERENCES machines(id), title TEXT NOT NULL, symptom TEXT NOT NULL, content TEXT NOT NULL, kind TEXT NOT NULL, author TEXT NOT NULL, submitted_by TEXT REFERENCES users(id), problem TEXT NOT NULL DEFAULT '', root_cause TEXT NOT NULL DEFAULT '', resolution TEXT NOT NULL DEFAULT '', safety_notes TEXT NOT NULL DEFAULT '', status TEXT NOT NULL CHECK(status IN ('Pending','Approved','Rejected','Revoked')), created_at TEXT NOT NULL, UNIQUE(record_id,revision));
CREATE TABLE review_events (id INTEGER PRIMARY KEY, version_id TEXT NOT NULL REFERENCES knowledge_versions(id), reviewer_id TEXT REFERENCES users(id), reviewer_name TEXT NOT NULL, previous_status TEXT NOT NULL, decision TEXT NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE source_documents (id TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES knowledge_versions(id), name TEXT NOT NULL, media_type TEXT NOT NULL, size INTEGER NOT NULL, sha256 TEXT NOT NULL, data BLOB NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE knowledge_chunks (id TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES knowledge_versions(id), document_id TEXT REFERENCES source_documents(id), position INTEGER NOT NULL, page INTEGER, section TEXT, content TEXT NOT NULL, content_hash TEXT NOT NULL);
CREATE TABLE conversations (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id), machine_id TEXT NOT NULL REFERENCES machines(id), created_at TEXT NOT NULL);
CREATE TABLE conversation_messages (id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id), role TEXT NOT NULL CHECK(role IN ('user','assistant')), content TEXT NOT NULL, response_mode TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX versions_record ON knowledge_versions(record_id,revision);
CREATE INDEX versions_status ON knowledge_versions(status,machine_id);
```

### backend/migrations/002_rag.sql

SHA-256: `573e429d486839bf7cb79931efb52531913693d1937531bdd5c6005d5c6a0d23`

```sql
CREATE TABLE rag_generations (version_id TEXT PRIMARY KEY REFERENCES knowledge_versions(id), fingerprint TEXT NOT NULL, embedding_key TEXT NOT NULL);
CREATE TABLE chunk_embeddings (chunk_id TEXT PRIMARY KEY REFERENCES knowledge_chunks(id) ON DELETE CASCADE, embedding_key TEXT NOT NULL, vector BLOB NOT NULL);
CREATE VIRTUAL TABLE rag_fts USING fts5(chunk_id UNINDEXED, version_id UNINDEXED, content);
```

### backend/migrations/003_capture_ai.sql

SHA-256: `f18ecd9fe8e30b2e2270d9eef4402c5c2a71330f59e788caf5889a53fb642876`

```sql
CREATE TABLE capture_ai_runs (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id), original_submission TEXT NOT NULL, proposal TEXT, execution TEXT NOT NULL, created_at TEXT NOT NULL, version_id TEXT UNIQUE REFERENCES knowledge_versions(id), reviewed_structure TEXT);
CREATE INDEX capture_ai_owner_time ON capture_ai_runs(owner_id,created_at);
```

## Bootstrap schema and dynamic fragments

`backend/app/storage/database.py` also creates `schema_migrations(version TEXT PRIMARY KEY)` at startup. It executes each pending SQL statement from the migration files, in filename order, inside a transaction; applied filenames are recorded once. `PRAGMA foreign_keys=ON` is set on every connection, WAL on initialization, and SQLite busy timeout is 10 seconds. Commit on normal context exit, rollback on exceptions. Login and capture also explicitly commit at selected boundaries.

`LATEST` in storage.py: `v.revision=(SELECT MAX(v2.revision) FROM knowledge_versions v2 WHERE v2.record_id=v.record_id)`.

`ELIGIBLE` in retrieval.py: `v.status='Approved' AND v.revision=(SELECT MAX(v2.revision) FROM knowledge_versions v2 WHERE v2.record_id=v.record_id)`.

FTS5 creates internal shadow tables `rag_fts_data`, `rag_fts_idx`, `rag_fts_content`, `rag_fts_docsize`, `rag_fts_config` (default contentful FTS5). These are implementation details, not independently migrated application tables.

## app: 71 database execution call sites

### APP-001 — backend/app/api/capture.py:33 — structure_capture

```sql
SELECT 1 FROM machines WHERE id=?
```

### APP-002 — backend/app/api/capture.py:45 — structure_capture

```sql
BEGIN IMMEDIATE
```

### APP-003 — backend/app/api/capture.py:47 — structure_capture

```sql
SELECT 1 FROM capture_ai_runs WHERE owner_id=? AND created_at>?
```

### APP-004 — backend/app/api/capture.py:57 — structure_capture

```sql
INSERT INTO capture_ai_runs (id,owner_id,original_submission,execution,created_at) VALUES (?,?,?,?,?)
```

### APP-005 — backend/app/api/capture.py:81 — structure_capture

```sql
UPDATE capture_ai_runs SET proposal=?,execution=? WHERE id=?
```

### APP-006 — backend/app/api/storage.py:39 — current_user

```sql
SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token_hash=? AND s.expires_at>?
```

### APP-007 — backend/app/api/storage.py:73 — login

```sql
DELETE FROM login_attempts WHERE attempted_at<?
```

### APP-008 — backend/app/api/storage.py:75 — login

```sql
SELECT count(*) FROM login_attempts WHERE key=?
```

### APP-009 — backend/app/api/storage.py:82 — login

```sql
SELECT * FROM users WHERE username=?
```

### APP-010 — backend/app/api/storage.py:89 — login

```sql
INSERT INTO login_attempts VALUES (?,?)
```

### APP-011 — backend/app/api/storage.py:92 — login

```sql
DELETE FROM login_attempts WHERE key=?
```

### APP-012 — backend/app/api/storage.py:93 — login

```sql
DELETE FROM sessions WHERE expires_at<=? OR token_hash=?
```

### APP-013 — backend/app/api/storage.py:99 — login

```sql
INSERT INTO sessions VALUES (?,?,?)
```

### APP-014 — backend/app/api/storage.py:124 — logout

```sql
DELETE FROM sessions WHERE token_hash=?
```

### APP-015 — backend/app/api/storage.py:137 — machines

```sql
SELECT data FROM machines ORDER BY id
```

### APP-016 — backend/app/api/storage.py:148 — serialize

```sql
SELECT * FROM review_events WHERE version_id=? ORDER BY id DESC LIMIT 1
```

### APP-017 — backend/app/api/storage.py:154 — serialize

```sql
SELECT id,name,size,media_type AS type,sha256 FROM source_documents WHERE version_id=?
```

### APP-018 — backend/app/api/storage.py:159 — serialize

```sql
SELECT * FROM capture_ai_runs WHERE version_id=?
```

### APP-019 — backend/app/api/storage.py:202 — knowledge

```python
f"SELECT v.* FROM knowledge_versions v WHERE {LATEST} AND v.status='Approved' AND (?='' OR v.machine_id=?) AND (?='' OR instr(lower(v.title || ' ' || v.symptom || ' ' || v.content),lower(?))>0) ORDER BY v.created_at DESC"
```

### APP-020 — backend/app/api/storage.py:213 — submissions

```python
f"SELECT v.* FROM knowledge_versions v JOIN knowledge_records r ON r.id=v.record_id WHERE {LATEST} AND (?='supervisor' OR r.owner_id=?) ORDER BY v.created_at DESC"
```

### APP-021 — backend/app/api/storage.py:228 — save_submission

```sql
SELECT 1 FROM machines WHERE id=?
```

### APP-022 — backend/app/api/storage.py:255 — save_submission

```sql
BEGIN IMMEDIATE
```

### APP-023 — backend/app/api/storage.py:259 — save_submission

```sql
SELECT * FROM knowledge_records WHERE id=?
```

### APP-024 — backend/app/api/storage.py:266 — save_submission

```sql
SELECT MAX(revision)+1 FROM knowledge_versions WHERE record_id=?
```

### APP-025 — backend/app/api/storage.py:272 — save_submission

```sql
INSERT INTO knowledge_records VALUES (?,?,?)
```

### APP-026 — backend/app/api/storage.py:279 — save_submission

```sql
SELECT * FROM capture_ai_runs WHERE id=? AND owner_id=?
```

### APP-027 — backend/app/api/storage.py:307 — save_submission

```sql
INSERT INTO knowledge_versions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
```

### APP-028 — backend/app/api/storage.py:329 — save_submission

```sql
UPDATE capture_ai_runs SET version_id=?,reviewed_structure=? WHERE id=?
```

### APP-029 — backend/app/api/storage.py:334 — save_submission

```sql
INSERT INTO source_documents VALUES (?,?,?,?,?,?,?,?)
```

### APP-030 — backend/app/api/storage.py:349 — save_submission

```sql
SELECT * FROM knowledge_versions WHERE id=?
```

### APP-031 — backend/app/api/storage.py:390 — review

```sql
BEGIN IMMEDIATE
```

### APP-032 — backend/app/api/storage.py:391 — review

```python
f"SELECT v.*,r.owner_id FROM knowledge_versions v JOIN knowledge_records r ON r.id=v.record_id WHERE v.record_id=? AND {LATEST}"
```

### APP-033 — backend/app/api/storage.py:406 — review

```sql
UPDATE knowledge_versions SET status=? WHERE id=?
```

### APP-034 — backend/app/api/storage.py:409 — review

```sql
INSERT INTO review_events (version_id,reviewer_id,reviewer_name,previous_status,decision,note,created_at) VALUES (?,?,?,?,?,?,?)
```

### APP-035 — backend/app/api/storage.py:423 — review

```sql
SELECT * FROM knowledge_versions WHERE id=?
```

### APP-036 — backend/app/api/storage.py:435 — history

```sql
SELECT * FROM knowledge_records WHERE id=?
```

### APP-037 — backend/app/api/storage.py:443 — history

```sql
SELECT * FROM knowledge_versions WHERE record_id=? ORDER BY revision
```

### APP-038 — backend/app/api/storage.py:450 — history

```sql
SELECT e.* FROM review_events e JOIN knowledge_versions v ON v.id=e.version_id WHERE v.record_id=? ORDER BY e.id
```

### APP-039 — backend/app/api/storage.py:464 — document

```python
f"SELECT d.*,v.status,r.owner_id,({LATEST}) AS latest FROM source_documents d JOIN knowledge_versions v ON v.id=d.version_id JOIN knowledge_records r ON r.id=v.record_id WHERE d.id=?"
```

### APP-040 — backend/app/api/troubleshooting.py:28 — troubleshoot

```sql
SELECT 1 FROM machines WHERE id=?
```

### APP-041 — backend/app/demo.py:38 — provision

```sql
SELECT * FROM users WHERE username=?
```

### APP-042 — backend/app/rag/prepare.py:22 — main

```sql
SELECT id FROM machines
```

### APP-043 — backend/app/rag/retrieval.py:48 — valid_evidence

```python
f"SELECT v.* FROM knowledge_versions v WHERE v.id=? AND v.machine_id=? AND {ELIGIBLE}"
```

### APP-044 — backend/app/rag/retrieval.py:52 — valid_evidence

```sql
SELECT content_hash FROM knowledge_chunks WHERE id=? AND version_id=?
```

### APP-045 — backend/app/rag/retrieval.py:89 — _sync

```python
f"SELECT v.* FROM knowledge_versions v WHERE {ELIGIBLE} AND v.machine_id=?"
```

### APP-046 — backend/app/rag/retrieval.py:96 — _sync

```sql
SELECT * FROM rag_generations WHERE version_id=?
```

### APP-047 — backend/app/rag/retrieval.py:117 — _sync

```sql
BEGIN IMMEDIATE
```

### APP-048 — backend/app/rag/retrieval.py:118 — _sync

```python
f"SELECT v.* FROM knowledge_versions v WHERE v.id=? AND {ELIGIBLE}"
```

### APP-049 — backend/app/rag/retrieval.py:124 — _sync

```sql
DELETE FROM rag_fts WHERE version_id=?
```

### APP-050 — backend/app/rag/retrieval.py:125 — _sync

```sql
DELETE FROM knowledge_chunks WHERE version_id=?
```

### APP-051 — backend/app/rag/retrieval.py:133 — _sync

```sql
INSERT INTO knowledge_chunks (id,version_id,position,section,content,content_hash) VALUES (?,?,?,?,?,?)
```

### APP-052 — backend/app/rag/retrieval.py:147 — _sync

```sql
INSERT INTO chunk_embeddings VALUES (?,?,?)
```

### APP-053 — backend/app/rag/retrieval.py:151 — _sync

```sql
INSERT INTO rag_fts VALUES (?,?,?)
```

### APP-054 — backend/app/rag/retrieval.py:155 — _sync

```sql
INSERT OR REPLACE INTO rag_generations VALUES (?,?,?)
```

### APP-055 — backend/app/rag/retrieval.py:168 — _retrieve

```python
f"SELECT 1 FROM knowledge_versions v WHERE {ELIGIBLE} AND v.machine_id=?"
```

### APP-056 — backend/app/rag/retrieval.py:178 — _retrieve

```python
f"""SELECT c.*,v.record_id,v.title,v.machine_id,g.fingerprint,e.vector
                    FROM knowledge_chunks c JOIN knowledge_versions v ON v.id=c.version_id
                    JOIN chunk_embeddings e ON e.chunk_id=c.id JOIN rag_generations g ON g.version_id=v.id
                    WHERE {ELIGIBLE} AND v.machine_id=? AND e.embedding_key=?"""
```

### APP-057 — backend/app/rag/retrieval.py:185 — _retrieve

```python
f"""SELECT f.chunk_id FROM rag_fts f JOIN knowledge_versions v ON v.id=f.version_id
                    WHERE rag_fts MATCH ? AND {ELIGIBLE} AND v.machine_id=? ORDER BY bm25(rag_fts) LIMIT 20"""
```

### APP-058 — backend/app/storage/database.py:17 — connect

```sql
PRAGMA foreign_keys=ON
```

### APP-059 — backend/app/storage/database.py:34 — initialize

```sql
PRAGMA journal_mode=WAL
```

### APP-060 — backend/app/storage/database.py:35 — initialize

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY)
```

### APP-061 — backend/app/storage/database.py:40 — initialize

```sql
BEGIN IMMEDIATE
```

### APP-062 — backend/app/storage/database.py:41 — initialize

```sql
SELECT 1 FROM schema_migrations WHERE version=?
```

### APP-063 — backend/app/storage/database.py:46 — initialize

```python
statement
```

### APP-064 — backend/app/storage/database.py:47 — initialize

```sql
INSERT INTO schema_migrations VALUES (?)
```

### APP-065 — backend/app/storage/database.py:52 — initialize

```sql
BEGIN IMMEDIATE
```

### APP-066 — backend/app/storage/database.py:53 — initialize

```sql
SELECT 1 FROM machines LIMIT 1
```

### APP-067 — backend/app/storage/database.py:57 — initialize

```sql
INSERT INTO machines VALUES (?,?)
```

### APP-068 — backend/app/storage/database.py:62 — initialize

```sql
INSERT INTO knowledge_records VALUES (?,NULL,?)
```

### APP-069 — backend/app/storage/database.py:66 — initialize

```sql
INSERT INTO knowledge_versions (id,record_id,revision,machine_id,title,symptom,content,kind,author,status,created_at) VALUES (?,?,1,?,?,?,?,?,?,?,?)
```

### APP-070 — backend/app/storage/database.py:82 — initialize

```sql
INSERT INTO review_events (version_id,reviewer_name,previous_status,decision,note,created_at) VALUES (?,?,?,?,?,?)
```

### APP-071 — backend/app/storage/security.py:42 — create_user

```sql
INSERT INTO users VALUES (?,?,?,?,?,?)
```

## tests: 31 database execution call sites

### TESTS-001 — backend/tests/test_capture.py:237 — test_end_to_end_pending_edit_approve_index_and_revoke

```sql
SELECT count(*) FROM knowledge_records WHERE owner_id IS NOT NULL
```

### TESTS-002 — backend/tests/test_capture.py:243 — test_end_to_end_pending_edit_approve_index_and_revoke

```sql
SELECT version_id FROM capture_ai_runs WHERE id=?
```

### TESTS-003 — backend/tests/test_capture.py:309 — test_run_ownership_stale_source_confirmation_and_one_use

```sql
SELECT count(*) FROM knowledge_records WHERE owner_id IS NOT NULL
```

### TESTS-004 — backend/tests/test_capture.py:339 — test_failed_run_cannot_submit_ai_but_manual_capture_survives

```sql
SELECT execution FROM capture_ai_runs
```

### TESTS-005 — backend/tests/test_capture.py:371 — test_endpoint_auth_csrf_machine_validation_and_cost_guard

```sql
SELECT count(*) FROM capture_ai_runs
```

### TESTS-006 — backend/tests/test_capture.py:379 — callback

```sql
DELETE FROM sessions
```

### TESTS-007 — backend/tests/test_demo.py:16 — test_judge_accounts_are_private_idempotent_and_do_not_change_roles

```sql
SELECT * FROM users WHERE username='judge-tech'
```

### TESTS-008 — backend/tests/test_demo.py:19 — test_judge_accounts_are_private_idempotent_and_do_not_change_roles

```sql
SELECT count(*) FROM users
```

### TESTS-009 — backend/tests/test_demo.py:20 — test_judge_accounts_are_private_idempotent_and_do_not_change_roles

```sql
SELECT count(*) FROM machines
```

### TESTS-010 — backend/tests/test_demo.py:21 — test_judge_accounts_are_private_idempotent_and_do_not_change_roles

```sql
UPDATE users SET role='technician' WHERE username='judge-supervisor'
```

### TESTS-011 — backend/tests/test_rag.py:35 — config

```sql
INSERT INTO knowledge_records VALUES (?,NULL,?)
```

### TESTS-012 — backend/tests/test_rag.py:38 — config

```sql
INSERT INTO knowledge_versions (id,record_id,revision,machine_id,title,symptom,content,kind,author,status,created_at) VALUES (?,?,1,?,?,?,?,?,?,?,?)
```

### TESTS-013 — backend/tests/test_rag.py:76 — test_retrieval_persists_chunks_vectors_fts_and_excludes_unapproved

```sql
SELECT count(*) FROM chunk_embeddings
```

### TESTS-014 — backend/tests/test_rag.py:78 — test_retrieval_persists_chunks_vectors_fts_and_excludes_unapproved

```sql
SELECT length(vector) FROM chunk_embeddings LIMIT 1
```

### TESTS-015 — backend/tests/test_rag.py:84 — test_retrieval_persists_chunks_vectors_fts_and_excludes_unapproved

```sql
SELECT count(*) FROM rag_fts WHERE rag_fts MATCH 'vibration'
```

### TESTS-016 — backend/tests/test_rag.py:90 — test_retrieval_persists_chunks_vectors_fts_and_excludes_unapproved

```sql
SELECT count(*) FROM knowledge_chunks WHERE version_id LIKE 'PRIVATE-%'
```

### TESTS-017 — backend/tests/test_rag.py:146 — test_revocation_excludes_cached_vectors

```sql
UPDATE knowledge_versions SET status='Revoked' WHERE machine_id='CNC-01' AND status='Approved'
```

### TESTS-018 — backend/tests/test_rag.py:161 — test_superseded_source_excluded

```sql
INSERT INTO knowledge_versions (id,record_id,revision,machine_id,title,symptom,content,kind,author,status,created_at) SELECT 'SOP-001-v2',record_id,2,machine_id,title,symptom,'New unreviewed version',kind,author,'Pending',created_at FROM knowledge_versions WHERE id='SOP-001-v1'
```

### TESTS-019 — backend/tests/test_rag.py:173 — handler

```sql
UPDATE knowledge_versions SET status='Revoked' WHERE id='SOP-001-v1'
```

### TESTS-020 — backend/tests/test_rag.py:280 — test_new_approval_is_indexed_on_next_query

```sql
UPDATE knowledge_versions SET status='Approved' WHERE id='SUB-005-v1'
```

### TESTS-021 — backend/tests/test_speech.py:179 — test_speech_api_auth_csrf_validation_and_no_knowledge_write

```sql
SELECT count(*) FROM knowledge_records WHERE owner_id IS NOT NULL
```

### TESTS-022 — backend/tests/test_speech.py:184 — test_speech_api_auth_csrf_validation_and_no_knowledge_write

```sql
SELECT count(*) FROM source_documents
```

### TESTS-023 — backend/tests/test_speech.py:211 — transcribe

```sql
DELETE FROM sessions
```

### TESTS-024 — backend/tests/test_storage.py:119 — test_session_expiry_and_hashed_storage

```sql
SELECT token_hash FROM sessions
```

### TESTS-025 — backend/tests/test_storage.py:121 — test_session_expiry_and_hashed_storage

```sql
SELECT password_hash FROM users
```

### TESTS-026 — backend/tests/test_storage.py:123 — test_session_expiry_and_hashed_storage

```sql
UPDATE sessions SET expires_at=?
```

### TESTS-027 — backend/tests/test_storage.py:275 — test_upload_validation_and_rollback

```sql
SELECT count(*) FROM knowledge_records WHERE owner_id IS NOT NULL
```

### TESTS-028 — backend/tests/test_storage.py:286 — test_migration_and_seed_are_idempotent

```sql
SELECT count(*) FROM machines
```

### TESTS-029 — backend/tests/test_storage.py:287 — test_migration_and_seed_are_idempotent

```sql
SELECT count(*) FROM knowledge_records
```

### TESTS-030 — backend/tests/test_storage.py:288 — test_migration_and_seed_are_idempotent

```sql
SELECT count(*) FROM schema_migrations
```

### TESTS-031 — backend/tests/test_storage.py:289 — test_migration_and_seed_are_idempotent

```sql
PRAGMA foreign_key_check
```

## Coverage and interpretation

Total: 71 application call sites and 31 test call sites. Counts include transaction/PRAGMA statements and the dynamic migration executor; repeated SQL is intentionally retained at each source location. Runtime scripts use these modules; raw SQL search found no additional application SQL engine.

Inventory contains source literals only, with no bound parameter values. Data rows, password hashes, session tokens, model outputs, private environment files and existing SQLite databases were not accessed.
