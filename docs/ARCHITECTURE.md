# SHIFT — Technical Architecture

## Implementation status

Stage 2 implements SQLite persistence, authenticated sessions, source-file storage,
versioned knowledge submissions, and supervisor approval. Factory data is synthetic.
The approved Stage 3 vertical slice now implements LlamaIndex chunking/retrieval,
local MiniLM embeddings, SQLite FTS5/vector fusion, and AMD-selected source quotes.
Attachment extraction, Ragas and conversation history remain deferred.
See STAGE_3_REPORT.md for validation and implementation boundaries.

## System boundaries

```text
Next.js UI → typed API client → FastAPI authentication and domain services
                                      │
                                      └─ SQLite source of truth
                                           machines, users, sessions
                                           records, immutable content versions
                                           documents, review history
                                           chunk and conversation schema

Implemented Stage 3 slice:
approved version → LlamaIndex ingestion → local Sentence Transformers
                 → SQLite chunks/vectors/FTS5
question → approval-aware SQLite retrievers → LlamaIndex hybrid RAG
         → modular verified AMD provider → validated source citations
```

The frontend uses reusable UI components, a separate `ShiftBrand` text logo,
CSS design tokens, and a typed API module. Visual changes do not alter database,
authorization, retrieval, or inference contracts. Further token consolidation can
happen independently of the backend.

## Stage 2 storage and services

Python 3.12 / FastAPI / Pydantic. SQLite is accessed through small parameterized
repository operations using the standard library. Ordered SQL migrations provide
reproducible transactional schema setup without an additional ORM dependency.
A future SQLAlchemy adapter can be introduced if relational requirements grow.

- `users`: administrator-provisioned technicians and supervisors; scrypt hashes.
- `sessions`: hashes of opaque session tokens with expiry; revocable on logout.
- `machines`: persisted synthetic fixture data; UI telemetry remains simulated.
- `knowledge_records`: stable identity and original owner.
- `knowledge_versions`: revision, submitting user, machine, symptoms, problem,
  root cause, resolution, safety notes, content, timestamps, approval status.
- `review_events`: reviewer identity, previous status, decision, reason, timestamp.
- `source_documents`: original bytes, filename, MIME metadata, size and SHA-256.
- `knowledge_chunks`, `chunk_embeddings`, `rag_generations`, `rag_fts`: derived local index.
- `conversations`, `conversation_messages`: unused foundations; no history API.

Files are stored transactionally as SQLite BLOBs for the small local MVP. Limit:
four attachments per submission (including voice), each at most 10 MiB. Extraction,
OCR, and transcription are deferred. Downloads are authenticated attachments with
nosniff headers, never executable server paths.

## Approval and authentication invariants

- No public role selection or self-registration. Local administrators create users.
- Session cookies are HttpOnly, SameSite=Lax, and Secure in production mode.
- Mutations require a custom request header; browser origins must be allowlisted.
- Author and reviewer identities come from the session, never request payloads.
- Technicians see approved knowledge plus their own submissions in a separate API.
- Only supervisors review; authors/owners cannot approve their own contributions.
- Reviews target the exact version and valid prior state, inside a write transaction.
- Edits create a pending revision; old approval is immediately withdrawn from active
  technician reads. Content history and review events remain available to authorized
  owners/supervisors. Attachments must be explicitly provided on each new revision.
- Rejected, revoked, and superseded sources never appear in `/knowledge`.
- Owners may inspect their own pending sources; this is not trusted retrieval.

## RAG and AMD boundaries

LlamaIndex is the primary open-source RAG framework, not an authorization store.
SHIFT adapters own SQLite persistence, current approval checks and source integrity.
Use local `all-MiniLM-L6-v2` embeddings, SQLite FTS5 keyword ranking, NumPy exact
cosine similarity and deterministic reciprocal rank fusion. Do not introduce a
second authoritative JSON document store or hosted vector service.

AMD inference remains behind a provider interface. DeepSeek-V4-Flash is configured
and live-verified. No automatic model fallback occurs. Authenticated POST
`/api/v1/troubleshoot` retrieves at most five chunks, asks AMD to select passage IDs,
and copies only exact approved source passages into the answer. Invalid IDs,
changed approvals, expired sessions and provider failures withhold the answer.
One in-flight request per process bounds local embedding and provider concurrency;
run a single API worker for this local MVP. Source bodies are untrusted data.

See RAG_DESIGN.md and STAGE_3_REPORT.md for limits and measured checks.
