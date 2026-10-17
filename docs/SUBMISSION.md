# SHIFT — Industrial Knowledge Intelligence

AMD Developer Hackathon ACT III submission draft. Deadline supplied by the team:
Sunday, October 18, 2026. Local synthetic MVP; final publication awaits approval.

## Project overview and problem

Factory troubleshooting often depends on experience held by individual technicians.
Shift changes, fragmented notes and staff turnover can make that experience difficult
to find or assess. A plausible answer is not enough: technicians need to know which
machine a procedure applies to, who reviewed it and where the supporting evidence
came from. SHIFT demonstrates a workflow for retaining that knowledge and making
approved evidence inspectable during troubleshooting.

## Solution and users

Technicians capture written observations, machine context and supporting attachments.
Supervisors review exact versions, approve or reject submissions, and revoke outdated
knowledge. Authenticated technicians ask a machine-specific question and receive
AI-selected quotations from currently approved sources with inspectable citations.
Outcomes can be saved as new pending submissions, closing the human review loop.

Primary users: maintenance technicians, shift supervisors and maintenance leads.
All factory assets, telemetry and maintenance examples in this demonstration are
synthetic. SHIFT is decision support, not machine control or maintenance authorization.

## Architecture and stack

```text
Next.js / TypeScript / Tailwind / Lucide
  → FastAPI authenticated session + machine-scoped question
  → SQLite latest approved source versions
  → LlamaIndex SentenceSplitter + custom BaseRetriever
  → local Sentence Transformers MiniLM + SQLite FTS5
  → NumPy cosine similarity + reciprocal-rank fusion
  → bounded AMD DeepSeek chat completion selecting passage IDs
  → server validates IDs, exact quotations, current approval and session
  → source-linked quotations in the existing troubleshooting screen
```

SQLite is the source of truth for users, hashed sessions, immutable content versions,
review events, original attachments and derived chunks/vectors. There is no hosted
vector database. Local administrator-provisioned accounts use scrypt passwords and
HttpOnly session cookies. Supervisor review is enforced by the backend; authors
cannot approve their own submissions. Branding and presentation remain reusable
frontend components, independent of retrieval and provider contracts.

## AMD Developer Cloud integration

The working model is **DeepSeek-V4-Flash**, invoked through an asynchronous httpx
adapter at the verified AMD API base `https://developer.amd.com.cn/radeon/api/v1`,
using `POST /chat/completions` and a backend-only Bearer credential. Configuration
uses AMD_API_KEY, AMD_BASE_URL and AMD_MODEL. There is no raw public inference route.
The provider interface isolates the rest of the application from AMD transport.

Connection, read and overall deadlines default to 5s, 45s and 55s. Bounded retries
apply to connection/pool failures and rate limiting; ambiguous completion timeouts
are not automatically replayed. Provider errors are sanitized and withhold answers.
No automatic switch to another model or canned guidance occurs.

Gemma received a separate connectivity probe earlier, but is **not** the model in
the verified end-to-end workflow. No claim of local AMD GPU execution, dedicated
hardware performance or unrestricted free service availability is made. Inference
uses the team's available hackathon access; live network and provider quota matter.

## LlamaIndex RAG implementation

The selective open-source packages are llama-index-core and its Hugging Face
embedding integration, with Sentence Transformers and NumPy. LlamaIndex Documents,
SentenceSplitter and BaseRetriever are used directly; SHIFT owns SQLite eligibility
queries and the final passage-validation service.

Approved written record fields are chunked at 180 embedding tokens with 25 overlap.
Local `all-MiniLM-L6-v2` is pinned to revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, producing normalized 384-dimensional vectors
on CPU. Preparation downloads the public model once; retrieval uses the local cache.
SQLite FTS5 keyword ranking and exact vector cosine search both operate. Reciprocal
rank fusion selects at most five chunks, with a conservative lexical-overlap and
cosine threshold gate. Queries over 240 embedding tokens are rejected.

This is a narrow **extractive RAG workflow**: DeepSeek selects supplied passage IDs;
the server displays original source text, preserving source order within each chunk.
It does not generate unrestricted maintenance procedures. Selection relevance and
completeness are not guaranteed by exact quotation validation.

## Approval gating and citations

Both retrieval branches require the latest revision to be Approved and match the
selected machine. Pending, rejected, revoked and superseded records are ineligible.
Lazy indexing publishes a version atomically after rechecking approval. Cached index
metadata never overrides SQLite. Fresh checks before inference and before response
return validate current status, machine, source fingerprint and chunk content hash.
Invented source IDs or passage IDs are rejected. The server supplies citation titles,
record IDs, version IDs, chunk IDs and excerpts from the retrieved evidence.

Authorization is checked at request/response time; an already displayed quotation is
not remotely erased by a later revocation. Refresh/requery after review changes.
The app is a single authenticated workspace, not a multi-tenant industrial access
control system. Citation validity proves provenance, not a safe or complete diagnosis.

## Tested capabilities and measured results

Final acceptance on October 17, 2026:
- 95 backend tests passed, including storage, auth, review, adapter and RAG checks.
- 15 browser tests passed across all seven routes, capture/review/library persistence,
  citations, no-evidence handling, timeout UI, accessibility and responsive layouts.
- Frontend lint, typecheck and production build passed.
- Six real MiniLM retrieval fixtures matched expected source sets (6/6); four additional
  warmed-index outbound-request checks excluded pending/rejected/revoked/superseded
  sources while retaining valid approved citations.

The six retrieval durations in the final preparation run were 6496.7ms (cold model load),
26.1ms, 26.0ms, 13.0ms, 0.9ms and 12.1ms. This is a tiny synthetic check, not a
retrieval-quality benchmark or latency distribution.

The final live browser rehearsal returned HTTP 200 with
`self-dploy/DeepSeek-V4-Flash`: 12659ms provider latency, 574 input + 128 output =
702 tokens, with valid SOP-001 and NOTE-002 citations displayed. CNC-02 returned
insufficient evidence with no model usage or citations. The earlier Stage 3 browser
run took 7325.9ms / 719 tokens; an initial 20s-read probe timed out. These are
individual observations, not service guarantees. The credential's successful use
does not resolve its PENDING rotation requirement. Automated browser tests use
mocked AMD responses; the separately reported live run verifies the real pipeline.

## Limitations and roadmap

Implemented: synthetic written knowledge capture, persisted attachments and browser
voice recordings, human review, approved-only hybrid retrieval, AI-selected quotations,
source validation and outcome logging. Stored audio/PDFs are not transcribed or
parsed for retrieval. Telemetry is simulated, not connected to equipment.

Deferred: document extraction/OCR/transcription, durable background indexing,
conversation history, free-form answer synthesis, production deployment hardening
and Ragas evaluation. Ragas, Recall@5, MRR, faithfulness scores, branch ablations and
peak memory benchmarks were not run. No downtime reduction or industrial accuracy
percentage has been measured. The relevance gate may reject valid paraphrases.

Next work requires review; no additional phase is underway. Near-term priorities
are a presenter rehearsal, credential-rotation confirmation and submission packaging.
See DEMO_GUIDE.md for launch/reproduction and FINAL_ACCEPTANCE.md for release gates.

## Suggested submission description

SHIFT helps maintenance teams retain technician experience across shifts. Technicians
capture machine-specific observations; supervisors approve exact versions before they
become searchable evidence. Our local-first MVP combines FastAPI and SQLite with
LlamaIndex, local Sentence Transformers embeddings, and keyword/vector retrieval.
AMD Developer Cloud's DeepSeek-V4-Flash selects relevant passages from approved
synthetic maintenance records. SHIFT verifies their citations and returns exact
source quotations, with explicit uncertainty and no answer when evidence is missing.
The responsive Next.js interface connects capture, review, troubleshooting and
outcome logging. Validation includes 95 backend tests, 15 browser tests, six local
embedding fixtures and a successful live AMD browser demonstration. This is
inspectable, human-reviewed decision support—not autonomous machine control.


## Security status for the presenter

AMD credential rotation: **PENDING**, intentionally deferred. Private repository
preparation is authorized, but this does not resolve the exposure risk. No secrets
are included in the submission source. Do not claim the exposed credential is safe.
The final preparation report supersedes the earlier acceptance status and records
current tests and the authorized private repository commits.
