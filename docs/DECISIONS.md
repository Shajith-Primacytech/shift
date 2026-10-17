# SHIFT — Architecture Decision Records

## ADR-001: Frontend Framework

Decision: Next.js with TypeScript and Tailwind CSS.

Reason:
- Modern web application framework.
- Reusable UI components.
- Strong developer ecosystem.
- Suitable for responsive dashboards.

## ADR-002: Backend Framework

Decision: Python with FastAPI.

Reason:
- Strong AI and data processing ecosystem.
- Automatic API documentation.
- Pydantic data validation.
- Easy integration with ML libraries.

## ADR-003: Language Model

Decision: AMD Developer Cloud with DeepSeek-V4-Flash for the working MVP.

Supersedes the original Gemma-first proposal after live endpoint verification.
The end-to-end troubleshooting workflow was verified with DeepSeek. Gemma had a
standalone probe only; it does not power the demonstrated workflow. Switching
AMD_MODEL changes the provider request configuration, but any replacement model
must pass the JSON/citation contract tests before being presented as supported.

## ADR-004: Database

Decision: SQLite for the local MVP; PostgreSQL/pgvector is a future adapter.

Supersedes the initial Supabase-first plan following the approved Phase 2 audit.

Reason:
- Relational storage for structured records.
- Local float32 vectors with exact NumPy similarity.
- SQLite FTS5 keyword search in Stage 3.
- No hosted account or paid service prerequisite.

## ADR-005: Embedding Model

Decision:
sentence-transformers/all-MiniLM-L6-v2

Reason:
- Open-source embedding model.
- Runs locally.
- Produces 384-dimensional vectors.
- Avoids paid embedding API costs.

## ADR-006: Retrieval Architecture

Decision: Approval-gated hybrid RAG.

Components:
- Vector similarity retrieval
- Keyword retrieval
- Machine metadata filtering
- Approval filtering
- Reciprocal Rank Fusion
- Source-aware answer generation

Reason:
Combines semantic understanding with
exact technical term matching.

## ADR-007: Human Approval

Decision:
Submitted written knowledge must be reviewed before authoritative indexing.
AI extraction is deferred.

Reason:
Prevent unverified AI output from becoming
trusted factory maintenance knowledge.

## ADR-008: Agent Framework

Decision:
Use explicit Python domain services and LlamaIndex as the primary RAG framework.
The narrow Stage 3 slice implements chunking, embeddings and retrieval; SHIFT
validates AMD passage selection. General synthesis remains deferred.
Authorization and persistence remain SHIFT-owned. No agent orchestration.

Reason:
- Easier debugging.
- Lower complexity.
- Better testability.
- No unnecessary orchestration dependency.

Install selective LlamaIndex packages; explicitly configure local embeddings and
verified inference. Keep Ragas evaluation in a separate environment.

## ADR-009: Document Processing

Future candidate: PyMuPDF for text-based PDFs, subject to license review.
Not installed or used in the submitted MVP; attachment extraction is deferred.

Reason:
- Practical PDF text extraction.
- Page-level provenance.
- Suitable for the hackathon MVP.

Scanned PDF OCR is deferred.

## ADR-010: Development Workflow

Decision:
GitHub for version control and Codex
for AI-assisted implementation.

Rules:
- One milestone at a time.
- Test before committing.
- Never commit secrets.
- Review Codex changes.
- Push validated milestones to GitHub.

## ADR-011: Budget

Decision:
Zero out-of-pocket development budget.

Use:
- Open-source libraries
- Local development
- Available free hosting
- SQLite local storage
- Verified AMD hackathon credits

Do not introduce paid infrastructure
without explicit approval.

## ADR-012: Product Safety

Decision:
SHIFT is a decision-support system,
not an autonomous machine controller.

Requirements:
- Ground answers in approved evidence.
- Display source citations.
- Communicate uncertainty.
- Avoid fabricated specifications.
- Never recommend bypassing safety systems.
- Require qualified technician judgment.

## ADR-013: Stage 2 persistence and identity

Use standard-library SQLite with ordered transactional SQL migrations. This is the
reproducible-schema equivalent for the MVP; SQLAlchemy/Alembic are not required yet.
Use administrator-created accounts, scrypt password hashes, hashed opaque sessions,
HttpOnly cookies, origin checking and a required custom header for mutations.
Versions retain immutable content; authenticated supervisors append review events.
Only the latest approved version is eligible for technician knowledge reads.
Store source bytes and checksums transactionally in SQLite for the bounded local MVP.
No parsing, embeddings, indexing or AI generation in Stage 2.

## October 17, 2026 — Approved Stage 3 MVP slice

Implement the authenticated written-knowledge RAG path now, preserving Stage 2.
LlamaIndex custom retrieval uses pinned local MiniLM embeddings and SQLite FTS5
with reciprocal-rank fusion. Current latest approval and machine scope are checked
in SQL, before inference, and before delivery. SQLite remains authoritative.

For the deadline, AMD DeepSeek selects bounded passage IDs rather than producing
free-form maintenance instructions. The backend returns only exact source quotes
with verified citations, preserving source order. Missing evidence, invalid output
or failed inference produces no answer. Ragas, attachment extraction and background
indexing remain deferred. See STAGE_3_REPORT.md for actual validation and limits.
