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

Decision: Gemma through AMD Token Factory.

Reason:
- Alignment with AMD hackathon technology.
- Available hackathon inference resources.
- Supports structured knowledge extraction
  and evidence-grounded answer generation.

Requirement:
Verify the exact model, endpoint, and quota
before implementing the production client.

## ADR-004: Database

Decision: Supabase PostgreSQL with pgvector.

Reason:
- Relational storage for structured records.
- Vector similarity search.
- PostgreSQL full-text search.
- Suitable free-tier starting point.

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
AI-extracted maintenance knowledge must
be reviewed before authoritative indexing.

Reason:
Prevent unverified AI output from becoming
trusted factory maintenance knowledge.

## ADR-008: Agent Framework

Decision:
Use explicit Python services initially.

Reason:
- Easier debugging.
- Lower complexity.
- Better testability.
- No unnecessary orchestration dependency.

Reconsider agent frameworks only if needed.

## ADR-009: Document Processing

Decision: PyMuPDF for text-based PDFs.

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
- Supabase free tier
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
