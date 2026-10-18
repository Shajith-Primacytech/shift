# SHIFT PostgreSQL Phase 2 implementation report

Completed locally on 2026-10-18. No live Supabase access or changes, deployment,
commit, push, purchase, existing SQLite database access, or private environment-file
read was performed. Source changes are uncommitted and ready for review.

## Implemented

- Optional `SHIFT_STORAGE_BACKEND=postgres`, with SQLite as the unchanged default.
  The default app does not import the PostgreSQL driver or initialize a pool.
- A separate PostgreSQL semantic repository (`app/storage/postgres.py`) with
  explicit schema-qualified `%s` SQL, dictionary rows, JSONB/bytea/vector codecs,
  a bounded per-app Psycopg pool and short transactional units. No SQL-string
  replacement shim and no automatic fallback database.
- The original SQLite SQL/migrations/initialization path is retained. Shared routes
  dispatch to PostgreSQL methods only when selected. Public validation,
  serialization, document authorization and cookie formatting are shared. A broad
  rewrite of the SQLite repository is intentionally avoided during compatibility
  work; the unchanged HTTP regression assertions also run against PostgreSQL.
- Preserved endpoints, response shapes, source date strings, binary attachments,
  scrypt authentication, hashed opaque sessions, HttpOnly/Secure/SameSite cookies,
  request-origin/header checks, technician/supervisor access, self-review rejection,
  immutable revisions, privileged history and append-only audit permissions.
- PostgreSQL advisory transaction locks coordinate per-record revisions, reviews
  and derived-index replacement. Conditional status updates and an atomic AI-run
  row lock/claim prevent double review or double use. Login throttle and capture
  cooldown checks are also serialized per key/owner.
- Interrupted capture receipts commit before AMD. Result updates commit separately.
  Model/HTTP/transcription work holds no PostgreSQL transaction or checked-out
  connection. Session checks run again after slow work; success is returned only
  after storage commits.
- Exact native `vector(384)` cosine queries and generated simple-config tsvector/GIN
  search. Semantic thresholds, meaningful-term overlap, candidate counts, RRF,
  machine/approval/latest-version scope and exact citations remain enforced.
  Float32 vectors are rescored using the existing NumPy routine to preserve gate
  and tie semantics. Final evidence checks use a fresh single-statement snapshot
  and also verify generation/embedding-key coherence.
- Separate local-only schema migration, generated with the Supabase CLI, preserving
  the reviewed types/constraints, text IDs/timestamps, JSONB and bytea compatibility.
  The application schema is `shift_private`, owned by a NOLOGIN role. Runtime has
  explicit operation/column grants, no DDL/provisioning/history deletion rights,
  and operation-specific service-role RLS policies. These remain the reviewed
  trusted-FastAPI boundary, **not** per-technician database RLS.
- A guarded, explicit synthetic bootstrap and checksum ledger. App startup never
  applies schema changes or seeds PostgreSQL. Existing SQLite management commands
  refuse PostgreSQL mode; RAG preparation supports the selected local store.
- PostgreSQL credentials load only from environment variables, never `.env`.
  Phase 2 rejects production mode, remote/non-loopback targets, ordinary/live
  database names and libpq target overrides. Runtime refuses privileged/owner-member
  roles. Driver/pool failures become sanitized 503 responses without replaying
  inference or silently writing to SQLite.

Local Whisper workers, model pins, AMD transport/Gemma selection, provider deadlines
and frontend configuration have not been replaced or changed. Four optional
packages were added to the local Python environment; no existing locked ML package
was upgraded or removed.

## Verification

Environment: disposable, user-space PostgreSQL **17.11**, native pgvector **0.8.7**,
Python **3.12**, Psycopg **3.3.6**, psycopg-pool **3.3.3**, Python pgvector **0.5.1**.
The server listened on loopback only. The final combined run used SCRAM database
password authentication; credentials were generated in process/environment and
were not printed or saved in the repository. Each fixture created and removed its
own random database. The disposable server was stopped after testing.

| Check | Result |
| --- | --- |
| Original SQLite baseline before adapter changes | 147 passed |
| Original SQLite regressions after integration changes | 147 passed |
| New PostgreSQL integration coverage | 34 passed |
| New configuration/vector safety coverage | 13 passed |
| Final combined backend suite | **194 passed**, 1 existing Starlette/httpx deprecation warning; 18.36 seconds |
| Ruff undefined/unused-name checks for backend and new tests | Passed |
| Lockfile consistency (`uv lock --check`) | Passed |
| Patch whitespace (`git diff --check`) | Passed |

The PostgreSQL tests cover:

- Eight unchanged existing HTTP regression tests against the new adapter, including
  restart persistence, review history, cross-technician access, self-review,
  superseded approval, stale review and document gates.
- Independent concurrent supervisor reviews: one succeeds, one gets 409, one audit
  event. Concurrent revisions produce distinct revisions 2 and 3. Review/revision
  races never expose an older approved version behind a pending latest revision.
- Concurrent failed logins cannot bypass five-attempt throttling; distinct database
  connections cannot both pass the capture cooldown. Two submissions using one
  AI run yield one success and one rejection with no orphan version/attachments.
- Binary download checksum/byte identity, literal substring search/injection
  strings/ASCII folding, upload failures, session expiry/hashes, secure cookies,
  original capture-source matching and AI-run ownership.
- Native vector dimensions and FTS, approved-only citations, empty-scope abstention,
  source/chunk tampering, supersession/revocation before or during inference,
  embedding-key changes and logout during AMD/Whisper work.
- Committed interrupted receipts visible before inference; no pooled connection
  held during provider work. Driver failure rolls back a partially inserted
  attachment/submission. A failed audit insert rolls back the status change.
- Runtime permission denials (DDL, role escalation, source mutation, audit/document
  deletion, privileged tables), RLS coverage, pool recovery/sanitized failures,
  idempotent schema/seed application and checksum drift rejection.
- Column/FK coverage compared with a freshly created **in-memory** SQLite schema;
  no existing database is used as the source of this test.

Automated inference uses existing offline test doubles. No live AMD credits were
used. Real Whisper/MiniLM end-to-end latency/quality, the full browser suite and
hosted network/TLS/quotas were not revalidated in this phase. PostgreSQL lexical
ranking deliberately uses PostgreSQL rank rather than SQLite BM25; it is not
claimed numerically equivalent.

## Operating the development path

See [backend/postgres/README.md](../backend/postgres/README.md) for environment-only
settings, disposable cluster requirements, isolation and test commands. Public
project identity, region, installed hosted extensions, current privileges and
remaining free quota have not been inspected. The target remains the user-supplied
existing PostgreSQL 17 Singapore project; no target endpoint is inferred or stored.

## Remaining work before any live migration

1. Review the implementation and local migration, including the accepted service
   authorization/RLS boundary, text timestamp compatibility and lexical-rank change.
   No new schema or security decision beyond that design was needed to complete
   the local adapter. A live connection is deliberately impossible through Phase 2.
2. Separately authorize and inspect hosted metadata: confirm project identity,
   version, namespace/version of pgvector, absence of schema/role collisions,
   Data API exclusion, inherited privileges, actual free storage/connection budget
   and correct Singapore endpoints. Do not modify shared Supabase objects blindly.
3. Implement/review a hosted connection path using a least-privilege role, verified
   TLS/CA/hostname checks, appropriate direct/session pooling and schema-version
   checks. Lifting the loopback/production guard requires a separate reviewed change;
   it must not be bypassed with production set to development.
4. Prepare controlled migration and user-provisioning identities/tools. The local
   bootstrap and its test/admin credentials are not production tools or credentials.
   The Docker production build currently remains SQLite/voice oriented; enabling
   PostgreSQL there requires explicit optional dependency/configuration work.
5. Implement and rehearse a checksummed synthetic importer and reverse exporter,
   attachment/vector/JSON conversions, identity sequence restoration, private backup
   and recovery, write freeze and session reauthentication policy. No existing SQLite
   file has been migrated. A post-write rollback must not point at a stale snapshot.
6. Evaluate real MiniLM retrieval quality including FTS rank/tokenization differences;
   run real local Whisper and a deliberately authorized AMD smoke only when needed.
   Run browser workflows through the chosen ingress and measure accepted upload sizes,
   database growth, connection use and latency within free-tier limits.
7. Keep one worker until durable cross-process feature job limits are designed/tested.
   This repository does not yet include a distributed Whisper/inference queue or
   feature lease system. Keep the independent SQLite demo available throughout.

The phase is ready for code review and additional local development. It is **not**
a live migration or deployment, and the production/Supabase restrictions remain active.
