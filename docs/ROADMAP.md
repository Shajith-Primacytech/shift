# SHIFT — Implementation Roadmap

Budget: zero additional spending. Synthetic factory data only.
No commits, pushes or deployment without explicit approval.

## Completed foundation

Seven responsive Next.js routes, reusable UI, FastAPI health endpoint, synthetic
telemetry and explicitly labeled demonstration troubleshooting.

## Phase 2 / Stage 1 — Audit

Completed: repository inspection and approved SQLite/LlamaIndex architecture.

## Phase 2 / Stage 2 — Persistent storage and approval

Implement SQLite migrations and synthetic seed data; local accounts and sessions;
versioned knowledge and source-file storage; authenticated supervisor review;
review audit history; approved-only knowledge reads; frontend persistence integration.
Validate restart persistence, role boundaries, rejection/revocation, stale reviews,
source download authorization, all seven routes, lint, build and backend tests.
Deliver a completion report and stop for review.

## Phase 2 / Stage 3 — Document ingestion and RAG

Approved narrow slice completed: approved written-record ingestion, LlamaIndex
token-aware chunks, local embeddings, SQLite vectors/FTS5 fusion, AMD-selected
source passages, validated citations and existing troubleshooting UI integration.
See STAGE_3_REPORT.md. Stop for review before further implementation.

PDF/audio extraction, durable ingestion jobs, free-form generation and Ragas are
deferred. The items below describe broader follow-up work, not current blockers
for the demonstrated synthetic written-knowledge workflow.

## Later stages

Completed before final acceptance: modular AMD inference, grounded quote selection,
source validation, current approval checks and frontend integration.

Deferred after review: attachment extraction/transcription, durable indexing jobs,
Ragas and broader retrieval evaluation, conversation history, deployment hardening.
No new implementation phase is authorized. Current work is acceptance, presenter
rehearsal, documentation and submission preparation only.

SQLite is the MVP source of truth. PostgreSQL/pgvector migration is optional future
work, not a prerequisite. Hosting and public deployment require separate approval.
