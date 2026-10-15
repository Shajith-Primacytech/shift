# SHIFT — System Architecture

## 1. Product Overview

SHIFT is an AI-powered industrial knowledge
retention and maintenance assistance platform.

It captures technician expertise, structures it
using Gemma, and makes approved knowledge
searchable through Retrieval-Augmented Generation.

## 2. Technology Stack

Frontend:
- Next.js
- TypeScript
- Tailwind CSS

Backend:
- Python
- FastAPI
- Pydantic

AI:
- Gemma via AMD Token Factory
- Sentence Transformers for local embeddings

Database:
- Supabase PostgreSQL
- pgvector for semantic search
- PostgreSQL full-text search

Document Processing:
- PyMuPDF for PDF text extraction

Development:
- Git
- GitHub
- OpenAI Codex

## 3. High-Level Architecture

Technician
    |
    v
Next.js Frontend
    |
    v
FastAPI Backend
    |
    +--> Gemma AI Extraction
    |
    +--> Expert Approval Workflow
    |
    +--> Supabase PostgreSQL
    |
    +--> Embedding Service
    |
    +--> Hybrid RAG Retrieval
    |
    +--> Gemma Answer Generation
    |
    v
Grounded Answer with Source Citations

## 4. Core Services

### Knowledge Capture Service

Accepts technician notes and voice transcripts.

Preserves the original input and machine context.

### AI Extraction Service

Uses Gemma to extract:
- Symptoms
- Root cause
- Diagnostic steps
- Resolution
- Safety notes
- Missing information

All extracted data requires human review.

### Approval Service

Allows authorized supervisors to approve,
edit, or reject knowledge records.

Only approved records become authoritative.

### Document Ingestion Service

Extracts text from maintenance PDFs.

Preserves document and page references.

### Embedding Service

Uses sentence-transformers/all-MiniLM-L6-v2.

Embedding dimensions: 384.

### Retrieval Service

Combines:
- Vector similarity search
- Keyword search
- Machine filtering
- Approval filtering
- Reciprocal Rank Fusion

### Answer Generation Service

Uses retrieved evidence and Gemma to
produce answers with source citations.

Must clearly state when evidence is insufficient.

## 5. Database Entities

- machines
- knowledge_records
- documents
- knowledge_chunks
- question_logs

## 6. Security Principles

- Never expose API keys to the frontend.
- Store secrets in environment variables.
- Enforce backend authorization.
- Only approved knowledge enters RAG.
- Preserve source provenance.
- Validate all inputs.
- Use synthetic hackathon data.

## 7. Engineering Principles

- Modular code architecture
- Typed API contracts
- Testable Python services
- Explicit error handling
- Versioned database migrations
- No unnecessary agent frameworks
- No paid infrastructure dependencies

## 8. MVP Success Criteria

1. Technician submits maintenance knowledge.
2. Gemma extracts structured information.
3. Supervisor reviews and approves it.
4. Approved knowledge is indexed.
5. Technician asks a maintenance question.
6. Hybrid RAG retrieves relevant evidence.
7. Gemma generates a grounded answer.
8. SHIFT displays valid source citations.
9. Unapproved knowledge remains excluded.
10. The complete workflow passes tests.
