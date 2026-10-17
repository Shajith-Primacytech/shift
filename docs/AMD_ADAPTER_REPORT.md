# SHIFT — Isolated AMD Inference Adapter

Completed October 16, 2026. Ready for review; no public inference endpoint or RAG
integration has been added. The frontend and Stage 2 business APIs are unchanged.

## Files

- `backend/app/config.py`: separate AMDSettings with explicit AMD_* aliases; SecretStr
  key excluded from repr and serialization; verified HTTPS endpoint validation.
  Existing SHIFT_* settings are unchanged. Configuration is loaded lazily.
- `backend/app/inference/contracts.py`: provider-independent validated messages,
  requests, results, token usage, protocol and fixed-message typed errors.
- `backend/app/inference/amd.py`: async httpx completion transport and configuration
  factory. No logging of prompts, headers, credentials or provider error bodies.
- `backend/app/inference/__init__.py`: isolated package boundary.
- `backend/tests/test_amd.py`: 53 mocked/configuration/regression cases.
- `backend/pyproject.toml`, `backend/uv.lock`: httpx promoted from dev to runtime,
  managed through uv lock and uv sync --locked. No new AI framework dependencies.
- `backend/.env.example`: timeout/retry settings. Local backend/.env was not changed.
- README, architecture and handoff notes: current integration status and boundaries.

## Configuration and behavior

Run from backend/ so the default .env resolves correctly. The factory reads:
AMD_API_KEY, AMD_BASE_URL, AMD_MODEL, AMD_CONNECT_TIMEOUT (5 seconds),
AMD_READ_TIMEOUT (20 seconds), AMD_OVERALL_TIMEOUT (25 seconds), and
AMD_MAX_RETRIES (1 additional attempt; permitted range 0–2).

The verified endpoint is https://developer.amd.com.cn/radeon/api/v1. Redirects and
implicit environment proxies are disabled. Credentials are sent only in the Bearer
header. Model selection remains configuration-based; no automatic model switch or
fallback occurs. The existing local DeepSeek configuration was preserved.

HTTPX has explicit connect/read/write/pool timeouts; asyncio.timeout supplies one
wall-clock deadline across all attempts and sleeps. Write/pool timeouts use the
configured connection timeout. Caller cancellation propagates normally.

Retry only connection-establishment errors/timeouts, pool timeouts (no request sent),
and explicit HTTP 429 rejection. Respect numeric and HTTP-date Retry-After values;
if the required delay exceeds the remaining budget, return a rate-limit error instead
of shortening it. Retry count is bounded. Never replay read/write timeouts, mid-flight
network/protocol errors, or 5xx completion responses automatically: their outcomes
can be ambiguous. Authentication/permission errors do not retry.

Successful text results include provider, configured and returned model IDs, total
elapsed latency including retry delays, attempts, finish reason and token usage when
available. Missing optional usage/model/finish metadata remains absent rather than
being invented. Reject malformed/non-JSON, blank, refused, tool-only or truncated
completions and invalid token counts. Raw reasoning is not returned.

Errors expose fixed descriptions, typed codes, HTTP status when available, attempts
and elapsed latency. They retain no response body, request object, provider message
or raw transport exception chain. Credential echoes in successful text/model results
are rejected, including escaped JSON text. No fabricated guidance is returned.

## Validation

- Full backend suite: **71 passed in 2.97 seconds** (53 adapter/configuration tests
  plus all 18 existing Stage 2 tests).
- Ruff selected correctness/import checks and formatting: passed.
- git diff --check: passed.
- A route-inventory regression verifies that the public API paths are unchanged.
- All HTTP tests use httpx.MockTransport; no live AMD requests or credits used.
- Credential protection tests use synthetic tokens and inspect error tracebacks,
  captured logs, settings repr/dumps and malicious response bodies.
- Local .env remains ignored, untracked and mode 600; its values were not printed.
- Frontend files were not changed; frontend build/browser tests were not rerun for
  this isolated backend addition.
- Existing non-failing Starlette/httpx TestClient deprecation warning remains.

The HTTPX phase timeout/exception classification follows:
https://www.python-httpx.org/advanced/timeouts/
https://www.python-httpx.org/exceptions/

## Remaining boundaries and blockers

The earlier minimal live probes confirmed both DeepSeek-V4-Flash and Gemma-4-31B-IT
can return text. Those probes predate this implementation; the new adapter itself
has only mocked validation. A live adapter smoke test requires a deliberate request.
Remaining quota, sustained availability, long-response quality and model-specific
structured output behavior have not been measured.

This is a text-only inference boundary, not a grounding or safety validator. It does
not retrieve documents, enforce evidence approval on arbitrary caller messages, or
validate citations. Future approved orchestration must select current approved
sources, skip inference on empty retrieval, validate references and recheck approval
before delivery. Never wire arbitrary technician prompts straight into this transport
and call the results grounded maintenance guidance.

LlamaIndex ingestion, embeddings, hybrid retrieval, Ragas and frontend AI behavior
remain deferred. Stop for review before any integration, commit, push or deployment.
