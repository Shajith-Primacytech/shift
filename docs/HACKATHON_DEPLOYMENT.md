# SHIFT PostgreSQL hackathon deployment

Prepared 18 October 2026. **No hosted SQL, deployment, Vercel environment change,
push, or merge is authorized by this preparation.** Production main is untouched.
Work is on `codex/hackathon-postgres-deployment`, based on feature commit
`fc85ecc218e55f8c7bc53a2a5600fdf4ee99e93f`.

## Architecture and reviewed security boundary

Browser → existing Vercel same-origin `/api/v1/*` rewrite → HTTPS FastAPI on Render
→ Supabase PostgreSQL using a dedicated `shift_runtime` password. Supabase Auth,
Data API, service-role keys and browser database clients are not used. Existing
SHIFT scrypt passwords, opaque hashed sessions, secure HttpOnly SameSite cookies,
CSRF header/origin checks, independent supervisor review, revision handling,
approval/revocation checks before and after inference, and append-only review
history remain authoritative in FastAPI. Do not publish demo account passwords.

The production baseline is ONLY
`backend/postgres/production/supabase/migrations/20261018082544_shift_production_storage.sql`.
The original `backend/postgres/supabase/migrations/` is LOCAL ONLY; do not apply it
first and do not `supabase db push` the two directories together.

The reviewed baseline retains 15 tables, `extensions.vector(384)`, generated
simple-language full-text vectors, GIN lexical search, explicit vector operators,
and exact filtered vector ranking. There is no approximate vector index; this
avoids limiting away eligible evidence before authorization. Use the deployed
extension default; do not pin or relocate an existing shared extension blindly.

`shift_owner` is NOLOGIN, owns the schema/tables, and is not the runtime role.
`shift_runtime` starts NOLOGIN with no password; it has no role memberships,
SUPERUSER, CREATEDB, CREATEROLE, REPLICATION or BYPASSRLS. Only SELECT on account
hashes/machines, narrow INSERT/DELETE rights for session/attempt/index state,
INSERT-only review/document history, and enumerated column UPDATE rights are
granted. No runtime user creation, audit deletion, content overwrite, TRUNCATE,
DDL, schema migration access or conversations access is granted. The backend
checks effective table/column privileges, role attributes, membership, table
ownership and RLS at startup and refuses drift. Database faults return redacted
503s, never SQLite fallback. Runtime never executes DDL, seeds, or admin scripts.

RLS is enabled everywhere, but policies intentionally trust this backend role
across rows; user-level authorization is in FastAPI, not `auth.uid()`. A stolen
runtime credential can read private backend data and exercise its write grants.
Keep it exclusively on the backend, rotate on compromise, and never grant it to
`authenticator` or any other Supabase role. The owner can bypass RLS for deliberate
administration; FORCE RLS would prevent that provisioning path and is not enabled.
No SECURITY DEFINER functions, views, public policies or new shared-role powers
are introduced. `anon`, `authenticated`, `service_role`, `authenticator` and PUBLIC
receive no access to this schema. Keep `shift_private` out of Data API exposed
schemas and Realtime publications even though ACLs and RLS also block access.

## Approval checkpoint A: Supabase provisioning

Obtain approval for the exact migration and project before any step below that
connects to hosted Supabase, including preflight queries. Confirm SHIFT project
reference, region, PostgreSQL version, backup/recovery plan and no existing data.
The reported zero tables is not proof there are no functions, types, or roles.

1. In the approved project's dashboard inspect Connect, database extensions,
   exposed schemas, and SSL settings. Enable `vector` in `extensions` if needed
   (a separate approved live change). Never move an existing extension used by
   another application. The migration also checks this and rolls back on mismatch.
2. Download the project's database CA certificate from its dashboard using the
   official connection/SSL instructions. Validate its provenance. Keep a local
   absolute path. Obtain the actual direct hostname from Connect; do not derive
   the session pooler hostname from the region. Migrations use direct PostgreSQL
   on port 5432; if the admin workstation cannot reach IPv6, use the session
   pooler on 5432 with the dashboard's `postgres.<project-ref>` username.
3. In a private administrative shell, set these non-password libpq variables to
   actual approved values, then let `psql -W` prompt. Do not save passwords in
   command history or use frontend Supabase API keys as database passwords.

   ```sh
   export PGHOST='<approved direct or session hostname>'
   export PGPORT=5432 PGDATABASE=postgres
   export PGUSER=postgres # session pooler: postgres.<project-ref>
   export PGSSLMODE=verify-full PGSSLROOTCERT='/absolute/path/supabase-ca.crt'
   psql -X -W -v ON_ERROR_STOP=1
   ```

4. Run this read-only preflight, and review output privately:

   ```sql
   SELECT current_user, current_database(), version();
   SELECT e.extname,e.extversion,n.nspname FROM pg_extension e
     JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector';
   SELECT rolname,rolcanlogin,rolsuper,rolbypassrls FROM pg_roles
     WHERE rolname IN ('shift_owner','shift_runtime'); -- must return zero
   SELECT n.nspname,c.relname,c.relkind FROM pg_class c
     JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='shift_private';
   SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
     WHERE n.nspname='shift_private';
   SELECT t.typname FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
     WHERE n.nspname='shift_private'; -- all three object lists must be empty
   SELECT nspname,nspowner::regrole,nspacl FROM pg_namespace
     WHERE nspname IN ('shift_private','extensions');
   ```

   Inspect public/default grants and role memberships as well. Supabase's
   `postgres` needs permission to grant extension-schema/type usage and change the
   empty schema owner; do not grant SUPERUSER or BYPASSRLS if this fails. Have the
   project administrator resolve the scoped extension ownership/grant issue.
   The migration was tested with non-superuser postgres plus grantable extension
   usage; managed Supabase extension creation itself still needs hosted testing.

5. Record the approved SQL's SHA-256 (`shasum -a 256 <migration-file>`) in the
   deployment record. Capture a private preflight/ACL snapshot and a backup of
   any existing `shift_private` schema (`pg_dump -W --schema=shift_private
   --format=custom --file=/private/backup/shift-before.dump`). If absent, record
   that fact instead. Verify the backup restore procedure before taking data.
6. Apply only the reviewed file from repository root, using the same verified
   libpq settings. The file owns its BEGIN/COMMIT; do not add `--single-transaction`.

   ```sh
   psql -X -W -v ON_ERROR_STOP=1 \
     -f backend/postgres/production/supabase/migrations/20261018082544_shift_production_storage.sql
   ```

   On any error, disconnect/ROLLBACK; do not continue the failed script or patch
   permissions ad hoc. Existing roles/objects cause an intentional hard failure.
   Re-running a completed migration intentionally fails. The private ledger stores
   the baseline identifier, not a self-referential file checksum; the external
   SHA-256 is the authoritative artifact-integrity record.
7. Privately provision a fresh runtime password through interactive `psql`:

   ```sql
   SET password_encryption = 'scram-sha-256';
   \password shift_runtime
   ALTER ROLE shift_runtime LOGIN;
   ```

   Use a password manager-generated value (32+ random characters). `\password`
   prompts and avoids putting the plaintext into a SQL file/history. Do not use
   `postgres`, `service_role`, publishable keys, or anon credentials for FastAPI.
8. Prepare account/machine provisioning offline from `backend/`. Make a reviewed
   JSON **list** of machine objects using the frontend's machine metadata shape
   (the local `app/storage/synthetic.json` has a `machines` list as an example).
   Supply only approved demo metadata, no automatic historical approvals.

   ```sh
   uv run --locked --extra postgres python -m app.storage.production_provision \
     --machines-json /private/reviewed-machines.json \
     --output /private/shift-accounts.provision.sql
   ```

   This prompts for one technician and two supervisors with distinct usernames
   and unique passwords. It creates a new mode-0600 SQL artifact containing
   scrypt hashes, never connects, and never seeds knowledge. Review privately,
   separately approve the users and machine list, then apply with
   `psql -X -W -v ON_ERROR_STOP=1 -f /private/shift-accounts.provision.sql` in the
   administrative shell. Remove the private artifact securely per your retention
   policy. Never commit it. A supervisor cannot approve their own submission;
   the second supervisor permits review of supervisor-authored work.
9. Verify as admin: 15 tables, every table RLS enabled and owned by shift_owner;
   role flags, no runtime memberships, no API schema access, and no lingering
   SET/INHERIT-enabled postgres membership in shift_owner. PostgreSQL 17 may retain
   its automatic role-creator ADMIN-only grant (SET=false, INHERIT=false); postgres
   remains the trusted role administrator and can deliberately re-grant access. Run Supabase Security Advisor and review
   scoped findings; do not "fix" intentional private backend policies by exposing
   them. Log the migration hash, grants review, advisor results and provisioned
   account identifiers without passwords or hashes.

## Approval checkpoint B: create the hosted backend

`render.yaml` prepares a Docker web service, single replica/worker, Singapore,
Free plan, auto-deploy off, and `/api/v1/ready` as database-backed health check.
`backend/Dockerfile.hackathon` installs locked voice and PostgreSQL extras,
predownloads pinned public embedding/Whisper models and runs without root. No
runtime model downloads or database admin credentials are required. SQLite's
existing Dockerfile and behavior are preserved. No Docker build or hosted
capacity success is claimed by unit/database tests.

After explicit public deployment approval, push only this branch and select it
for a new Render service. Do not change main or attach this branch to the existing
frontend production deployment. Upload a Render secret file named
`supabase-ca.crt` so it appears at `/etc/secrets/supabase-ca.crt`. If the pooler's
certificate chain requires a different trust root from the direct endpoint,
obtain its official CA bundle; do not downgrade verify-full or trust an arbitrary
certificate to resolve the error. Set these server-only variables:

| Variable | Exact requirement |
| --- | --- |
| `SHIFT_ENVIRONMENT` | `production` |
| `SHIFT_STORAGE_BACKEND` | `postgres` |
| `SHIFT_SEED_SYNTHETIC` | `false` |
| `SHIFT_POSTGRES_MODE` | `session` (IPv4 session pooler), or `direct` if IPv6 works |
| `SHIFT_POSTGRES_DSN` | `host=<Connect session pooler host> port=5432 dbname=postgres user=shift_runtime.<project-ref> password=<libpq-escaped runtime secret> sslmode=verify-full` |
| `SHIFT_POSTGRES_EXPECTED_HOST` | Exact DSN hostname from the approved Connect dialog |
| `SHIFT_POSTGRES_SSLROOTCERT` | `/etc/secrets/supabase-ca.crt` |
| `SHIFT_POSTGRES_POOL_MAX` | `2` (bounded 1–4); one service replica |
| `SHIFT_POSTGRES_CONNECT_TIMEOUT` | `5` seconds (bounded 1–10) |
| `SHIFT_CORS_ORIGINS` | JSON array, e.g. `["https://shift-demo.vercel.app"]`; actual frontend origins only, no slash/wildcard/path |
| `AMD_API_KEY` | Existing provider secret, server-only; required for live inference |

Use URI form if more convenient: percent-encode user/password and include explicit
`:5432`, database and `?sslmode=verify-full`. A direct DSN uses `user=shift_runtime`
instead of the pooler suffix. Do not use transaction pooler/6543: this adapter
configures session timeouts, search_path and pgvector registration once per
connection. Prepared statements are disabled but that alone does not make session
state transaction-pooler compatible. No libpq `PG*` variables are allowed on the
runtime, nor DSN service/options/hostaddr/passfile overrides. Admin instructions
use a separate shell; do not copy those `PG*` settings into Render.

Wait for successful startup validation and a 200 from `/api/v1/ready` over the
assigned Render HTTPS hostname. `/api/v1/health` reports process health only.
A successful probe does not prove AI, RAG authorization, or frontend sessions.
Do not scale replicas while model/spending busy locks remain process-local.

## Approval checkpoint C: connect a frontend deployment

The existing `frontend/next.config.ts` already proxies `/api/v1/*`. In a separately
approved Vercel deployment set **server-only** `SHIFT_BACKEND_URL` to
`https://<assigned-backend>.onrender.com` (origin only; no `/api/v1`, credentials,
query or fragment). Keep `NEXT_PUBLIC_API_URL` unset/empty so the browser
uses the same-origin proxy. Add the exact Vercel frontend HTTPS origin to the
backend's `SHIFT_CORS_ORIGINS`. Rebuild the frontend because rewrites are evaluated
at build time. Do not weaken the existing Vercel HTTPS build guard.

The branch inherits Vercel automatic Git deployments disabled; keep that guard.
Use a separate reviewed preview/demo deployment before changing production
settings. Login through the frontend, not cross-site directly to Render: this
preserves same-origin HttpOnly cookies. Verify Secure/HttpOnly/SameSite=Lax,
login/me/logout, invalid-origin and missing-header rejection, failed-login limits,
private document access, and independent reviewer behavior through the actual
Vercel proxy. Never set a cookie Domain to the backend host.

Capture a fresh Pending record: it must not enter RAG. Independently approve it,
verify grounded citations, create a revision (old approval invalidated), reject
and revoke in separate flows, and confirm withdrawn evidence cannot survive
pre/post-inference revalidation. Review immutable history, then restart the
backend and verify accounts/records/documents survive. Also verify speech,
embedding load and inference under realistic concurrent demo requests.

## Rollback and incident containment

Before COMMIT, any migration failure rolls back schema/roles/grants created by
that transaction. Pre-enabled vector remains a shared extension; do not drop it.
Do not run an automatic down migration or drop Supabase public/auth/storage.

After COMMIT, prefer application rollback to a tested **PostgreSQL-compatible**
backend revision using the same schema. Never route this dataset back to SQLite:
there is no cross-store migration or reverse replication. Keep frontend pointed
at the last healthy compatible backend, or put the demo into maintenance while
repairing it. Retain schema, uploaded documents and audit trails.

For a credential incident, stop the backend and, as approved project postgres:

```sql
ALTER ROLE shift_runtime NOLOGIN;
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
 WHERE usename='shift_runtime' AND pid<>pg_backend_pid();
```

NOLOGIN alone does not disconnect existing pool sessions. Rotate using
`\password shift_runtime`, update the backend secret, review history and effective
grants, then separately approve `ALTER ROLE shift_runtime LOGIN` and restart.
If managed Supabase denies session termination, stop the backend/pooler clients
and ask the project admin to terminate remaining sessions; do not assume they died.

A schema restore requires an explicit maintenance window and separately reviewed
restore plan. First export the current schema/data/audits to protected storage,
verify a restore into an isolated database, and reconcile all writes since the
backup. Restore the approved `pg_dump` artifact only after those checks. Never
execute `DROP SCHEMA ... CASCADE` merely to retry this baseline. Even an initially
empty deployment should be retained/disabled until an explicit deletion approval.

## Remaining blockers before a live success claim

- Hosted preflight, database version/extension privileges and advisor results are
  unverified; no live SQL was executed for this work.
- Approval to apply the reviewed migration, enable vector if needed, set the
  runtime password, and provision distinct accounts/reviewed machine metadata.
- Actual session-pooler hostname, project ref, CA bundle and TLS/custom-role login
  must be verified from the target backend network. Unit tests cannot establish
  Supavisor or managed-project compatibility.
- Approval to push/deploy the branch, create the Render service and secrets, and
  separately change/rebuild a Vercel demo deployment's backend origin.
- Docker/Linux build and full model load are unverified. Free Render has 512 MB
  RAM and no durable disk: PyTorch/embeddings plus Whisper may exceed the limit.
  Full-feature operation on Free is a capacity blocker until measured; do not
  disable RAG/voice/security to claim it passed. Select sufficient paid capacity
  or another approved host if the full model workload cannot fit.
- Free services idle after 15 minutes and can take about a minute to wake; quotas
  and outbound-traffic limits can suspend demos. Budget/cold-start acceptance is
  needed. No production availability guarantee is implied by this free plan.
- Backend URL is not assigned yet, so the current Vercel failure remains until an
  approved hosted HTTPS backend is healthy and `SHIFT_BACKEND_URL` is rebuilt.
- Live provider inference, real frontend proxy cookies/CSRF, restart durability,
  review/audit and RAG revocation smoke tests remain pending.

## References checked

[Supabase connections](https://supabase.com/docs/guides/database/connecting-to-postgres),
[custom database roles](https://supabase.com/docs/guides/database/postgres/roles),
[SSL connections](https://supabase.com/docs/guides/platform/ssl-enforcement),
[extension version defaults](https://supabase.com/changelog/extension-version-pinning-ignored),
[PostgreSQL 17.11 security changes](https://supabase.com/changelog/postgres-15-19-17-11-breaking-changes),
[Render Free limits](https://render.com/docs/free),
[Render compute capacity](https://render.com/docs/compute-plans),
[Render Blueprint reference](https://render.com/docs/blueprint-spec).
The current Supabase changelog was scanned; no new custom estimators, deprecated
crypto/ltree indexes, or HTTP database clients are added by this adapter.
