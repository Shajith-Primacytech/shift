# SHIFT — Stage 2 Completion Report

Date: 2026-10-15. Stage 2 is complete for review. Stage 3 has not started.
No commits, pushes, deployments, paid services or external AI calls were made.

## Delivered

- Persistent SQLite source of truth with versioned transactional SQL migrations.
- Six seeded synthetic machines and six initial synthetic knowledge examples.
- Administrator-provisioned technician/supervisor accounts; scrypt password hashes.
- Opaque, hashed, expiring sessions; HttpOnly cookies; logout revocation; login
  throttling; explicit CORS origins and mutation origin/custom-header checks.
- Persistent knowledge versions supporting machine, symptoms, problem, root cause,
  resolution, safety notes, source attribution, timestamps and approval status.
- Atomic storage of submissions and original attachments, with SHA-256 checksums.
- Backend-enforced supervisor approval, rejection and revocation with review history.
- Prevention of self-review, spoofed attribution, stale decisions and duplicate review.
- New revisions become pending and remove old approval from active technician reads.
- Approved-only knowledge API and authenticated, permission-checked source downloads.
- Frontend sign-in, persistent capture/review/library workflow and useful error states.
- Dedicated text-based ShiftBrand component, base typography tokens, typed API client
  and separate knowledge/session provider. Existing seven routes and visual design retained.
- Schema foundations for source chunks and troubleshooting conversations/messages.

The implementation uses standard-library SQLite and ordered SQL migrations instead
of adding SQLAlchemy/Alembic now. This meets the reproducible schema requirement
with fewer runtime dependencies; it does not change the approved storage boundary.
The only newly added backend runtime package is python-multipart for source uploads.

## Measured validation

| Check | Result |
| --- | --- |
| Backend `uv run pytest -q` | 18 passed, 2.33 seconds |
| Frontend `npm run lint` | Passed |
| Frontend `npm run typecheck` | Passed |
| Frontend `npm run build` | Passed; all required routes present |
| Playwright `npm run test:e2e` | 13 passed, 15.9 seconds |
| Python Ruff selected correctness/import checks | Passed |
| `git diff --check` | Passed |

Backend coverage includes restart persistence using a fresh FastAPI app against the
same file, session expiry/logout, hashed credential storage, origin/CSRF rejection,
login throttling, cross-user boundaries, version history, approval/rejection/revocation,
source-file visibility, self-review including supervisor-authored revisions,
spoofed identities, invalid uploads, rollback and idempotent migrations.

Browser tests use an isolated temporary database and test-only accounts. They cover
capture with attachment → supervisor sign-in → approval → library → reload persistence;
source download; rejection; revocation; failed saves; guided demo outcomes; all seven
routes; automated WCAG checks; 390px/768px layout overflow; mobile keyboard focus;
microphone denial and a synthetic MediaRecorder stream. No real microphone was used.
Mobile screenshot was visually inspected. Automated accessibility checks are not a
complete manual accessibility audit.

One initial new browser assertion matched Next.js's route announcer as well as the
form alert. The selector was scoped to the capture form; the final full suite passed.
A non-failing Starlette/httpx TestClient deprecation warning remains. Browser tooling
also emits a non-failing FORCE_COLOR/NO_COLOR warning.

## Architecture adopted for future stages

LlamaIndex is the primary RAG framework; SQLite remains authoritative. Sentence
Transformers provides local embeddings. SQLite FTS5 and local exact vector search
feed approval-aware hybrid retrieval. Stable version/chunk/document attribution and
final citation validation remain mandatory. AMD inference stays modular and requires
verification of endpoint, credentials, available models and free allowance. Ragas runs
in a separate offline evaluation environment alongside deterministic tests.

The architecture, RAG design, decisions and roadmap now record these choices.
No LlamaIndex, embeddings, Ragas, extraction or inference package was installed.
No RAG quality, groundedness, embedding memory or model latency score is claimed.

## Explicit limitations and handoff

- This is a local synthetic hackathon application, not an industrial control system.
- Machine directory/telemetry presentation remains based on synthetic fixtures;
  the database also persists those machines. There is no live telemetry connection.
- Troubleshooting remains a clearly labeled fixed demo guide. Outcomes persist,
  but no AI answer, semantic retrieval or source-grounded generation occurs yet.
- Files persist as bounded SQLite BLOBs; parsing, OCR and transcription are deferred.
- The API supports revisions and review history; dedicated revision/history UI is
  future work. Capture currently uses free-form text; structured fields are API-ready.
- Chunk/conversation tables exist, but no chunk ingestion or conversation API exists.
- Draft editing, index jobs, reindexing and retrieval-time approval gates beyond the
  existing approved knowledge endpoint belong to later stages.
- Accounts require the local administrative CLI. No default development passwords,
  password recovery, public registration or production identity provider is configured.
- Session expiry and revocation are enforced by the backend; cached screen content
  refreshes on navigation/reload or window focus. It is not a live push subscription.
- The local database and session state are not encrypted at rest. Database file
  permissions are restricted; keep the machine and backups private.

## Local review

Frontend: http://localhost:3000
API docs: http://localhost:8000/docs
Health: http://localhost:8000/api/v1/health

Create technician and supervisor accounts with the password-prompting commands in
README.md before signing in. No test credentials are copied into the development
database. API documentation is public locally; business-data endpoints require login.

Stop here for Stage 2 review. Do not proceed to Stage 3 without further approval.
