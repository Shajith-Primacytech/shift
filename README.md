# SHIFT — Industrial Knowledge Intelligence

SHIFT preserves technician knowledge for the AMD Developer Hackathon ACT III.
All demonstration factory data and telemetry are synthetic.

## Current status: Stage 3 vertical slice

Stage 2 persistence, authentication and supervisor review remain operational.
The approved narrow Stage 3 slice adds LlamaIndex token-aware chunking, local
Sentence Transformers embeddings, SQLite FTS5 plus vector retrieval, and AMD
DeepSeek selection of approved source passages with verified citations.
Troubleshooting now calls the authenticated backend. Answers are explicitly labeled
AI-selected source quotes, not a diagnosis. No real machine controls exist.
See `docs/STAGE_3_REPORT.md` for measured validation and deferred capabilities.

## Submission and acceptance

- [Submission overview and description](docs/SUBMISSION.md)
- [Reproducible demo and 90-second script](docs/DEMO_GUIDE.md)
- [Final acceptance and GitHub readiness](docs/FINAL_ACCEPTANCE.md)

Technical acceptance passes. AMD credential rotation is **PENDING**, intentionally
deferred by the owner. It remains an unresolved security requirement and does not
block the authorized private repository preparation. No claim is made that the
exposed credential is safe.

## Local setup

Prerequisites: Node.js 24, npm and [uv](https://docs.astral.sh/uv/).
Run backend commands from `backend/`; paths in settings are relative to that directory.

```sh
cd /Users/mohamedshajith/Projects/shift/backend
uv sync --locked
uv run python -m app.manage init-db
uv run python -m app.rag.prepare
uv run python -m app.manage create-user --username technician --name "Arun Patel" --role technician
uv run python -m app.manage create-user --username supervisor --name "Maya Chen" --role supervisor
```

Each account command securely prompts twice for a password of 12–256 characters.
There are no default passwords, public registration, or client-selected roles.
Use separate credentials for the two accounts. Account provisioning requires local
access to the backend computer. Keep passwords and the database private.

Start the backend:

```sh
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
cd /Users/mohamedshajith/Projects/shift/frontend
npm ci
npm run build
npm run start
```

For frontend development, use `npm run dev` instead of build/start.

- Frontend: [http://localhost:3000](http://localhost:3000)
- API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Process health: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

Use matching hostnames for frontend and API: both `localhost` or both `127.0.0.1`.
The frontend defaults to its current hostname on port 8000. Optional settings are
in `frontend/.env.example` and `backend/.env.example`. Configure `AMD_API_KEY`,
`AMD_BASE_URL` and `AMD_MODEL` only in ignored `backend/.env`. The preparation
command downloads the pinned public MiniLM model once; subsequent retrieval is
local. Never place credentials in `NEXT_PUBLIC_` variables.

SQLite defaults to `backend/data/shift.sqlite3`, with WAL mode and foreign keys.
Startup applies ordered transactional SQL migrations and seeds six synthetic
machines and six sample knowledge records once. Seed approvals are explicitly
synthetic and do not represent real maintenance authorization. Account creation
and normal startup never reset stored submissions. Back up the database with
SQLite's backup mechanism or while the service is stopped (including WAL state).

## Screens and workflow

| Route | Behavior |
| --- | --- |
| `/` | Synthetic factory overview and saved knowledge counts |
| `/machines` | Synthetic machine directory and filtering |
| `/machines/CNC-01` | Synthetic telemetry and approved machine knowledge |
| `/troubleshoot` | Live approved-source retrieval and AI-selected quotes; outcomes saved as pending submissions |
| `/knowledge` | Approved-only source library with literal text filtering |
| `/knowledge/capture` | Saved written observations, attachments and browser audio |
| `/approvals` | Supervisors review/revoke; technicians inspect their own submissions |

1. Sign in as a technician and capture a synthetic observation.
2. Attach optional PDF, TXT, Markdown or supported audio. Four files total including
   voice, at most 10 MiB each. Written observations remain required.
3. Submit. The record and files persist, but the record is excluded from the library.
4. Sign out and sign in as a different supervisor. Open Approvals and review it.
5. Approve: the entry appears in the library. Reject: provide a reason; it stays excluded.
6. Reload or restart the backend: the saved content and decisions remain.
7. To withdraw an approved source, select the Approved tab and revoke with a reason.

The backend derives attribution from the authenticated account. Users cannot submit
an approval status, author name or reviewer identity. A supervisor cannot review
their own submission or their own revision. Review actions target an exact version;
stale or duplicate decisions receive HTTP 409. Edited content becomes a new pending
revision; the previous approved version immediately leaves active knowledge reads.
The revision API requires an explicit new attachment set; it does not silently copy
attachments from the old version.

## API boundaries

All business-data routes require authentication. Health, login, and API documentation
are public; logout is idempotent.
Mutating requests require `X-Shift-Request: 1`; browser origins are allowlisted.
Sessions use HttpOnly, SameSite=Lax cookies, become Secure in production mode, expire
after 12 hours by default, and are invalidated on logout. Only token hashes and
scrypt password hashes are stored. Failed sign-ins are limited per client/username.

- `POST /api/v1/auth/login`, `GET /auth/me`, `POST /auth/logout`
- `GET /api/v1/machines`
- `GET /api/v1/knowledge?q=...&machine=...`: latest approved versions only
- `GET /api/v1/submissions`: own submissions, or all for supervisors
- `POST /api/v1/submissions`: multipart `metadata` JSON and optional `files`
- `POST /api/v1/submissions/{id}/revisions`: same multipart shape
- `POST /api/v1/submissions/{id}/review`: `versionId`, `decision`, `note`
- `GET /api/v1/submissions/{id}/history`: authorized version/review audit history
- `GET /api/v1/documents/{id}`: authorized original source download

- `POST /api/v1/troubleshoot`: authenticated `{machine_id, question}`; approved-source quotes and citations, or explicit insufficient-evidence/error response.

Chunk tables now support retrieval. Conversation history remains deferred. Original
attachments are stored but not extracted; retrieval uses approved written fields.

## Validation

```sh
cd /Users/mohamedshajith/Projects/shift/backend
uv run pytest -q

cd /Users/mohamedshajith/Projects/shift/frontend
npm run lint
npm run build
npm run typecheck
npx playwright install chromium
npm run test:e2e
```

Stop local servers on ports 3000 and 8000 before browser tests. Playwright starts
its own production frontend and backend with a temporary database and test-only
accounts, then stops them. It refuses to reuse a running development server.
Browser tests do not write the development database. The suite runs serially against its isolated synthetic workspace.

Backend tests cover authorization, session expiry, CSRF/origin controls, rate limits,
persistence across app restart, approval filtering, source download authorization,
revision invalidation, self-review prevention, upload validation and migration
idempotency. Browser checks cover all seven routes, complete capture/review flow,
failed-save handling, revocation, accessibility, mobile/tablet layouts and voice UI.
See `docs/STAGE_2_REPORT.md` for measured results and remaining limitations.

## Modular architecture and remaining work

`frontend/src/lib/api.ts` owns typed network calls; `knowledge-provider.tsx` owns
session/workspace state. Page components own presentation. `shift-brand.tsx` is the
replaceable text logo; CSS variables centralize base colors and typography.

SQLite remains the source of truth. LlamaIndex adapters recheck current approval
before inference and delivery. Sentence Transformers supplies local embeddings;
SQLite FTS5 and NumPy provide hybrid retrieval. The modular AMD provider is invoked
only by authenticated troubleshooting. Ragas remains deferred offline evaluation.

Deferred: attachment extraction/transcription, durable indexing jobs, Ragas,
free-form generated maintenance instructions, conversations, recovery and deployment
hardening. This local synthetic MVP makes no production-readiness claim.

## Isolated AMD adapter

`backend/app/inference/` provides async, provider-independent completion contracts
and an AMD-compatible httpx transport. It is called through the narrow RAG service; no raw completion endpoint exists.
`AMDSettings` loads `AMD_API_KEY`, `AMD_BASE_URL`, `AMD_MODEL` and timeout/retry
settings from backend-local configuration. Secrets are excluded from settings dumps.
No adapter constructor, health check or startup hook sends inference requests.

The current configured model is unchanged. Model switching uses `AMD_MODEL`; no
automatic provider/model fallback occurs. See `docs/AMD_ADAPTER_REPORT.md` for retry
semantics, validation results and limitations. Run mocked tests with:

```sh
cd /Users/mohamedshajith/Projects/shift/backend
uv run pytest tests/test_amd.py -q
```
