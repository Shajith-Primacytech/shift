# AMD Gemma knowledge capture integration

Implemented 17 October 2026. The preceding finalized brand work remains intact.

## Implemented behavior

An optional **Structure with AI** action in the existing capture form sends only
its written fields to the existing AMD API adapter. No attachments, audio,
retrieved knowledge or technician identity are sent. The action does not submit,
approve or index knowledge.

Capture pins **Gemma-4-31B-IT** independently of `AMD_MODEL`, so the existing
troubleshooting model, RAG pipeline and provider settings remain unchanged. There
is exactly one outbound request per action, a 1,800-token output cap, no automatic
retries (including 429/connection failures) and no fallback. The existing configured
backend timeout applies. A per-user 30-second durable admission guard and an
in-flight application lock reduce duplicate calls and unnecessary cost.

The shared completion contract now accepts an optional `response_format`.
Capture requests strict JSON Schema output. Calls without it, including existing
troubleshooting calls, keep their original HTTP payload.

The ten categories are machine/equipment context, symptoms, fault codes, operating
conditions, observations, confirmed root cause, actions performed, observed outcome,
verification steps and safety considerations. Gemma returns named-source exact
excerpts. The backend rejects malformed/fenced JSON, missing/extra fields, wrong
types, excessive lengths, absent observations, invented excerpts and unexpected
returned model IDs. Unknown information stays blank. No generated maintenance
advice or free-form interpretations are accepted. AI categorization is explicitly
labeled as a proposal; technician edits are attributed to technician review.

The technician can edit all ten fields. Editing invalidates the confirmation
checkbox. Changing the original source makes the proposal stale and prevents its
submission. The user must review/confirm the current structure or discard it and
continue manually. Server-side source equality, run ownership, success and one-use
checks back up these UI rules. All fields fit the existing domain schema before
acceptance.

## Persistence and approval

`SubmissionFields` extracts the existing domain schema into a reusable module.
`Submission` adds one optional `aiReview` envelope. Ordinary submissions retain
their existing behavior and required fields.

The additive migration `003_capture_ai.sql` creates a separate run receipt table;
it does not rewrite existing knowledge or review tables. Receipts preserve the
original normalized submission, AI excerpt proposal, execution metadata and
technician-reviewed structure. Original written content stays in the original
version's `content`; reviewed categories map into the existing `problem`,
`root_cause`, `resolution`, and `safety_notes` columns. This lets the unchanged RAG
indexing path include the reviewed categories only after approval. The association
between receipt and version is transactional and single-use.

Existing role permissions, independent-review requirement, review audit events,
revision invalidation and latest-approved retrieval checks are unchanged. AI drafts
and failures never create knowledge versions or review events. Submitted AI-assisted
knowledge is always **Pending**. Only an authorized, different supervisor may
approve it. Supervisor review shows the original observation and reviewed structure
together; the library reader shows them after approval. Execution details are
collapsible in both places.

Failures preserve the form, show a fixed sanitized error, and allow ordinary manual
submission. Failed run metadata remains in the separate receipt table; unsaved
proposals are not automatically recovered into the UI after reload.

## Sanitized execution metadata

Each accepted AI action records provider (`AMD Token Factory`), requested model,
returned/expected model ID, UTC request timestamp, measured latency, token counts
when available, success/failure, provider HTTP status and safe failure category.
If the provider omits its model ID, `model_id` uses the explicitly requested model.
Failures before a completion may lack usage or an upstream HTTP status. Interrupted
processes leave an interrupted receipt rather than inventing a success.

No credential, authorization header, raw provider error, reasoning text or system
prompt is saved in execution metadata or exposed in the UI. Original technician
source data is stored separately as required for provenance and normal review.

## Validation

### Mocked/offline

- Backend: **120 tests passed**, including **25 new capture regression cases**.
- Frontend: lint, TypeScript validation and production build passed.
- Browser: **18 tests passed**: all 15 existing workflow tests plus three new AI
  capture cases. AMD responses in browser tests use the existing adapter with
  `httpx.MockTransport`; they are not live inference claims.
- New tests cover successful JSON/excerpt validation, malformed and fenced JSON,
  missing/extra fields, fabricated excerpts, wrong types/lengths/model,
  unsupported structured-output requests (400/422), authentication errors,
  rate limits, read/connect timeouts and connection failures without retries.
- API/domain coverage includes explicit confirmation, edited structure persistence,
  stale originals, run ownership and single use, session revocation during inference,
  authentication/CSRF, unknown machines, duplicate-call cost guard, and manual
  capture following AI failure.
- Approval/RAG regression verifies no draft knowledge record, Pending exclusion,
  technician denial, independent supervisor approval, inclusion on the next query,
  unchanged audit trail, revocation exclusion and provenance after app restart.
  Existing suite also covers rejection, self-review and revision invalidation.
- Browser tests exercise editing/confirmation, source changes/discard, failure
  metadata/manual submission, persisted metadata, supervisor approval and library
  display. Axe checks passed with AI fields visible. New expanded capture UI was
  checked for overflow at 390px, 768px and 1440px; its screenshot was inspected.
- The normal 3000/8000 ports were already in use. Tests ran against a production
  frontend and temporary synthetic backend/database on ports 3001/8001, without
  stopping the user's servers or changing the development database. Temporary
  port-adjusted suite/config copies were removed. Production assets were rebuilt
  afterward with the normal API configuration.
- Existing dependency warning: Starlette's test client reports an httpx deprecation;
  it does not fail the tests.

### One live integration smoke test

Exactly **one** AMD completion request was made through the new authenticated
`POST /api/v1/capture/structure` endpoint, with synthetic text and a temporary
database. No retries, fallback or further live requests were performed.

- HTTP **200**; actual model **self-dploy/Gemma-4-31B-IT**.
- Strict JSON output accepted and all ten categories validated.
- Latency **9,787.2 ms**.
- Tokens: **309 prompt + 203 completion = 512 total**, reasoning tokens 0.
- Subsequent normal submission: HTTP **201**, status **Pending**.
- Original observation preserved, unknown confirmed root cause left blank, and
  submission absent from the approved library.

Sanitized machine-readable evidence: `docs/GEMMA_CAPTURE_LIVE.json`. The temporary
smoke database was removed; development users/data were not changed.

## Files added

- `backend/app/capture/__init__.py`
- `backend/app/capture/service.py`
- `backend/app/api/capture.py`
- `backend/app/storage/capture_schema.py`
- `backend/migrations/003_capture_ai.sql`
- `backend/tests/capture_fakes.py`
- `backend/tests/test_capture.py`
- `frontend/src/lib/capture-structure.ts`
- `frontend/src/components/capture-ai.tsx`
- `frontend/src/components/capture-execution.tsx`
- `frontend/src/components/saved-capture-details.tsx`
- `frontend/tests/capture-ai.spec.ts`
- `docs/GEMMA_CAPTURE_LIVE.json`
- `docs/GEMMA_CAPTURE_REPORT.md`

## Existing files modified for this feature

- `backend/app/inference/contracts.py`: optional JSON output contract.
- `backend/app/inference/amd.py`: serialize optional response format.
- `backend/app/api/storage.py`: validate/bind reviewed run and serialize provenance.
- `backend/app/main.py`: register authenticated capture router.
- `backend/.env.example`: document independent model pin; no real secret changes.
- `backend/tests/e2e_server.py`: offline capture provider override.
- `backend/tests/test_amd.py`: update exact route allowlist.
- `backend/tests/test_storage.py`: account for third idempotent migration.
- `frontend/src/components/knowledge-capture.tsx`: optional structuring/review state.
- `frontend/src/components/ui.tsx`: optional disabled state for reused checklist.
- `frontend/src/app/approvals/page.tsx`: display saved AI structure/evidence.
- `frontend/src/components/knowledge-library.tsx`: display saved structure/evidence.
- `frontend/src/lib/api.ts`: typed structuring call and sanitized error metadata.
- `frontend/src/lib/demo-data.ts`: optional saved provenance type; no data changes.
- `README.md`: feature setup/demo reference.

No changes were made during this feature to finalized logo assets, colors, global
layout CSS, demo data, embeddings, retrieval logic or existing review rules. Earlier
uncommitted branding changes remain in the working tree and are separate from
this feature's file list.

## Limitations

- Written text only: attachment extraction and speech transcription remain deferred.
- This is evidence-grounded organization, not a diagnosis, safety verifier or
  guarantee of correct categorization. An exact quote can still be misplaced or
  omit context; technician review and independent supervisor judgment are required.
- User edits are validated for schema/length, not automatically verified as true.
- Unsupported JSON-schema responses fail clearly; no hidden second request tries
  another format or model. Oversized/truncated outputs require manual capture or
  a deliberately requested smaller input after the guard interval.
- One live synthetic sample demonstrates connectivity and the integrated path;
  it does not establish general maintenance accuracy or service reliability.
- Receipts persist locally; draft recovery, cleanup/retention controls and
  multi-instance request queues are not implemented in this phase.

## Exact demonstration steps

1. Use your existing backend-only key in ignored `backend/.env`. Do not paste a key
   into chat/source or set a `NEXT_PUBLIC_` secret. No model-setting change is needed.
2. Restart the backend with the repository's normal command from `backend/`:
   `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000`. Startup applies the
   additive migration once.
3. From `frontend/`, run `npm run build` and `npm run start`. Use the same hostname
   for frontend and API. Open `http://127.0.0.1:3000`.
4. Sign in as your existing technician. Open Knowledge capture. Choose CNC-01,
   enter a title and symptom, and write synthetic observations. For example:
   "Synthetic observation: vibration was noticed after a tool change. The root
   cause is not confirmed. Inspection has not yet been performed."
5. Select **Structure with AI** once. Inspect the proposed categories beside the
   unchanged original. Missing fault codes/known root cause should stay blank.
   Edit a category if needed. Expand **AI execution** to show AMD, actual Gemma
   model, timestamp, latency, token counts and success.
6. Confirm **I reviewed and edited this proposed structure…** and choose
   **Submit for review**. Show Pending status and exclusion from the library.
7. Sign out; sign in as a different supervisor. Open Approvals, select the
   submission, compare its original and structured fields, inspect execution
   evidence, then approve or reject using the unchanged review actions.
8. After approval, find the record in the knowledge library and its structured
   details. Only this latest approved version is eligible for ordinary RAG retrieval.
9. To demonstrate safe manual capture without another API charge, show the
   discard action on an existing proposal or the mocked failure regression test.
   Real provider failures also leave the original text and manual submission intact.
