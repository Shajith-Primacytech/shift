# SHIFT — RAG Design

## Implemented MVP boundary — October 17, 2026

LlamaIndex Documents, SentenceSplitter and BaseRetriever are operational. Approved
written fields are split at 180 embedding tokens with 25 overlap. MiniLM is pinned
to revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, CPU, normalized 384 dimensions.
Queries over 240 embedding tokens are rejected. Chunks retain record/version/chunk
IDs, position, text hash and source fingerprint; no PDF page provenance is claimed.

SQLite migration 002 adds vectors, FTS5 and index-generation fingerprints. Lazy
indexing atomically publishes each approved version; each search joins current
latest approved versions and the selected machine. Both vector cosine and FTS5
BM25 operate, combined by reciprocal-rank fusion. Candidates need cosine >=0.35
and meaningful lexical overlap; this conservative gate is not calibrated confidence.
Revoked/superseded cached rows cannot pass the current eligibility join. Evidence
is checked again before inference and immediately before response delivery.

AMD selects supplied passage IDs; the server returns exact source text only.
This deliberately replaces free-form synthesis for the deadline. Missing evidence,
invalid citations, changed approvals and failed inference produce no answer.
The endpoint accepts no caller-supplied evidence. Source access is the existing
single-workspace authenticated, approved-only policy plus strict machine scope.
There is no new tenant or plant ACL model.

Six real-embedding fixture checks passed; deterministic authorization/citation
and browser tests are documented in STAGE_3_REPORT.md. Ragas, extraction, background
jobs, general cross-machine SOPs, branch comparison, recall/MRR and resource
benchmarks below remain future work, not completed claims.

## Longer-term design (beyond the implemented slice)

## Framework and storage

LlamaIndex is the primary RAG framework: Documents, nodes, ingestion transforms,
local embedding integration, custom retriever interfaces and response synthesis.
SQLite remains the source of truth for content versions, approval, chunks and
embeddings. Source text and evidence must remain inspectable independently of LLMs.

Runtime packages: llama-index-core, llama-index-embeddings-huggingface,
sentence-transformers, numpy, and the existing PDF extractor decision (PyMuPDF).
Use selective integrations rather than the umbrella llama-index installation.
No LlamaCloud, hosted parsing, hosted embeddings, or paid vector database.

## Ingestion

1. Validate and preserve written notes or PDF/TXT/Markdown source bytes.
2. Extract text with page/section provenance; scanned PDF OCR is deferred.
3. Human review approves an exact knowledge revision.
4. Enqueue durable, retryable ingestion keyed by version, content hash, chunking
   configuration and embedding model revision. Pending/rejected content is not indexed.
5. Use LlamaIndex section-aware, token-aware splitting with the embedding tokenizer.
6. Generate normalized local embeddings and persist vectors plus FTS5 entries.
7. Keep indexing status distinct from approval status. Publish a complete generation
   atomically; failed work must not expose partial or unauthorized content.

Model: sentence-transformers/all-MiniLM-L6-v2, 384 dimensions. Its default limit is
256 wordpieces. Start around 200–220 tokens with roughly 30-token overlap, reserving
space for metadata and special tokens. Validate actual complete model input lengths
against truncation. These are tuning defaults, not measured optima.

Each node preserves record ID, version ID, chunk ID, document ID, page/section,
position/offsets, original excerpt and content hash. Pin model/tokenizer revisions;
reindex after incompatible changes. Deduplicate within version without erasing source
lineage. Framework caches never override database approval.

## Retrieval

1. Authenticate and validate machine/query scope.
2. Resolve current eligible approved versions in SQLite.
3. Embed the question with the same pinned embedding model.
4. Retrieve up to 20 eligible vector candidates using exact NumPy cosine similarity.
5. Retrieve up to 20 eligible FTS5 keyword candidates.
6. Merge deterministic reciprocal ranks; deduplicate and select up to five chunks.
7. Recheck current approval and active version before generation and before delivery.

Implement SQLite adapters as LlamaIndex retrievers returning NodeWithScore objects.
Filter before each branch's top-k; a post-filter alone is insufficient. No LLM query
expansion initially. Machine-specific content and explicitly scoped general SOPs
must have deliberate eligibility rules. Revocation takes effect without waiting
for index cleanup. Existing source/history routes are not retrieval substitutes.

## Generation and citations

Use an explicitly configured provider only after AMD endpoint/model/quota verification.
Keep request limits, timeouts and retry behavior behind a modular inference adapter.
Use LlamaIndex synthesis with bounded context and provider calls. Treat source text
as untrusted evidence, never instructions. Do not fabricate procedures or specifications.

Validate citations against the selected, currently approved evidence. Preserve exact
source/version/chunk references and excerpts. Do not let automatic citation
re-chunking sever lineage. Missing evidence produces an explicit insufficient-evidence
result. Without inference, return source excerpts labeled retrieval-only.

Record pipeline timings, candidate IDs/ranks/scores, selected evidence, model revision,
prompt version and provider identity. Scores are not calibrated probabilities.
Avoid secrets or confidential content in logs. Use synthetic evaluation data.

## Evaluation

Required deterministic tests: Recall@5, MRR, citation validity, machine isolation,
pending/rejected/revoked exclusion, stale-index handling, reindexing and no-evidence
behavior. Compare keyword-only, vector-only and hybrid retrieval on a versioned set.

Ragas is an offline evaluation dependency in a separate environment. Its dependencies
include LangChain and datasets; they must not expand the production API runtime.
Start with ID-based context precision/recall. Add faithfulness and other judge-based
metrics only with an explicitly configured evaluator and verified free allowance.
No default OpenAI provider or automatic paid calls. Missing metrics are "not run".

Publish actual dataset size, scores, failed cases, package/model versions, judge
configuration, cold/warm latency, p50/p95 latency, peak RSS and run date. Human review
and deterministic authorization tests remain necessary alongside Ragas scores.

## Resource plan (estimates, not benchmarks)

384-dimensional float32 vectors require 1,536 bytes each: about 14.6 MiB for 10,000
chunks or 146.5 MiB for 100,000, excluding metadata and copies. Provision approximately
1–2 GiB for a single embedding process initially, then measure peak usage. Use one
model instance, bounded batches and indexing concurrency. Avoid duplicating models
across API workers. Exact search is intended for a small hackathon corpus.
