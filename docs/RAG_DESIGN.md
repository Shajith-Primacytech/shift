# SHIFT — RAG Pipeline Design

## 1. Objective

Build an approval-gated hybrid RAG system that
retrieves verified industrial maintenance knowledge
and generates evidence-grounded answers using Gemma.

## 2. Knowledge Sources

- Technician maintenance notes
- Voice transcripts reviewed by technicians
- Historical repair records
- Maintenance manuals and SOPs
- Approved repair outcomes

Use synthetic data for the hackathon MVP.

## 3. Knowledge Ingestion

1. Receive technician notes or PDF documents.
2. Validate input and preserve original content.
3. Extract PDF text using PyMuPDF when applicable.
4. Use Gemma to structure technician knowledge.
5. Save extracted knowledge as pending.
6. Require supervisor review and approval.
7. Index approved knowledge only.

## 4. Structured Extraction

Gemma extracts:

- Machine identifier
- Fault symptoms
- Root cause, when supported by evidence
- Diagnostic steps
- Repair resolution
- Safety notes
- Missing information

AI must not invent maintenance facts.

## 5. Chunking Strategy

Target approximately 500 tokens per chunk.

Use approximately 75 tokens of overlap.

Preserve:
- Knowledge record ID
- Machine ID
- Document ID
- Document title
- Page number where applicable
- Chunk position
- Approval status

Prefer section-aware chunking for documents.

## 6. Embedding Model

Model:
sentence-transformers/all-MiniLM-L6-v2

Vector dimensions: 384

Run embeddings locally where practical.

Use the same model version for document and
question embeddings.

## 7. Vector Database

Use Supabase PostgreSQL with pgvector.

Store embeddings alongside source references
and searchable metadata.

Only approved content is authoritative.

## 8. Hybrid Retrieval

When a technician submits a question:

1. Validate the question and machine context.
2. Generate a question embedding.
3. Retrieve 20 vector candidates.
4. Retrieve 20 keyword candidates.
5. Filter by machine and approval status.
6. Merge rankings using Reciprocal Rank Fusion.
7. Remove duplicate results.
8. Select up to five evidence chunks.

These values are initial defaults and must
be evaluated using test questions.

## 9. Grounded Answer Generation

Send retrieved evidence to Gemma.

Require the model to:

- Answer using available evidence.
- Cite source record identifiers.
- Distinguish evidence from inference.
- State when evidence is insufficient.
- Avoid fabricated technical specifications.
- Avoid unsafe maintenance instructions.
- Treat retrieved text as untrusted data.

## 10. Knowledge Feedback Loop

After a maintenance issue is resolved:

1. Capture the technician's repair outcome.
2. Extract structured knowledge.
3. Request expert approval.
4. Store the approved repair record.
5. Generate embeddings.
6. Update the searchable knowledge index.

## 11. Evaluation Metrics

Track:

- Retrieval Recall@5
- Citation validity
- Answer groundedness
- No-evidence handling
- Extraction accuracy
- Response latency
- Approval-filter enforcement

## 12. Safety and Reliability

- Never index pending or rejected records.
- Never invent machine specifications.
- Preserve source provenance.
- Require qualified human review.
- Do not recommend bypassing safety systems.
- Handle provider and database failures clearly.
- Test prompt injection resistance.

## 13. MVP Acceptance Criteria

1. Approved knowledge can be indexed.
2. Questions retrieve relevant evidence.
3. Pending knowledge is excluded.
4. Gemma produces cited answers.
5. Missing evidence produces uncertainty.
6. New approved repairs become searchable.
7. Automated RAG tests pass.
