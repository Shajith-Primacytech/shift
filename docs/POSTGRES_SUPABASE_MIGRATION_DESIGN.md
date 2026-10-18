# SHIFT PostgreSQL / Supabase migration design

Design baseline · 2026-10-18 · local implementation progress is recorded in [POSTGRES_PHASE2_REPORT.md](POSTGRES_PHASE2_REPORT.md). The SQL inventory remains the original pre-implementation source snapshot.

Target supplied by the user: the existing SHIFT Supabase project, PostgreSQL 17, Singapore. Project identity, minor version, extension version, existing objects, exposed schemas, usage and connection limits have **not** been inspected or verified. No Supabase connection, SQL execution, secret access, configuration change or database migration was performed. Only this design and its source inventory were created.

## 1. Recommended scope and boundaries

Add PostgreSQL as an explicit, optional persistence implementation behind FastAPI. Keep SQLite as the default, retain the existing SQLite migrations, and keep the prepared local demo on its existing path and settings. Do not silently fall back from an unavailable PostgreSQL database to SQLite: that would create divergent histories and potentially stale approval decisions.

Keep SHIFT authentication, not Supabase Auth: scrypt passwords, database-backed opaque sessions, technician/supervisor roles and secure same-origin cookies. Keep all browser traffic through the existing FastAPI contracts. Use PostgreSQL through a backend-only database role, not browser Supabase clients or the Data API. No frontend Supabase key, service-role key, JWT integration or new frontend URL is needed.

Use the unexposed application schema `shift_private`. Do not modify Supabase's `auth`, `storage`, `realtime`, `public` or other applications' objects. Do not change the existing project's exposed-schema configuration globally. Verify that the new schema is unexposed before any future hosted rollout.

Keep MiniLM embeddings and Whisper on the FastAPI host, and AMD calls in the existing adapter. PostgreSQL changes persistence and retrieval execution; it does not supply Python model hosting or remove backend RAM, temporary disk, audio decoding or inference requirements.

## 2. Inventory and existing invariants

[SQLITE_SQL_INVENTORY.md](SQLITE_SQL_INVENTORY.md) contains all three SQL migration files verbatim, their SHA-256 hashes, the bootstrap table, dynamic query fragments, and every database execution call site: **71 in application code and 31 in tests**. SQL parameter values are not included. This is a source inventory, not an inspection of any existing database; drift and data quality remain future preflight checks.

There are **16 logical SQLite objects**: 14 ordinary tables declared in migrations, one FTS5 virtual table, and one startup-created migration table. FTS5's five shadow tables are derived implementation details and must not be copied to PostgreSQL.

| Migration / bootstrap | Objects |
| --- | --- |
| `001_storage.sql` | users, sessions, login_attempts, machines, knowledge_records, knowledge_versions, review_events, source_documents, knowledge_chunks, conversations, conversation_messages; three explicit indexes |
| `002_rag.sql` | rag_generations, chunk_embeddings, rag_fts virtual table |
| `003_capture_ai.sql` | capture_ai_runs and owner/time index |
| `storage/database.py` | schema_migrations; ordered, transactional, once-only migration application and idempotent synthetic seed |

Existing behavior that must survive:

- Users are identified by text IDs; usernames are normalized by Python, passwords salted/hashed with scrypt. The browser cannot assign its role. Authentication reads users and hashed, expiring sessions; login failures are persisted and explicitly committed even when the response is an error.
- Production `shift_session` cookies are HttpOnly, Secure, SameSite=Lax, path `/`; logout removes the token hash. Authentication is rechecked after slow capture, speech and troubleshooting operations. Keep the request-origin allowlist and mandatory `X-Shift-Request: 1` on writes.
- Technicians see their own submissions/history; supervisors see the queue/history. Technicians cannot revise another technician's record. Supervisors may revise another record but cannot approve their own record **or their own revision of somebody else's record**.
- A new submission/revision is Pending. The maximum revision is authoritative immediately, including when Pending or Rejected: do not fall back to an older Approved revision. The old version, old documents and old review events remain available through privileged history access.
- Review transitions: Pending → Approved or Rejected; Approved → Revoked. A stale version/status produces 409. Rejection/revocation require a reason. Status update and append-only review event must commit together. Review IDs determine event order.
- Documents are downloadable by the owner or a supervisor, or by another authenticated user only when attached to the latest Approved version. Fail with the existing 404 behavior instead of revealing unauthorized document existence.
- Capture writes an interrupted receipt before inference, commits the result separately, and checks session freshness afterwards. A submitted AI run must belong to the actor, have successful execution, match the original source fields, be explicitly reviewed, and be unused. The reviewed fields are mapped into the existing knowledge fields; the result still needs supervisor approval.
- RAG eligibility is latest revision AND Approved AND selected machine AND current embedding key. Cached vectors do not grant access. The written source fingerprint and exact chunk hash are checked before and after inference. Source/passages must be exact quotes, and source order is preserved. Empty or unsafe scopes abstain without calling AMD.
- Attachments are stored as BLOBs with name/type/size/SHA-256. Allowed extensions, four-file limit, nonempty 10 MiB per-file limit, 42 MiB middleware limit and safe response headers remain unchanged. Attachments are not automatically parsed into RAG evidence; only the existing approved written-record text is indexed.
- Conversations/messages exist in schema but have no application read/write queries today. Preserve them in migration coverage; do not invent an API for them.

## 3. Complete target schema mapping

Legend: PK = primary key; NN = NOT NULL; FK = foreign key. All target objects live in `shift_private`; all identifiers remain **text**, including 32-hex user IDs, synthetic IDs, `SUB-...`, version IDs and chunk IDs. Do not coerce these to UUID. Text identifiers and username uniqueness use a deterministic case-sensitive collation (e.g. `C`) consistent with existing normalized values.

Unless explicitly noted, carry every source NN/default/unique/FK/check constraint from the inventory. FK delete/update actions remain NO ACTION; only the existing embedding→chunk FK cascades on deletion. PostgreSQL PK columns are necessarily NN: SQLite rowid-table TEXT PKs can admit NULL, so future data preflight must detect and reject NULL IDs rather than silently changing them.

### All columns, target types, keys and constraints

| Table | Target columns and constraints |
| --- | --- |
| `schema_migrations` | `version text PK`. A **new PostgreSQL-specific** ledger, not copied SQLite applied filenames. Extend this new ledger with `checksum text NN`, `applied_at timestamptz NN DEFAULT clock_timestamp()` for PostgreSQL migration verification. |
| `users` | `id text PK`; `username text NN UNIQUE`; `name text NN`; `role text NN CHECK (role IN ('technician','supervisor'))`; `password_hash text NN`; `created_at text NN`. |
| `sessions` | `token_hash text PK`; `user_id text NN FK users(id)`; `expires_at bigint NN` (same epoch-second representation). |
| `login_attempts` | `key text NN`; `attempted_at bigint NN` (epoch seconds). Preserve absence of a PK; repeated attempts in the same second must not be deduplicated. |
| `machines` | `id text PK`; `data jsonb NN` (source TEXT contains JSON). |
| `knowledge_records` | `id text PK`; `owner_id text NULL FK users(id)` (synthetic seeds legitimately have NULL owners); `created_at text NN`. |
| `knowledge_versions` | `id text PK`; `record_id text NN FK knowledge_records(id)`; `revision integer NN`; `machine_id text NN FK machines(id)`; `title text NN`; `symptom text NN`; `content text NN`; `kind text NN`; `author text NN`; `submitted_by text NULL FK users(id)`; `problem text NN DEFAULT ''`; `root_cause text NN DEFAULT ''`; `resolution text NN DEFAULT ''`; `safety_notes text NN DEFAULT ''`; `status text NN CHECK (status IN ('Pending','Approved','Rejected','Revoked'))`; `created_at text NN`; UNIQUE (`record_id`,`revision`). |
| `review_events` | `id bigint GENERATED BY DEFAULT AS IDENTITY PK`; `version_id text NN FK knowledge_versions(id)`; `reviewer_id text NULL FK users(id)`; `reviewer_name text NN`; `previous_status text NN`; `decision text NN`; `note text NN`; `created_at text NN`. Nullable seed reviewers and the exact previous-status/audit text are retained. |
| `source_documents` | `id text PK`; `version_id text NN FK knowledge_versions(id)`; `name text NN`; `media_type text NN`; `size bigint NN`; `sha256 text NN`; `data bytea NN`; `created_at text NN`. |
| `knowledge_chunks` | `id text PK`; `version_id text NN FK knowledge_versions(id)`; `document_id text NULL FK source_documents(id)`; `position integer NN`; `page integer NULL`; `section text NULL`; `content text NN`; `content_hash text NN`; **new derived** `search_vector tsvector GENERATED ALWAYS AS (to_tsvector('pg_catalog.simple'::regconfig, content)) STORED`. |
| `conversations` | `id text PK`; `owner_id text NN FK users(id)`; `machine_id text NN FK machines(id)`; `created_at text NN`. |
| `conversation_messages` | `id text PK`; `conversation_id text NN FK conversations(id)`; `role text NN CHECK (role IN ('user','assistant'))`; `content text NN`; `response_mode text NN`; `created_at text NN`. |
| `rag_generations` | `version_id text PK FK knowledge_versions(id)`; `fingerprint text NN`; `embedding_key text NN`. |
| `chunk_embeddings` | `chunk_id text PK FK knowledge_chunks(id) ON DELETE CASCADE`; `embedding_key text NN`; `vector extensions.vector(384) NN`, assuming the existing vector extension is installed in `extensions` (verify, do not move a shared extension). |
| `rag_fts` | **No physical PostgreSQL table.** Replace its redundant content/index with `knowledge_chunks.search_vector` plus GIN. Its chunk/version/content data already exists in chunks. |
| `capture_ai_runs` | `id text PK`; `owner_id text NN FK users(id)`; `original_submission jsonb NN`; `proposal jsonb NULL`; `execution jsonb NN`; `created_at text NN`; `version_id text NULL UNIQUE FK knowledge_versions(id)`; `reviewed_structure jsonb NULL`. Preserve SQL NULL separately from JSON null in import/export. |

### Deliberate compatibility decisions

Keep existing `created_at` fields as TEXT with deterministic ordering in this first migration. SQLite seeds contain date-only strings while runtime writes UTC ISO strings, and serializers slice/return those exact strings. Blind conversion to timestamptz changes API date representations and cutoff comparisons. Keep `now()` serialization and the capture cutoff in the same canonical UTC ISO form. A later native-timestamp migration can add a parsed timestamp alongside original text after API normalization is approved; do not conflate it with backend compatibility work. New infrastructure-only lease/migration times may use timestamptz.

Use native JSONB for JSON documents. The PostgreSQL repository returns Python mappings/JSON values; remove `json.loads()` assumptions at the repository boundary, not in frontend contracts. JSON key ordering/spacing is not an API guarantee. Reject invalid JSON, duplicate-key ambiguities or PostgreSQL-incompatible NUL/unpaired-surrogate strings during a future import instead of silently rewriting data. Compare decoded source structures, not serialized JSON bytes, for AI run reuse checks. Do not use JSONB encoding to calculate written-text evidence fingerprints.

Keep text CHECK constraints instead of introducing enums for existing roles/statuses. Do not invent source DB constraints for `kind`, review decision/history strings or previously nullable fields. Candidate hardening checks (`revision > 0`, positive document size, `size=octet_length(data)`, hash format) need explicit validation and review before adoption, and must not reject accepted synthetic fixtures.

Identity audit IDs must be imported explicitly and their sequence advanced beyond MAX(id) before writes resume. Gaps are valid. Preserve per-version event order and tie handling; concurrent independent record reviews do not require global commit order from the identity sequence.

### Index inventory and target indexes

Existing explicit indexes:

1. `login_attempt_time(key, attempted_at)` → retain the composite B-tree.
2. `versions_record(record_id, revision)` → its access path is already covered by UNIQUE(record_id,revision); omit a duplicate target index unless EXPLAIN justifies a different order.
3. `versions_status(status, machine_id)` → retain initially.
4. `capture_ai_owner_time(owner_id, created_at)` → retain, ordered consistently with cutoff queries.

Existing implicit indexes: all declared PKs; `users.username` unique; `(record_id,revision)` unique; `capture_ai_runs.version_id` unique (ordinary PostgreSQL UNIQUE preserves multiple NULL values). `login_attempts` has no unique index. FTS5 indexes are replaced, not copied.

Proposed PostgreSQL additions, reviewed against plans and measured size:

- `sessions(expires_at)` for expiry cleanup and `sessions(user_id)` for FK/administration.
- `login_attempts(attempted_at)` for global old-attempt cleanup; the existing composite index starts with key.
- `knowledge_records(owner_id)`; `knowledge_versions(machine_id)` if the existing status/machine index is insufficient for the FK; `knowledge_versions(submitted_by)` if needed for FK maintenance.
- `review_events(version_id, id DESC)` for latest review/history; `review_events(reviewer_id)` for FK operations if warranted.
- `source_documents(version_id)`; `knowledge_chunks(version_id)`; `knowledge_chunks(document_id)` for lookups/FKs/deletes.
- GIN on `knowledge_chunks(search_vector)`.
- `chunk_embeddings(embedding_key)` only if plans justify it; PK joins plus version/machine filtering may suffice initially.
- Dormant conversation FK indexes when migrating populated conversations: `conversations(owner_id)`, `(machine_id)`, `conversation_messages(conversation_id)`.
- Do not build HNSW or IVFFlat in the first phase. Exact scoped search is sufficient for the synthetic corpus and avoids ANN recall changes/index memory costs.

PostgreSQL does not automatically index referencing FK columns. Each optional index is a capacity tradeoff, not permission to create every listed index without measurement. FK/PK constraints and the eligibility query remain correctness controls even where indexes are deferred.

## 4. PostgreSQL full-text and vector retrieval

Keep model ID, pinned revision, normalization, 180-token chunks, 25-token overlap, 384 dimensions, embedding key, candidate counts, 0.35 semantic gate and reciprocal-rank fusion constant 60. Carry the existing application `terms()` stop list and its 32-term cap; terms are normalized ASCII alphanumeric tokens, not raw tsquery syntax.

Design-only SQL fragments, not an executable migration:

```sql
-- Assumes the extension is already installed in the reviewed extensions schema.
vector extensions.vector(384) NOT NULL

-- Column on shift_private.knowledge_chunks:
search_vector tsvector GENERATED ALWAYS AS
  (to_tsvector('pg_catalog.simple'::regconfig, content)) STORED

-- Corresponding lexical match/ranking expressions:
c.search_vector @@ to_tsquery('pg_catalog.simple'::regconfig, %s)
ts_rank_cd(c.search_vector, to_tsquery('pg_catalog.simple'::regconfig, %s))

-- Similarity, using a bound vector, with exact cosine search:
1 - (e.vector OPERATOR(extensions.<=>) %s::extensions.vector(384))
```

Build the OR tsquery from validated `terms()` output (`token1 | token2`), and bind it. Do not feed raw user syntax to `to_tsquery` and do not replace OR retrieval with default AND behavior. `simple` avoids English stemming that would change the existing lexical gate; punctuation, accents, case and tokenization still differ from FTS5 unicode61. PostgreSQL rank is **not** SQLite BM25. Preserve gating/fusion algorithms, but treat lexical ranking differences as an explicit quality change requiring the synthetic retrieval evaluation, never claim score equivalence.

Initial algorithm:

1. Check for eligible written records in the selected machine before loading an embedding model or calling AMD. Keep query token-length rejection before embedding truncation.
2. Synchronize only current approved versions. Compute embeddings without an open write transaction. Under the record's transaction lock, re-read eligibility and written fingerprint before replacing chunks/embeddings/generation atomically. Generated FTS stays synchronized with chunk insertion/deletion automatically.
3. For the small corpus, get all eligible chunks and exact cosine scores in the selected machine/key. Apply the existing Python meaningful-term-overlap gate and 0.35 threshold before selecting each branch's top 20. Do not apply a premature LIMIT that loses eligible lexical or semantic candidates. Filter the lexical branch to the same semantically eligible set, then retain its top 20 by PostgreSQL rank and deterministic chunk-ID tiebreak.
4. Fuse the two ordered candidate lists with the current RRF algorithm and take five. Return the same LlamaIndex TextNode/NodeWithScore metadata, citations and original text.
5. Fresh, parameterized, machine-scoped database checks must verify latest/Approved state, source fingerprint, version/chunk relationship and chunk content hash before and after AMD selection. Batch these checks into one statement per phase where practical for one coherent snapshot. Missing/mismatched evidence rejects the **entire** answer as today; do not partly serve stale evidence.

Do not upload SQLite float32 bytes directly into vector. Decode using the original float32 representation/endian convention, require exactly 384 finite values, reject zero norm, and bind via the Python pgvector adapter. Native pgvector values have float32 precision. Test cosine score drift (target <=1e-6 on synthetic fixtures); explicitly recalculate threshold/tie-boundary cases with the existing NumPy routine if needed to preserve the gate. Do not change the threshold to hide differences.

Keep `rag_generations.embedding_key` and `chunk_embeddings.embedding_key` coherent and verify both during retrieval. Upsert the generation row with `ON CONFLICT(version_id) DO UPDATE`, not replacement/delete semantics. A model/key change triggers reindexing; it must not mix embeddings from different models.

Keep `/knowledge?q=` as literal substring search. Translate SQLite `instr()` to bound PostgreSQL `strpos()`, not LIKE/ILIKE (which treats `%` and `_` as patterns), and do not silently turn that endpoint into full-text search. SQLite built-in `lower()` is ASCII-focused: use an explicit ASCII folding helper/`translate()` expression for parity rather than assuming locale-aware PostgreSQL `lower()` behaves identically. Test non-ASCII names/content and literal `%`, `_`, quotes and backslashes.

## 5. Adapter and FastAPI integration

Proposed modules (development tasks, not files created in this draft):

- `storage/contracts.py`: Store/UnitOfWork interfaces and row/domain DTOs; no `sqlite3.Connection` in public service signatures.
- `storage/sqlite_store.py`: existing connection/SQL behavior isolated behind the interfaces; continue using existing migrations and default paths.
- `storage/postgres_store.py`: Psycopg 3 pool, dictionary rows, typed JSONB/bytea/vector adapters and PostgreSQL-specific statements.
- `storage/factory.py`: explicit configured backend choice; lazy-load PostgreSQL dependencies only when selected.
- Repositories for authentication, knowledge/documents/reviews, AI run receipts and RAG indexing/retrieval. Methods encode purpose (e.g. `latest_approved`, `own_or_supervisor_history`, `claim_reviewed_run`), not arbitrary browser-provided SQL.

Use pinned optional `postgres` dependencies (`psycopg`, pooling support and Python pgvector adapter) and update lockfiles only during implementation. No Supabase JavaScript/Python Auth SDK is required. Keep SQL in dialect-specific repositories; **do not implement a string-replacement SQLite-to-PostgreSQL shim**.

Routes and services retain URLs, request/response bodies, status codes, validation messages, cookie behavior, multipart handling and AMD/speech providers. Replace direct SQL dependencies in `api/storage.py`, `api/capture.py`, `api/troubleshooting.py`, `api/speech.py`, `storage/security.py`, `rag/retrieval.py`, `rag/service.py`, preparation/provisioning CLIs and test fixtures. RAG currently passes a database path through its constructors and `valid_evidence`; replace that internal parameter with a store dependency while retaining the external API. Administrative scripts must select the correct backend explicitly and refuse to run a production seed by accident.

Avoid blocking the event loop with synchronous PostgreSQL network I/O. A practical low-change implementation is synchronous repository units executed in FastAPI threadpool functions. Each unit acquires/releases its own connection; never share a mutable connection between concurrently running threads, or pass a request connection into an embedding worker. Do not mechanically hold one pooled connection for the entire async request.

Codec rules: JSONB ↔ Python JSON values; bytea/memoryview ↔ bytes; vector ↔ validated float32 array; identity IDs ↔ integers; timestamps/epochs ↔ the existing API formats. `fetchone()[0]` callers become named/scalar repository results, not dict-row positional indexing. Every INSERT gets explicit columns. Serialize/materialize API results before leaving the unit, but send a success/cookie only after the transaction has committed successfully. Map database errors to sanitized domain errors; never return a DSN, parameter dump or raw driver diagnostic.

### Proposed configuration, not production changes

| New setting | Proposed meaning |
| --- | --- |
| `SHIFT_STORAGE_BACKEND` | `sqlite` by default; optional explicit `postgres`. Existing settings continue working without it. |
| `SHIFT_POSTGRES_DSN` | Backend-only SecretStr; required only for explicit PostgreSQL selection. Never printed or included in frontend env. Obtain the real custom-role endpoint through a private administrative workflow later; do not compose an assumed regional pooler hostname. |
| `SHIFT_POSTGRES_SSLROOTCERT` | Reviewed CA path used with `sslmode=verify-full`; enforce certificate and hostname verification for hosted connections. |
| `SHIFT_POSTGRES_POOL_MAX` | Initial design cap 4 total connections per process, min 0; tune only within the actual existing project's remaining budget. |
| `SHIFT_POSTGRES_CONNECT_TIMEOUT` | Proposed 5 seconds; bounded checkout/wait time separately. |

Keep schema name fixed/allowlisted in source, not a raw SQL-interpolated environment value. Existing `SHIFT_DATABASE_PATH` is SQLite-only and unchanged. Existing frontend backend URL/CORS/security/model configuration is unchanged. No new settings should be added to the live environment as part of design review.

## 6. Private schema, roles and least privilege

Use a NOLOGIN `shift_owner` to own only the new schema/objects, a controlled migration identity able to act as that owner, a separate provisioning/import identity, and a runtime LOGIN `shift_runtime` with no ownership, superuser, CREATEDB, CREATEROLE, replication or BYPASSRLS. Do not give runtime membership in owner/admin or Supabase service roles. Bootstrap roles/extensions only in a future approved administrative step.

Revoke schema/object access to the new schema from PUBLIC, anon and authenticated, review inherited grants, and keep default privileges for new SHIFT objects private. Grant runtime only schema USAGE, exact table/column operations and sequence USAGE where needed. No schema CREATE, TRUNCATE, DDL, migration-ledger writes or blanket GRANT ALL. Do not globally revoke public-schema privileges in an existing shared project.

| Object | Runtime privileges |
| --- | --- |
| users | SELECT only on required authentication/profile columns. Provisioning, not runtime, creates users or changes passwords/roles. |
| sessions, login_attempts | SELECT, INSERT, DELETE; no UPDATE required. |
| machines | SELECT only; seeding is an administrative operation. |
| knowledge_records | SELECT, INSERT; no UPDATE/DELETE. Record-level transaction advisory locks avoid granting an otherwise unnecessary UPDATE just to lock a parent row. |
| knowledge_versions | SELECT, INSERT, UPDATE **only status**; immutable source/revision/ownership columns cannot be updated by runtime. |
| review_events | SELECT, INSERT and sequence USAGE; no UPDATE/DELETE. |
| source_documents | SELECT, INSERT; no UPDATE/DELETE. |
| knowledge_chunks, chunk_embeddings | SELECT, INSERT, DELETE for atomic reindexing; generated FTS column cannot be written directly. |
| rag_generations | SELECT, INSERT, UPDATE fingerprint/embedding_key. |
| capture_ai_runs | SELECT, INSERT, UPDATE proposal/execution/version_id/reviewed_structure only. Original source/owner/time remain immutable. |
| schema_migrations, conversations, conversation_messages | No runtime grants initially; separate migration/import role handles dormant data. Add only required capabilities if an actual feature is introduced. |

Enable RLS on the new tables as defense in depth, with explicit operation-specific policies TO the custom runtime/provisioning roles matching the grant matrix. For this **server-only adapter**, these are service capability policies, not Supabase end-user policies: the trusted FastAPI runtime needs authentication lookup access before knowing an actor, and RAG needs approved evidence across owners. They do **not** replace ownership/role/eligibility predicates in repository methods. Anonymous/authenticated Supabase roles have neither grants nor policies. Do not add a blanket `FOR ALL` policy to every table or claim that `auth.uid()` represents a SHIFT session.

The first adapter deliberately preserves today's trusted-backend authorization boundary. Compromise of its database credential is not isolated per technician. True per-user database RLS would require a separate design for verified SHIFT-session actor context, bootstrap auth tables, recursive latest-version policies and context cleanup on pooled connections. Do not improvise this with a browser-supplied user ID/role GUC. This limitation must be accepted explicitly during review; it is not concealed by enabling RLS.

Keep business SQL in the application. Any helper/view is schema-qualified and SECURITY INVOKER; PostgreSQL 17 views must use `security_invoker=true` if introduced. No public RPC or SECURITY DEFINER bypass. If internal functions are later introduced, revoke default PUBLIC EXECUTE and grant only required callers; do not alter privileges on unrelated existing project functions. Pin a safe search_path and qualify extension operators/types; only trusted schema owners may create referenced objects.

## 7. Concurrency and transaction design

SQLite `BEGIN IMMEDIATE` obtains a database writer lock. PostgreSQL `BEGIN` does not: READ COMMITTED plus explicit application locks and conditional writes is the proposed baseline. Use one documented advisory-lock key derivation (namespaced, stable 64-bit PostgreSQL hash of bound text), with `pg_advisory_xact_lock` or bounded try-lock behavior. Hash collisions serialize unrelated work but do not grant access. All mutating adapters/CLIs must use the same lock protocol; uniqueness/FK constraints remain independent backstops.

| Operation | PostgreSQL transaction protocol |
| --- | --- |
| Revision | Validate/read upload bytes outside transaction. Start short transaction; acquire per-record transaction advisory lock; re-read ownership and current MAX(revision); insert MAX+1 Pending version, AI binding and attachments together. UNIQUE(record_id,revision) backs the allocation. |
| Review/revoke | Same record advisory lock as revisions and indexing; re-read latest revision/actor/status; conditional status UPDATE with expected version/status, requiring one affected row; append one audit event; commit. Second conflicting reviewer gets 409 rather than duplicate events. |
| AI run attachment | After record lock, lock the run row FOR UPDATE or perform a conditional `UPDATE ... WHERE id/owner match AND version_id IS NULL ... RETURNING`; verify successful execution and source equality under the lock; bind once in the submission transaction. If linking fails, roll back the version and all attachments. Never overwrite a prior binding. |
| Login rate limit | Per-normalized-client/username advisory transaction lock, then expiry cleanup/count/attempt or session changes. Preserve five failures/15 minutes and committed failed-attempt state. Error-return flow must not roll back the security counter. This closes count-and-insert races across clients/processes. |
| Capture cooldown | Per-owner advisory transaction lock; test the 30-second receipt cutoff and insert interrupted receipt atomically; commit before AMD. Update the receipt in a separate short transaction after inference. No automatic replay of the AMD operation on a DB retry. |
| RAG sync | Build vectors outside transactions. Acquire the same record lock, recheck latest/status/fingerprint, replace derived rows and generation atomically. Do not remove durable source/history rows. |
| Evidence validation | Use fresh committed-state reads before and after inference. Do not reuse a long REPEATABLE READ snapshot, cached approval flags, or an ORM identity cache. Final validation's snapshot is the freshness boundary; revocation after that boundary cannot be prevented during network delivery, matching the existing practical guarantee. |
| Session recheck | Reacquire a connection and re-read the hashed session against current expiry after slow work. Do not retain the initial authentication result as final authorization. |

Lock order: acquire any operation-specific login/cooldown lock separately; for content writes acquire record keys in sorted order, then the relevant version/run locks consistently. Do not take record locks while holding a feature-wide long-lived DB transaction. Use lock_timeout, statement_timeout, bounded pool wait and idle-in-transaction timeout; proposed initial budgets are 2 seconds lock wait and 10 seconds DB statements, validated against synthetic binary uploads. These are **DB** budgets, not replacements for AMD/Whisper deadlines.

Retry only proven-rolled-back, database-only transactions for deadlock/serialization failures, bounded (e.g. two retries with jitter). Never replay inference, transcription, an ambiguous committed submission or an uncertain commit acknowledgment. Do not mask unique violations blindly: re-read to distinguish an allocation race from corruption; preserve the existing conflict/error contract.

Keep the initial deployment at one process/worker, retaining existing feature busy locks and 429 behavior. PostgreSQL persistence alone does not make CPU/model jobs or AMD spending globally serialized. Before any multiworker/replica rollout, introduce and test bounded persistent feature leases with expiry, heartbeat and fencing tokens (in a new private table), or an explicit queue. Do not hold session advisory locks or a database transaction through AMD/Whisper as a shortcut. This later scale-out work is out of the first migration.

### Pooling and region

For the existing long-lived backend, prefer a small Psycopg pool over a direct connection when IPv6 is available. For an IPv4-only host, use Supabase's shared **session** pooler rather than purchasing IPv4. Get the actual endpoint and custom-role username from the project's connection workflow; Singapore does not uniquely determine the hostname.

If transaction pooling is deliberately selected later, disable Psycopg automatic named preparation (`prepare_threshold=None`), avoid pipelining and all cross-transaction session state, and use transaction-local settings/locks. Register vector codecs using the verified type metadata without assuming connection session affinity. Migrations/backups use a suitable direct or tested session connection, not transaction mode. Hosted connections require TLS hostname verification and the proper CA. A failed TLS check must not downgrade security.

Pool capacity multiplies by processes, replicas, CLIs and separate pool objects. Share one application pool per process; count Supabase's existing services and other applications before allocating a cap. Keep transactions/connections closed during model loading, encoding, HTTP waits and transcription. Pool exhaustion must yield a bounded sanitized unavailable response, never a fallback write to SQLite.

## 8. Attachment and data migration plan

Phase one keeps `source_documents.data` in PostgreSQL **bytea**. No Supabase Storage bucket, public URL, signed URL or authorization rewrite is needed. Preserve document IDs, version links, names, media types, byte lengths, SHA-256 and exact bytes. The endpoint still emits bytes with application/octet-stream, Content-Disposition and nosniff. Do not base64-encode data into JSON or use PostgreSQL large-object OIDs.

Migration tooling is a future task. Initially exercise only a newly generated synthetic SQLite fixture (not the working demo database) and a disposable local PostgreSQL 17 + pgvector database. The extractor must accept an explicit source and destination, reject the known demo/live paths by default, never load the normal `.env`, and never discover a hosted DSN automatically. No existing SQLite database is to be opened or copied during this design work.

For any later authorized import, work from a consistent private snapshot, not a raw copy of a live WAL file. Preserve originals; use SQLite's backup API in a separately authorized capture step and then open only the snapshot read-only. Stream rows/documents in bounded batches and insert bytes as binary parameters or COPY; do not hold the entire corpus in memory or log payloads. Validate all input before enabling target writes. Never disable constraints to make an invalid load pass.

Load dependency order:

1. PostgreSQL ledger/DDL, users and machines.
2. knowledge_records, then all knowledge_versions.
3. review_events and source_documents.
4. conversations, then conversation_messages.
5. capture_ai_runs (now both owner and optional version references exist).
6. knowledge_chunks, then chunk_embeddings and rag_generations; regenerate search_vector/GIN instead of copying rag_fts or shadow tables.
7. Synthetic login_attempts/sessions only for explicit compatibility tests. A later real cutover should require reauthentication and omit active sessions by reviewed policy; never recreate a plaintext token from its hash. Preserve existing password-hash strings byte-for-byte, not rehash without the password.
8. Advance review identity sequence, analyze, validate counts/relationships/hashes/eligible scopes and produce a redacted migration manifest. Keep SQLite migration provenance in the report, not as applied PostgreSQL migrations.

Import all immutable history, including Pending/Rejected/Revoked and superseded rows. Do not index them as eligible evidence. Validate decoded vectors and embedding keys; rebuild inconsistent derived data from approved written text, never silently treat malformed vectors as valid. Import jobs are restartable into an isolated staging schema/database with checksums and explicit conflict verification; do not use broad `ON CONFLICT DO NOTHING` to conceal mismatches.

Supabase Storage is a possible later phase only if bytea capacity proves insufficient. It requires a private bucket, object checksum/size verification, the existing download-authorization gate, and a recoverable object/DB consistency protocol. It is not part of phase-one compatibility and must not be sold as a free drop-in fix.

## 9. SQL conversion checklist

- [ ] Inventory ledger covers all 71 app and 31 test execution sites; classify each as retain, dialect conversion, repository replacement, or SQLite-only. Keep dynamic LATEST and ELIGIBLE identical in meaning.
- [ ] Separate PostgreSQL migrations/ledger from SQLite startup scripts. Existing `001`–`003` files stay untouched. PostgreSQL runtime startup validates schema compatibility without DDL/seeding privileges; migration runner serializes itself and records checksums. Provisioning is explicit.
- [ ] Replace SQLite `?` with bound Psycopg `%s`; do not interpolate parameters or perform global text substitution. Static table/column names come from reviewed code.
- [ ] Add explicit INSERT columns everywhere, including 16-column knowledge versions, users, machines, sessions, source_documents and embedding/generation rows.
- [ ] Replace `BEGIN IMMEDIATE` using the reviewed transaction/locking protocol. Remove PRAGMAs, filesystem mkdir/chmod and file paths from PostgreSQL initialization only.
- [ ] Replace implicit connection-lifetime transactions with deliberate units; preserve explicit login failure and capture receipt/result commits; handle PostgreSQL aborted transactions with rollback/savepoints before reuse.
- [ ] Replace `INSERT OR REPLACE` for generations with `ON CONFLICT ... DO UPDATE`. Preserve embedding ON DELETE CASCADE, all other NO ACTION relationships, and transactional rollback behavior.
- [ ] Replace FTS5 MATCH/bm25 and manual FTS deletes/inserts with generated tsvector/GIN and parameterized tsquery/rank. Do not migrate shadow tables or substitute AND for OR.
- [ ] Decode vector BLOBs into vector(384); enforce dimensions, finite/nonzero data, model-key coherence and approved-scope filtering before top-k.
- [ ] Convert BLOB → bytea; TEXT JSON → JSONB; identity review IDs → RETURNING where generated values are needed, and reseed identity after import. No `.lastrowid` dependency exists in current app SQL.
- [ ] Replace `instr(lower(...), lower(?))` with literal strpos plus compatible ASCII folding; keep concatenation NULL semantics and empty filters.
- [ ] Replace positional SQLite rows and json.loads/NumPy-frombuffer assumptions with explicit codecs/scalar results; preserve public JSON shapes, dates, byte responses and error codes.
- [ ] Check boolean results (`latest` becomes PostgreSQL boolean), numeric counts, MAX+1 scalar handling, NULL owners/reviewers/version bindings and UNIQUE multiple-NULL behavior.
- [ ] Preserve ordering and deterministic ties (revision, review IDs, timestamps, rank/chunk ID). Do not accidentally lexically sort version IDs instead of numeric revisions.
- [ ] Cover auth SELECT, session expiry/delete/insert, rate cleanup/count/insert, latest approved library/queue/history/document queries, revision/review writes, capture cooldown/receipt/claim/results, RAG synchronize/validate/candidates, admin user creation and seed queries.
- [ ] Review every new FK index, GIN index, privilege, RLS policy and implicit index; omit redundant indexes; use EXPLAIN only against disposable synthetic data during first implementation.
- [ ] Keep error diagnostics/DSNs/bound values out of logs. Do not use superuser/service-role credentials for normal tests or runtime.

## 10. Ordered development tasks

| Order | Deliverable | Gate before moving on |
| --- | --- | --- |
| 1 | Review this design: private service access boundary, timestamp compatibility, JSONB codecs, exact vector search and lexical-rank difference. | User accepts scope before implementation. No hosted changes implied. |
| 2 | Add isolated synthetic fixture generator, baseline API snapshots and migration-manifest validator; record demo-path exclusion. | No real/local-demo DB access; test environment must use explicit temporary paths and `_env_file=None`. |
| 3 | Extract repository/UoW interfaces and wrap SQLite behavior with no PostgreSQL requirement. | Existing SQLite backend/frontend suites pass with default configuration and no PG package/DSN. |
| 4 | Create **local-only**, separate PG17+pgvector migrations/role grants and a migration runner; pin optional driver dependencies. | Fresh/repeated local migration, runtime privilege-denial tests and checksum checks pass. Use the Supabase CLI's migration creation command when Supabase migration files are eventually introduced; no invented filenames or remote linking. |
| 5 | Implement PostgreSQL auth/profile/machine repositories and unit boundaries. | Password/session/cookie/CSRF/rate-limit parity; error commits survive. |
| 6 | Implement submissions, documents, histories, revisions, reviews and AI-run persistence/claiming. | API contract parity and concurrent state-transition tests; audit append-only permissions. |
| 7 | Implement PostgreSQL derived indexing, exact vector search, FTS/rank fusion and fresh evidence validation. | Retrieval evaluation passes; differences reviewed; no non-Approved evidence reaches prompts. |
| 8 | Implement bounded synthetic importer and reverse exporter/rollback rehearsal. | All counts/FKs/hashes/vector checks and identity sequence tests pass. |
| 9 | Run full dual-backend integration/browser tests and bounded storage/connection/load measurements locally. | Acceptance checklist below signed off; no inference credit required. |
| 10 | Prepare a redacted hosted preflight/cutover runbook for the existing Singapore project. | Separate authorization needed to inspect actual hosted metadata/apply SQL or change config. This task does not authorize those actions. |

The eventual hosted preflight must confirm project identity, PG17 minor version, installed vector extension namespace/version, schema collisions, actual free-plan capacity, inherited grants, Data API exposure and network/TLS/pool endpoints. An existing schema-name collision must stop rollout, not overwrite objects or silently choose a shared schema.

## 11. Synthetic tests and acceptance criteria

Run the current storage, demo, RAG, capture, speech and frontend workflow suites against the SQLite adapter and equivalent parameterized PostgreSQL tests. Preserve SQLite-specific PRAGMA/schema-ledger checks in the SQLite suite and add PostgreSQL catalog/constraint/privilege equivalents. Mock AMD and speech for automated acceptance; run local real MiniLM evaluation separately when prepared. No live AMD calls or hosted tests are necessary.

- [ ] Default startup without new variables still selects SQLite and does not import/connect to PostgreSQL; existing paths/demo data/config remain untouched. An explicit invalid PostgreSQL selection fails closed.
- [ ] Fresh PostgreSQL schema has every mapped column, source NN/default/check/unique/FK, expected identity behavior and reviewed indexes. Invalid FK, duplicate username/revision/version binding and invalid role/status are rejected.
- [ ] SQLite→PostgreSQL synthetic import preserves row counts (FTS derived objects accounted separately), IDs, relationships, exact source text, nulls, status/revision history, password hashes and document bytes/SHA-256. JSON values round-trip semantically; timestamp strings round-trip exactly.
- [ ] API request/response schemas, error status codes, dates, cookies and document headers match baseline snapshots after normalizing intentionally nondeterministic IDs/tokens/times.
- [ ] Invalid credentials and missing/expired/logged-out sessions fail; raw passwords/tokens never persist. Production cookie flags and origin/header checks remain unchanged. Five concurrent failed attempts cannot bypass the persisted throttle.
- [ ] Other technicians cannot see/revise private histories, pending records or restricted documents; own/supervisor access survives. Self-approval and supervisor-own-revision approval fail. Missing authorization does not become a distinguishable existence oracle.
- [ ] Two simultaneous revisions serialize into unique increasing revisions with no partial attachments; stale review races produce one event and one conflict. Approval versus revision races leave only the actual latest Approved version eligible. Revocation preserves history and immediately excludes cached evidence.
- [ ] Two submissions claiming one AI run yield one successful binding, with no orphan version/documents on the loser. Changed original source, another owner's run, failed/unreviewed/previously bound run are rejected. Parallel cooldown checks permit one receipt. Crash after receipt keeps an interrupted, non-submittable run.
- [ ] Empty/unsupported/cross-machine/unsafe retrieval performs no AMD call. Candidate pool includes only eligible current-key sources; malformed/zero/nonfinite/wrong-dimension vectors fail. FTS punctuation/accents/stopwords/rank changes have reviewed fixture expectations.
- [ ] Approved source/chunk tampering, changed embedding key, revoked/superseded source before or during inference, and logout/expiry during AMD/Whisper reject stale output; no partial answer or stale proposal leaks. Final checks use fresh connections/snapshots.
- [ ] Binary fixtures include PDF/text/audio, boundary sizes and rejected types; existing upload limits and byte-identical downloads survive. No transcription-only audio is retained as a document.
- [ ] Runtime cannot CREATE/DROP/ALTER/TRUNCATE, provision/change users/roles/passwords, mutate immutable source text, delete audit/history/documents or access dormant/admin tables. anon/authenticated/PUBLIC cannot access any SHIFT object. Runtime cannot SET ROLE to owner/admin. Service capability RLS policies match only reviewed operations.
- [ ] Authentication, request-origin checks and supervisor gates work through unchanged frontend calls; no browser Supabase credential or new public schema/API endpoint exists.
- [ ] Deadlock/serialization failures, lock/pool timeout, dropped connection, commit ambiguity and transaction-aborted state have bounded sanitized outcomes; no external inference is retried as a side effect. No pooled session state or idle transaction leaks after tests.
- [ ] Original SQLite suite and demo workflow remain operational without PostgreSQL extras. Test cleanup removes only explicitly owned disposable fixtures/containers/schemas, never a shared project or existing database.
- [ ] Migration and restore rehearsals pass below reviewed storage/connection budgets. No hosted cutover is proposed until all unresolved differences and capacity estimates have been reviewed.

## 12. Rollback design

During development, rollback is simply disabling the opt-in PostgreSQL test configuration and removing disposable synthetic fixtures. The existing SQLite demo is never part of the test write path.

Before a future cutover, take a private consistent source snapshot, run checksummed import into isolated target objects, verify and restore-test backups, then stop writes briefly for a final authorized transfer. Do not dual-write. Keep the old SQLite source and application release immutable and protected; invalidate sessions under the reviewed reauthentication policy. Do not drop the target schema to roll back an application deployment in the existing shared Supabase project.

Before PostgreSQL accepts any new writes, reverting the adapter setting to the retained SQLite snapshot is straightforward. **After PostgreSQL accepts writes, switching to the old SQLite snapshot loses new submissions, approvals, revocations and audit events.** A safe data rollback must freeze writes, export all new authoritative PostgreSQL state into a **new separate SQLite database**, convert bytea/vector/JSON formats, re-run every integrity/eligibility/hash check, rebuild FTS5/derived indexes, test authentication with fresh sessions, and only then point the rollback instance at the validated new file. Never overwrite the existing demo database. Rehearse this reverse conversion entirely with synthetic writes before approving cutover.

Prefer fixing the PostgreSQL application forward when that is safer than reverse transfer. Rollback scripts must verify source/target identity and explicit fixture/production mode; avoid destructive down-migrations, CASCADE drops and automatic cleanup on shared resources. Backup artifacts include credentials/hashes/documents and require private storage, limited access and retention rules; they are never committed.

## 13. Free-tier and operational risks

Public Supabase pricing checked 2026-10-18 lists Free as 500 MB database size, shared CPU / 500 MB RAM, 5 GB egress, 1 GB file storage, inactivity pause after a week, and no included automatic backups/PITR. These are public plan figures, not verification of the existing project's plan or remaining quota. [Pricing](https://supabase.com/pricing)

- **bytea consumes the 500 MB database allowance, not the separate Storage allowance.** Twelve submissions with four near-10-MiB files already approach 480 MiB before source rows, TOAST/index overhead, embeddings and existing project data. Do not use those figures as a safe capacity guarantee. Adopt a demo admission budget (proposed warning at 60%, block new capacity-heavy ingestion by 80% of the actual available budget) before a hosted demo; do not silently reduce accepted file limits in the adapter.
- One vector has 1,536 bytes of float components (pgvector adds representation overhead); source text, chunk text, FTS/GIN, row metadata, JSON and indexes add substantially more. Count existing project usage and migration/import staging overhead. Avoid ANN until needed; unused/redundant indexes waste storage and maintenance CPU.
- Shared database CPU/RAM can cause slow exact search, index builds, JSON/BLOB copies, autovacuum and connection contention. Keep initial corpus bounded, operate a single small app pool, test worst-case accepted uploads and check transaction latency. Database compute does not run Whisper or MiniLM.
- Connections are a separate finite budget shared with Supabase's services and other applications. Do not assume published Micro paid-tier connection figures apply to this Free project. Verify both direct database and pooler client limits later; account for tooling/provisioning and reserve headroom.
- Singapore database latency depends on the backend's location. Reduce N+1 serialization queries using batched review/attachment/AI metadata reads and avoid fetching BLOB data during list/RAG queries. Downloads and cross-region transfers consume egress; no unlimited download claim follows from unlimited API requests.
- Pausing/quota exhaustion can make a scheduled demo unavailable. Use explicit readiness checks and a private backup/restore rehearsal; do not implement artificial keep-alive traffic or buy upgrades. Keep the independent local demo ready.
- Free backups must be explicitly exported to already available private storage and restore-tested; do not assume platform recovery or branching is included. Offline backups and migration staging themselves need disk capacity.

Migrating persistence does **not** by itself establish a free full-featured Vercel backend: the Python ML/runtime/upload requirements identified in the deployment review still apply. Do not change hosting or reduce model/security features as part of this persistence migration.

## 14. Documentation verified and remaining decisions

Public documentation only was consulted. The Supabase changelog index was checked, including the PG17.11 minor-release advisory. This design introduces no ltree/btree_gist/legacy pgcrypto encryption/custom selectivity operators; existing project-wide effects are unknown and must not be “fixed” as part of a new private schema. [PG17 advisory](https://supabase.com/changelog/postgres-15-19-17-11-breaking-changes)

Relevant authoritative references:

- [Supabase connection modes, TLS and pooler restrictions](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase connection budgeting](https://supabase.com/docs/guides/database/connection-management)
- [Supabase custom PostgreSQL roles](https://supabase.com/docs/guides/database/postgres/roles)
- [Supabase API hardening / unexposed private schemas](https://supabase.com/docs/guides/api/securing-your-api)
- [Supabase pgvector](https://supabase.com/docs/guides/database/extensions/pgvector)
- [PostgreSQL 17 text search](https://www.postgresql.org/docs/17/textsearch-controls.html)
- [PostgreSQL 17 transaction isolation](https://www.postgresql.org/docs/17/transaction-iso.html)
- [pgvector exact search, cosine distance, dimensions and storage](https://github.com/pgvector/pgvector)

Review decisions: accept backend-service authorization plus private grants/RLS boundary; accept text timestamps for API parity; approve JSONB codecs and bytea-first storage; accept evaluated lexical-rank differences with exact vectors; choose initial capacity/pool budgets; agree that implementation/testing starts locally and that hosted inspection/SQL/configuration requires a separate authorization. No project access or secret is needed to review these decisions.
