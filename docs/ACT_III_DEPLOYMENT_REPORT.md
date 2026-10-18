# SHIFT — ACT III deployment preparation

Prepared October 18, 2026 (Asia/Kolkata). Local validation is complete. Public
publication/deployment has **not** occurred. The owner requested a portable bundle;
hosting details will follow. No purchase, new plan or credit top-up was made.

## URLs and release status

| Item | Status |
| --- | --- |
| Existing GitHub repository | https://github.com/Shajith-Primacytech/shift — PRIVATE, visibility unchanged |
| Public repository URL | Pending explicit publication confirmation; existing URL can remain unchanged after approval |
| Public application URL | Not created; Vercel deployment awaits hosting details and confirmation |
| Public backend URL | Not created; persistent hosting resource and HTTPS origin are not supplied |
| Source bundle | `/Users/mohamedshajith/Projects/shift-act-iii-release-2026-10-18.tar.gz` |
| Unpacked public source | `/Users/mohamedshajith/Projects/shift-act-iii-release-2026-10-18/` |
| Deployment instructions | `deploy/README.md` |

The source snapshot includes the current working changes and a SHA-256 file
manifest; it is not a claim that uncommitted changes have been pushed to GitHub.
The `.git` directory, private environments, databases, model caches and test outputs
are excluded. The original repository's entire reachable/reflected history is
scanned separately. Re-run the scan after committing the reviewed release and
before any public visibility change.

## Credentials and history audit

- Existing AMD token retained in `backend/.env`, mode 0600; no rotation requirement
  imposed. Owner acceptance of the current token is respected.
- All remotes/tags fetched. Gitleaks 8.30.1 scanned all refs, reflogs and full history:
  3 commits, 171 file versions. No credential exposure found in history.
- Exact checks against private AMD and judge credentials supplement provider and
  entropy rules. Prepared public source also passed the redacted scanner.
- Compiled frontend static assets, public branding and documentation were checked
  for the current AMD token: no matches. No credential is included in API evidence.
- Private `.env`, judge password file and SQLite database are ignored by Git.
  Backend Docker context and Vercel uploads also exclude private environments.
- Reproducible scan: `scripts/audit_release.py`; evidence:
  `docs/DEPLOYMENT_SECRET_AUDIT.json`. Findings block release and identify only
  affected file/commit/rule, never the matched value.

## Implemented deployment preparation

- Vercel-ready Next.js configuration and same-origin `/api/v1/*` rewrite to a
  server-only `SHIFT_BACKEND_URL`. Production frontend uses relative API requests.
  This preserves the existing HttpOnly/Secure/SameSite=Lax session cookie design
  without weakening authentication. Vercel builds reject missing/non-HTTPS origins.
- Portable FastAPI Dockerfile: Python 3.12, locked dependencies with voice extra,
  pinned public Whisper and MiniLM models, offline runtime model access, unprivileged
  user, health check, one worker, no secrets in image build context and no automatic
  inference at startup.
- Docker Compose: private backend environment, exact required CORS origins, named
  `/data` volume for SQLite/attachments/vectors, loopback API binding and optional
  host TLS ingress template. Existing AMD adapter, schemas, RAG and approval gates
  are reused.
- Idempotent judge provisioning using synthetic fixtures and distinct randomly
  generated passwords stored only in a 0600 private file. Existing roles and
  passwords are never overwritten silently.
- Public source preparation with file hashes; redacted full-history/source audit;
  GitHub Actions validation prepared but not dispatched. No workflow requires live
  AMD access or embeds a credential.
- Explicit local real-service smoke utility, with at most one Gemma completion only
  when `--live-gemma` is supplied. It preserves existing business logic.

## Validation outcomes

| Check | Result / evidence |
| --- | --- |
| Backend automated suite | **147 passed**, including Gemma failure/schema handling, voice errors, RAG exclusion, supervisor permissions, private judge provisioning and production secure-cookie assertions |
| Frontend ESLint | Passed |
| TypeScript | Passed |
| Next.js production build | Passed; final local build uses default local proxy destination |
| Browser suite | **31 passed** against production Next.js proxy → isolated FastAPI on ports 3001/8001; AMD and speech mocked |
| Branding | Both official SVG variants load; all seven main routes checked; responsive login/mobile navigation and image-loading geometry pass; deterministic silhouette overlap 99.46% |
| Real MiniLM retrieval | **6/6 passed**, machine-scoped and irrelevant/no-evidence cases; zero AMD calls |
| Real local Whisper API | HTTP **200**, `Systran/faster-whisper-tiny.en`, English, 5.66-second synthetic audio, **1154.7 ms**, nonempty transcript |
| Live Gemma capture API | Exactly **one** completion, HTTP **200**, `self-dploy/Gemma-4-31B-IT`, **10457.2 ms**, 295 prompt + 168 completion = **463 tokens** |
| Live proposal semantics | Schema validated; unconfirmed root cause stays blank; reviewed submission starts Pending |
| Real approval API smoke | Technician approval 403; supervisor approval 200; Pending and Revoked excluded from approved library |
| Python lock | `uv lock --check` passed |
| Source / patch integrity | `git diff --check` passed |
| Linux container / public edge | **Not run**: Docker absent locally; host and public URLs not supplied |

Sanitized live evidence: `docs/DEPLOYMENT_LIVE_CHECK.json`. Synthetic audio was
used; no judge microphone or private recording was uploaded externally. The one
Gemma call used the existing quota; no credits were purchased or repeated requests
made. All routine tests use fakes. There is one nonfailing Starlette TestClient
httpx deprecation warning.

## Judge access and demonstration

Local synthetic database: `backend/data/hackathon.sqlite3`.

- Technician username: `judge-tech`.
- Supervisor username: `judge-supervisor`.
- Distinct passwords: ignored `backend/data/judge-accounts.env`, mode 0600.
  Share privately with judges; never place this file in the public source bundle.
- Account/password provisioning is verified; local database includes synthetic
  machines, approved seed knowledge, and pending review examples.
- Production account creation runs the same provisioning command inside the
  persistent volume and generates its own private credentials. Local credentials
  are not baked into a container or source archive.

Full demo steps are in `deploy/README.md`: record → transcribe → review transcript →
Structure with AI → review/edit proposal → submit Pending → supervisor approve →
show verified library/RAG; revoke and demonstrate exclusion. Existing troubleshooting
uses the independently configured `AMD_MODEL`; Gemma capture remains pinned.

## Remaining risks and launch gates

1. Supply an existing/free hosting resource with persistent storage; build the Linux
   image and measure CPU/RAM/disk use. Locked ML dependencies make the image large.
   No hosting plan or capacity has been promised or purchased.
2. Validate the actual HTTPS backend and Vercel proxy: Secure cookie round-trip,
   CORS, voice/document upload sizes, request timeouts, model readiness, persistence
   across restart, and a real browser microphone. Local tests do not certify those
   platform behaviors.
3. Confirm final URLs and judge accessibility without a Vercel protection login.
   Repeat source/history scan on the exact final release commit.
4. Owner must explicitly confirm repository publication and public deployment.
   No public URL can honestly be reported before those actions.
5. Existing token rotation remains unavailable and accepted, not a deployment
   blocker. Keep judge access private and monitor available AMD quota during the
   demo; upstream availability and rate limits remain external dependencies.
6. No new source license was selected; public visibility does not itself grant a
   reuse license. Choose one if the submission rules require it.

## Files added/updated during this preparation

- `frontend/next.config.ts`, `frontend/src/lib/api.ts`, `frontend/vercel.json`,
  `frontend/.vercelignore`, `frontend/.env.example`: deployment routing/configuration.
- `frontend/playwright.config.ts`, `frontend/tests/workflows.spec.ts`,
  `frontend/tests/branding.spec.ts`, `backend/tests/e2e_server.py`: proxy-based and
  configurable-port validation with isolated mock services.
- `backend/Dockerfile`, `backend/.dockerignore`: portable backend image definition.
- `backend/app/demo.py`, `backend/tests/test_demo.py`: private judge provisioning
  and production authentication regression coverage.
- `backend/app/deployment_check.py`: bounded explicit real-service smoke.
- `deploy/compose.yaml`, `deploy/Caddyfile`, `deploy/README.md`: persistence and launch bundle.
- `scripts/prepare_public_source.py`, `scripts/audit_release.py`,
  `.github/workflows/validation.yml`: release preparation and automated checks.
- `README.md`, this report, `docs/DEPLOYMENT_SECRET_AUDIT.json`,
  `docs/DEPLOYMENT_LIVE_CHECK.json`: handoff and sanitized evidence.

Earlier uncommitted AI, voice and branding changes are retained in the complete
source snapshot. The private AMD environment and existing developer database were
not modified. No repository visibility, remote source, public application or cloud
account was changed.
