# SHIFT — Stage 3 vertical slice report

Historical Stage 3 validation, October 17, 2026. For final private repository
preparation, current checks and PENDING credential rotation, see FINAL_ACCEPTANCE.md.

## Delivered

Authenticated technician question → current approved machine-scoped records →
LlamaIndex chunks → local MiniLM vectors + SQLite FTS5 → reciprocal-rank fusion →
AMD DeepSeek passage selection → server-verified source IDs and exact quotations →
existing troubleshooting UI. Outcomes remain pending Stage 2 submissions.

The answer contract is deliberately extractive: AMD selects supplied passage IDs;
SHIFT copies original text and preserves its order within each source. This is real
model inference, labeled “AI-selected approved guidance,” not free-form diagnostic
generation or a renamed canned answer. Source quotations do not prove a diagnosis.

Approval is checked in SQL before retrieval, before inference, and after inference.
Pending, rejected, revoked and superseded versions are ineligible, including cached
vectors. Index publication rechecks approval transactionally. Machine selection is
mandatory; the client cannot inject evidence. Session validity is checked again at
response delivery. Invalid citations, provider failures and insufficient evidence
produce no maintenance answer. A single-process request lock returns 429 while busy.

## Changes in this milestone

Created:
- `backend/migrations/002_rag.sql`: derived index generations, vectors and FTS5.
- `backend/app/rag/__init__.py`, `embeddings.py`, `retrieval.py`, `service.py`,
  `prepare.py`, `evaluate.py`: pinned local model, LlamaIndex retrieval, validated
  passage selection, explicit preparation and reproducible offline evaluation.
- `backend/app/api/troubleshooting.py`: authenticated narrow endpoint.
- `backend/tests/test_rag.py`, `rag_fakes.py`, `data/rag_cases.json`: mocked transport,
  authorization/citation/index tests and real-embedding evaluation fixtures.
- `frontend/src/components/grounded-answer.tsx`: live answer/source/error presentation.
- This report.

Modified:
- `backend/app/main.py`: register troubleshooting router.
- `backend/app/config.py`, `.env.example`: read timeout 45s, overall timeout 55s.
  Existing local credentials and configured model were not changed.
- `backend/pyproject.toml`, `uv.lock`: selective LlamaIndex, Sentence Transformers,
  NumPy and locked transitive dependencies; existing httpx runtime retained.
- `backend/tests/test_amd.py`, `test_storage.py`, `e2e_server.py`: new endpoint/schema
  expectations and isolated RAG browser fixtures (live mode opt-in).
- `frontend/src/lib/api.ts`, `components/troubleshooting.tsx`, `app/globals.css`,
  `tests/workflows.spec.ts`: typed 75s request, live evidence, source styles and tests.
- README, architecture, RAG design, roadmap, decisions and handoff documentation.

Existing Stage 2 files were already largely untracked. Do not discard the working
folder because it is uncommitted. The local database gained only additive index
schema/data during preparation; browser tests used separate temporary databases.

## Actual validation results

- Backend: 95 tests passed, including all existing adapter/storage tests.
- Browser: 14 passed; all seven routes, capture → supervisor approval → library,
  rejection, revocation, logged outcome, provider timeout without demo fallback,
  keyboard/accessibility and mobile/tablet checks.
- Frontend lint, TypeScript and production build passed. After the final source-order
  fix, the focused grounded browser workflow also passed (1/1).
- Real local MiniLM retrieval: 6/6 expected-record-set checks passed. Approved CNC-01,
  PRESS-01 and ASSY-01 positives; unrelated question, pending-only CNC-02 and
  wrong-machine subject negatives. Run `uv run python -m app.rag.evaluate`.
- Measured retrieval durations for that run: cold 5982.5ms; remaining cases 23.6,
  23.4, 11.5, 2.7 and 11.7ms. Tiny fixtures, not throughput or accuracy benchmarks.
- Actual outbound mock-transport requests were inspected: pending/rejected/revoked
  sentinel records and other-machine records never entered the model prompt.
- Revocation during inference discards the answer; malformed/invented citations,
  provider authentication/network/timeout failures, no evidence and long queries
  are tested. Unit embeddings are explicitly test doubles; real semantic checks
  are the separate six-case evaluation and live requests.

### Live AMD observations

| Probe | Outcome | Inference latency | Token usage |
| --- | --- | ---: | --- |
| Initial adapter, old 20s read limit | Timeout; no automatic replay | 20611.9ms observed | unavailable |
| Separate minimal adapter probe, increased bounded timeout | Success, “OK” | 9419.6ms | 9 input + 2 output = 11 |
| Grounded RAG service, passage IDs | Success, four SOP-001 quotes | 18135.4ms | 579 input + 145 output = 724 |
| Authenticated live browser/API request | HTTP 200; four quotes, one displayed valid SOP-001 citation | 7325.9ms | 574 input + 145 output = 719 |

Successful responses identified `self-dploy/DeepSeek-V4-Flash`; configured request
model remains `DeepSeek-V4-Flash`. Reasoning usage was zero in these successful
responses. Individual observations are not service guarantees. An earlier free-quote
RAG probe failed exact-quote validation and correctly withheld its answer; the final
contract selects server-defined passage IDs instead. Browser inspection additionally
led to server-enforced source ordering, covered by a regression test.

## Security and resource checks

The six Git-tracked files contained zero exact matches for the configured API key;
no `.env`, database, private key or certificate file was tracked. `backend/.env` is
ignored and mode 0600. A second scan covering all 84 tracked and unignored files
also found zero exact credential matches. No credential values were printed, sent to the frontend or
added to documentation. Test tokens/accounts are synthetic and isolated.

Model: `sentence-transformers/all-MiniLM-L6-v2`, revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, CPU, normalized 384 dimensions.
Chunks use 180 tokens/25 overlap; queries over 240 embedding tokens are rejected.
A 384-float vector occupies 1536 bytes before metadata. Peak RSS was not measured.
One cached embedding model and one API worker are intended for this 8GiB machine.
Runtime downloads are disabled; `prepare` explicitly downloads the public model.
Locked versions include LlamaIndex core 0.14.25, Hugging Face integration 0.8.0,
Sentence Transformers 6.1.0 and NumPy 2.5.4. No paid/hosted vector service was added.

## Launch and demonstration

From `backend/`:

```sh
uv sync --locked
uv run python -m app.rag.prepare
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Keep AMD_API_KEY, AMD_BASE_URL and AMD_MODEL in ignored backend/.env. Current
credentials have been tested. If accounts are absent, use README's interactive
`app.manage create-user` commands; there are no default production passwords.
From `frontend/`, in another terminal:

```sh
npm ci
npm run build
npm run start
```

Open http://localhost:3000; backend docs http://localhost:8000/docs.
Use matching hostnames. Sign in, open Troubleshoot, choose CNC-01 and unusual spindle
vibration, then Review evidence. Inspect the source card. Use CNC-02 to demonstrate
insufficient approved evidence. Capture a written synthetic observation, approve it
with a separate supervisor, then ask a matching question on that machine. Newly
approved text indexes on the next query. Revoke it and repeat to show exclusion.
Source selection still depends on relevance; approval alone does not force an answer.

## Deferred and remaining submission risks

No known code blocker remains for this narrow written-knowledge demo. Live AMD
access, free allocation and network availability are external dependencies; one
request already timed out. There is no automatic model switch or synthetic fallback.
Use prepared model cache and a single API worker for rehearsal.

PDF/audio extraction, OCR/transcription, durable indexing queues, conversation
history, broad free-form synthesis and Ragas are deferred. Ragas metrics, Recall@5,
MRR, branch ablations and peak-memory measurements were not run. Six fixtures do
not establish industrial accuracy; lexical-overlap/cosine gates may abstain on
valid paraphrases. Very long single-line passages may be excluded by the bounded
passage selector. Index updates are synchronous and intended for a small corpus.

Approval and citation checks validate provenance, not semantic completeness or
physical safety. All data is synthetic; qualified site procedures remain necessary.
Finish a presenter rehearsal and submission materials. Public hosting, committing
and deploying still require user approval. Stop here for review.
