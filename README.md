# SHIFT — Industrial Knowledge Intelligence

SHIFT is an AI-powered industrial knowledge-retention
and maintenance-assistance platform.

Built for the AMD Developer Hackathon: ACT III.

## The Problem

Factories lose valuable operational knowledge when
experienced technicians retire or leave.

Critical troubleshooting experience often exists
only in technicians' memories rather than in
searchable maintenance documentation.

## Our Solution

SHIFT captures technician expertise, converts it
into structured maintenance knowledge using Gemma,
and makes approved knowledge searchable through
Retrieval-Augmented Generation (RAG).

## Core Workflow

1. Capture technician knowledge through text or voice.
2. Extract structured information using Gemma.
3. Review and approve knowledge.
4. Store approved knowledge in PostgreSQL.
5. Index knowledge using vector embeddings.
6. Retrieve relevant evidence using hybrid RAG.
7. Generate answers with source citations.
8. Preserve approved repair outcomes for future use.

## Technology Stack

Frontend:
- Next.js
- TypeScript
- Tailwind CSS

Backend:
- Python
- FastAPI

AI:
- Gemma via AMD Token Factory
- Sentence Transformers

Database:
- Supabase PostgreSQL
- pgvector

Development:
- GitHub
- OpenAI Codex

## Project Structure

frontend/ - Next.js application (to be created)
backend/  - FastAPI and AI services
docs/     - Architecture and engineering documents
scripts/  - Development utilities
data/     - Synthetic demonstration data

## Current Status

Project initialization in progress.

## Security

Never commit API keys, passwords, or confidential
factory information.

Use synthetic data for the hackathon demonstration.
