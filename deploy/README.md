# SHIFT ACT III deployment bundle

Status: prepared locally; **no public deployment or visibility change is authorized yet**.
Use an existing hosting resource when supplied. Do not buy a plan, storage, domain,
or credits. The existing private AMD token remains accepted for this demo; rotation
is not a prerequisite. Backend `.env` remains mode 0600 and is excluded from Git,
Docker context, Vercel uploads and public source bundles.

## Intended topology

Browser → HTTPS Vercel Next.js → same-origin `/api/v1/*` rewrite → HTTPS FastAPI
on an existing persistent Linux host. FastAPI calls AMD Token Factory and performs
Whisper and MiniLM inference locally. SQLite and all attachments/indexes remain on
one named persistent volume. Run one API worker and one instance: request locks
are process-local and SQLite is the persistence layer. Do not use an ephemeral
backend filesystem or Vercel functions to host these models/database.

The official SHIFT logo and current layouts/colors are retained.

## Before any public release

Fetch all refs/tags, create the source snapshot and run the local scanner:

```sh
git fetch --all --tags --prune
python3 scripts/prepare_public_source.py --output /tmp/shift-release-review
python3 scripts/audit_release.py --source /tmp/shift-release-review \
  --gitleaks /path/to/gitleaks --report /tmp/shift-release-audit.json
```

Use Gitleaks 8.30.1. It scans all refs/reflogs/history and source, redacts all
findings and complements rules with exact matches against local private values.
If credentials are found, stop. Address the affected history before changing
visibility. Repeat the scan on the final release commit. Keep the judge password
file and all data directories private. Public source snapshot contains no `.git`
directory; the original repository's history is scanned separately.

## Backend: prepared, do not launch publicly yet

Docker is not installed on the preparation machine, so Linux image build and
host resource validation remain required. The Dockerfile uses the locked Python
3.12 dependencies, includes the voice extra and downloads pinned public Whisper
and MiniLM models at image build time. No AMD request is made during build or boot.
The locked Linux ML dependencies produce a large image; measure disk, RAM and CPU
on the supplied host rather than relying on an ephemeral free instance.

After confirmation and host access are supplied:

1. Transfer the reviewed source and separately transfer the existing private
   backend environment through the host's secure secret mechanism. Never paste it
   into GitHub, build arguments, Dockerfiles or Vercel. Keep `backend/.env` mode 0600.
2. Set `SHIFT_PUBLIC_ORIGINS` on the host to the JSON array of exact Vercel HTTPS
   origin(s), with no wildcard or trailing slash. For example:
   `export SHIFT_PUBLIC_ORIGINS='["https://your-project.vercel.app"]'`.
3. From the repository root, build the backend and initialize its named volume:
   `docker compose -f deploy/compose.yaml build api`.
4. Provision judge accounts on that fresh volume without printing passwords:
   `docker compose -f deploy/compose.yaml run --rm api /app/.venv/bin/python -m app.demo --database-path /data/shift.sqlite3 --credentials-file /data/judge-accounts.env`.
   This seeds synthetic records, hashes distinct generated passwords, and refuses
   to overwrite existing account roles/passwords. Retrieve the credentials through
   a private host session for the judge access sheet. Do not expose them in logs.
5. Warm the real approved-only index:
   `docker compose -f deploy/compose.yaml run --rm api /app/.venv/bin/python -m app.rag.prepare`.
6. Start only after deployment approval:
   `docker compose -f deploy/compose.yaml up -d api`.
   The API binds to loopback port 8000; configure an existing TLS reverse proxy.
   `Caddyfile` is an optional ingress template for a host with Caddy and an existing
   DNS name. Set `SHIFT_API_HOST`; validate the config before enabling it.
7. Confirm HTTPS `/api/v1/health` returns 200. Process health alone does not prove
   voice/model readiness: sign in and check AI configuration and voice status.

Keep the named volume when restarting/upgrading. Never use `down -v` on the demo.
Before replacing a host, use SQLite's online backup API to back up `/data/shift.sqlite3`
(not a raw copy of a live WAL database), and keep backups private. Restore into a
single instance before permitting writes. Do not reuse local developer sessions.

## Vercel: prepared, do not deploy yet

- Import the reviewed repository only after publication/deployment confirmation.
- Root directory: `frontend`; framework: Next.js; Node: 22.
- Install: `npm ci`; build: `npm run build`; default Next.js output.
- Set server-only `SHIFT_BACKEND_URL` to the HTTPS backend **origin**, no `/api/v1`,
  credentials, query or trailing path. Configure before building and redeploy if
  it changes. Builds on Vercel reject a missing or non-HTTPS backend origin.
- Leave `NEXT_PUBLIC_API_URL` unset. Production uses relative `/api/v1` requests,
  preserving existing HttpOnly, Secure, SameSite=Lax cookies without cross-site
  cookie exceptions. Do not add AMD keys to Vercel or any frontend environment.
- Keep backend CORS origins synchronized with the final frontend URL. Preview URLs
  need explicit origin entries or should remain disconnected from production data.
- Disable platform deployment protection for judges only when public launch is
  approved; verify access in a signed-out browser.

The external rewrite is a native proxy, not a new Next.js upload function.
[Vercel documents a 120-second external proxy timeout](https://vercel.com/docs/limits#proxied-request-timeout),
above the current backend deadlines. Validate actual audio and document upload
sizes on the selected host/platform; local proxy tests cannot certify edge limits.
[Next.js documents external rewrites here](https://nextjs.org/docs/app/api-reference/config/next-config-js/rewrites).

## Validation and judge demo

```sh
cd backend
uv sync --locked --extra voice
uv run --no-sync pytest -q
uv run --no-sync python -m app.rag.evaluate
cd ../frontend
npm ci
npm run lint
npm run typecheck
npm run build
npm run test:e2e
```

Browser tests use isolated synthetic SQLite storage and mocked AMD/speech; no API
credits. For occupied development ports, build with
`SHIFT_BACKEND_URL=http://127.0.0.1:8001 npm run build`, then run with
`SHIFT_E2E_FRONTEND_PORT=3001 SHIFT_E2E_API_PORT=8001 npm run test:e2e`.

An explicit real smoke is available from backend/:
`uv run --no-sync python -m app.deployment_check --audio /private/path/synthetic.wav --report /private/path/check.json`.
It uses real local Whisper, a temporary synthetic database and real approval APIs.
Add `--live-gemma` only when intentionally authorizing one AMD completion; it never
retries or switches models and records sanitized execution evidence. This run has
already made exactly one successful live Gemma check; do not repeat unnecessarily.

Judge sequence:

1. Sign in as `judge-tech` using the private access sheet. Open Capture Knowledge,
   choose CNC-02 and record a short synthetic vibration observation. Transcribe,
   inspect/edit the transcript, and insert it into the written observation.
2. Click **Structure with AI** once. Show AMD Token Factory, returned Gemma model,
   latency/usage metadata and the ten structured categories. Review/edit the
   proposal; preserve uncertainty and the original observation; submit.
3. Show **Pending** status and its absence from verified retrieval.
4. Sign out; sign in as `judge-supervisor`. Review the original and structured
   observation, then approve with a synthetic-demo note.
5. Return as technician, show the approved library entry and machine-scoped RAG.
   Use CNC-01's seeded spindle vibration question for a prepared grounded answer;
   its troubleshooting model is independently configured by existing `AMD_MODEL`.
6. Show an unsupported CNC-02 query before approval, or revoke the new item and
   show it excluded again. Do not describe synthetic notes as real repair advice.

The local prepared demo database is `backend/data/hackathon.sqlite3`; distinct
passwords are in ignored `backend/data/judge-accounts.env` (0600). Production
provisioning creates its own credentials privately; no passwords are in this guide.

## Remaining launch gates

Hosting resource and final URLs, Linux image build, persistent volume/restart and
TLS smoke, real browser microphone over HTTPS, final source audit, explicit public
release confirmation. No token-rotation gate is imposed. Shared judge account
passwords must stay private because authenticated inference consumes existing
AMD quota. No new credits or purchases are authorized.
