# Deployment validation — 18 October 2026

Status: **225 passed, 0 failed, 0 skipped** in 19.82 seconds.
One existing Starlette/httpx TestClient deprecation warning remains. No dependency
upgrade was included solely to suppress that warning.

## Reproduce without touching a hosted project

Install PostgreSQL 17 with pgvector available in its extension directory and an
OpenSSL CLI. From the repository root:

```sh
cd backend
uv sync --locked --extra voice --extra postgres
.venv/bin/python scripts/validate_deployment.py \
  --pg-bin /absolute/path/to/postgresql17/bin \
  --openssl /absolute/path/to/openssl
```

The runner creates two fresh private temporary clusters on loopback and randomly
allocated ports. It strips SHIFT/PG/AMD environment variables, runs from an empty
temporary working directory so `.env` is not loaded, generates synthetic passwords
in process memory, and stops both clusters in a finally block. It creates no live
resources and prints no credentials. Test certificates/cluster artifacts remain
in its reported private temp directory for inspection; remove those directories
when no longer needed. The optional integration tests skip when run directly
without explicitly supplied disposable test-cluster settings; a skipped run is
not equivalent to the result reported here.

Validated here with PostgreSQL 17.11 and pgvector 0.8.7 on macOS. The runtime uses
locked Psycopg 3.3.6, psycopg-pool 3.3.3 and Python pgvector 0.5.1. The production
migration was generated using Supabase CLI 2.121.0, without linking a project.

## Evidence and boundaries

- Existing SQLite and PostgreSQL regressions pass, including authentication,
  CSRF checks, login throttling, review/revision races, independent review,
  document authorization, retained review history, approved-only RAG, inference
  receipt persistence and revocation/stale-evidence checks. Provider/model calls
  in regression tests are faked; this does not establish live AMD inference.
- Production SQL executes as a role named postgres with CREATEDB/CREATEROLE and
  **without SUPERUSER**, against an existing empty schema with accidental API
  usage grants. Vector is pre-enabled by the test administrator with grantable
  extension usage, as required by the runbook. Result: all 15 private tables owned
  by shift_owner with RLS enabled, no API-role schema access, no seeded records.
- Real restricted-role queries verify vector(384) compatibility and refusal of
  user insertion, audit mutation/deletion, content overwrite, document deletion,
  TRUNCATE, schema DDL, owner SET ROLE and migration-ledger reads.
- Reapplying the baseline fails intentionally and leaves the migration ledger
  unchanged. PostgreSQL 17 retains the automatic role-creator ADMIN grant to
  postgres; tests assert SET/INHERIT are false after temporary DDL access is revoked.
- Actual libpq TLS handshakes succeed with the synthetic trusted certificate and
  matching hostname, and reject hostname mismatch, untrusted/missing CA, bad credentials
  and an unavailable endpoint. A production PostgresStore starts over that real
  TLS connection and validates its role, schema and effective grants. Only the
  test socket address/port are routed to loopback; TLS/role checks stay enabled.
- Startup refuses unexpected audit DELETE grants, public-schema CREATE grants,
  and disabled RLS. Offline tests reject insecure TLS modes, administrator DSNs,
  ambient libpq overrides, transaction-pooler ports, unexpected hosts, missing CA,
  automatic seeds and unsafe production origins. Storage failures produce a
  generic HTTP 503 and never create a SQLite fallback.
- Offline provisioning emits only hashed account credentials to a new mode-0600
  private file, escapes account names and preserves independent account roles.
- Render YAML's no-auto-deploy setting, readiness path, PORT handling and one-worker
  command are checked locally. Ruff checks on changed Python code and
  `git diff --check` pass.

## Migration artifact

File: `backend/postgres/production/supabase/migrations/20261018082544_shift_production_storage.sql`

SHA-256: `67fce4c2c1a5f33da0a641af4a9a317749e844c4ca1896391efdea8185003f30`

The original local migration, application authentication/review routes and RAG
implementation remain unchanged relative to the feature branch.

## Not validated / approvals still required

No hosted Supabase query or SQL change, Supabase Advisor run, Supavisor session
connection, secret provisioning, public deployment, Vercel environment update,
remote Git push or merge was performed. Main remains at
`74d538b991c3c31b8cba853be68777ff8bd334f0` with the user's existing work preserved.

Docker is unavailable on this machine (the installed CLI link points to a missing
Docker application), so the Linux image build was not run. Real Render model
memory/CPU, cold starts, backend HTTPS origin, frontend proxy cookies, restart
persistence and live RAG/provider flows remain deployment gates. A successful
local TLS/migration test is **not** a claim of hosted integration success.
See [the exact deployment and rollback runbook](HACKATHON_DEPLOYMENT.md) for
approval checkpoints, configuration and remaining blockers.
