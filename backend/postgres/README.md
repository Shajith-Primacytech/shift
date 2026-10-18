# PostgreSQL adapter

For the separate reviewed remote-deployment path, see
[the hackathon deployment runbook](../../docs/HACKATHON_DEPLOYMENT.md).
Its production SQL lives under `production/supabase/migrations/`. Nothing has
been applied to hosted Supabase. The Phase 2 instructions below describe only
the original local bootstrap, which remains guarded and unchanged.

# PostgreSQL Phase 2: local development only

SQLite is still the default. This directory is **not a live Supabase deployment**.
The implementation follows [the reviewed design](../../docs/POSTGRES_SUPABASE_MIGRATION_DESIGN.md).
See [the implementation report](../../docs/POSTGRES_PHASE2_REPORT.md) for results and remaining work.

## Safety boundaries

- PostgreSQL requires explicit `SHIFT_STORAGE_BACKEND=postgres` and a separate
  environment-only `SHIFT_POSTGRES_DSN`. The PostgreSQL settings class never reads `.env`.
- Local mode rejects `SHIFT_ENVIRONMENT=production`, all remote addresses, implicit
  libpq services/passfiles/options, and databases not named `shift_test_*` or `shift_dev_*`.
- Only explicit loopback IPs/localhost are accepted and the IP address is pinned.
  This development connection deliberately uses a loopback-only database; hosted
  TLS/CA verification must be implemented/reviewed before lifting the guard.
- Application startup validates the restricted `shift_runtime` role and table
  access. It does not run migrations, create users or seed PostgreSQL data.
- PostgreSQL failures never fall back to SQLite. The SQLite path setting is ignored
  by the PostgreSQL runtime, and tests assert that no SQLite file is created.
- One backend worker remains required for process-local feature busy locks and CPU
  models. Persistence locks coordinate revisions/reviews/indexing across connections;
  they do not coordinate Whisper jobs or inference spending across replicas.

## Optional dependencies

From `backend/`:

```sh
uv sync --locked --extra voice --extra postgres
```

All existing dependencies remain locked; the extra adds Psycopg, its binary client,
its pool and the Python pgvector adapter. SQLite requires none of these modules.

## Test prerequisites

Use a **dedicated disposable local PostgreSQL 17 cluster**, bound to loopback,
with the pgvector extension available. Do not point these tools at a shared
work database. The tests create randomly named `shift_test_*` databases, then
remove only the databases they created. Roles remain in the disposable cluster.
Stop/remove that cluster when finished.

Supply these variables privately through the test process environment:

| Variable | Meaning |
| --- | --- |
| `SHIFT_PG_TEST_ADMIN_DSN` | Explicit loopback connection to a `shift_test_*` control database in the dedicated cluster; needs local database/role/extension setup privileges. Must contain user, password and database explicitly. Never a hosted/admin production DSN. |
| `SHIFT_PG_TEST_RUNTIME_PASSWORD` | Synthetic local database password used when creating `shift_runtime`. Repeated runs on the same cluster must supply its existing test password; the bootstrap does not rotate existing roles. |

Do not place credentials in checked-in files, CLI arguments, logs or reports.
The fixture sets the application's runtime DSN in memory using the isolated test
database name. It provisions synthetic technician/supervisor accounts and invokes
HTTP requests using the existing synthetic regression credentials.

Run from an empty temporary working directory to avoid loading the normal backend
`.env`, including during import of the ASGI module:

```sh
# Start at the SHIFT repository root after configuring the two test env variables.
shift_repo_dir="$(pwd)"
shift_test_dir="$(mktemp -d)"
cd "$shift_test_dir"
PYTHONPATH="$shift_repo_dir/backend" \
  "$shift_repo_dir/backend/.venv/bin/python" -m pytest \
  "$shift_repo_dir/backend/tests" -q -o "cache_dir=$shift_test_dir/pytest-cache"
```

Without an explicit test-cluster DSN the database integration tests skip with a
reason; configuration safety tests and SQLite regressions still run. Without the
optional driver extra, driver-dependent tests skip. A skip is not proof of
PostgreSQL compatibility. This change was tested against a real disposable server.

## Explicit local bootstrap

The test fixture normally owns provisioning. For a separate, empty, named local
synthetic database only, a manual helper is available:

```sh
python -m app.storage.postgres_local --local-synthetic
```

It uses the two test environment variables above, refuses an incompatible existing
schema/role, applies the separately generated local migration, records its checksum
and seeds checked-in synthetic records. Re-running verifies the checksum and does
not duplicate seeds. It never opens SQLite. It does not create application users;
those are provisioned by the integration fixture. Existing SQLite administrative
CLI commands refuse PostgreSQL selection rather than opening a SQLite fallback.

The SQL migration file was created with `supabase migration new`; only its guarded
local runner has applied it. Do **not** link, push, reset or apply it to the existing
Supabase project without a separate migration review and authorization.
