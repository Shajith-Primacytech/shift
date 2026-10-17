# SHIFT — Final preparation and private GitHub readiness

Date: October 17, 2026. Submission deadline supplied by the team: October 18, 2026.
Scope: fix reproducible demo issues, validate the existing MVP, finalize documents,
and make the two owner-authorized commits to the existing private repository.
No deployment, visibility change, new phase or unrelated feature is authorized.

**AMD credential rotation: PENDING.** Intentionally deferred by the owner. This
remains an unresolved security requirement; the exposed credential is not claimed
safe. It does not block the explicitly authorized private repository preparation.

## Results

| Check | Result | Evidence |
| --- | --- | --- |
| Backend | PASS | 95 tests, 4.78s |
| Browser | PASS | 15 tests, 16.8s, including the new form-limit regression |
| Lint / typecheck / production build | PASS | All seven application routes |
| Real local embedding retrieval | PASS | 6/6 fixture source-set checks |
| Approval and machine restrictions | PASS | Existing tests cover pending/rejected/revoked/superseded exclusion, cached-source invalidation, scoped retrieval and outbound prompts |
| Citation validation | PASS | Exact passage IDs/text, live source-card display, invalid IDs rejected and changed approval withheld |
| CNC-01 live browser rehearsal | PASS | HTTP 200; DeepSeek; two real approved source citations |
| CNC-02 live browser abstention | PASS | HTTP 200; insufficient evidence; no citations/model/usage |
| Remote / branch | PASS | origin = https://github.com/Shajith-Primacytech/shift.git; GitHub reports PRIVATE; branch main |
| Index credential/artifact checks | PASS | Scanned exact staged contents; no credential matches, sensitive paths, unexpected binaries or files over 1MiB |
| Credential rotation | PENDING | Deferred; not established by local checks or successful API access |
| Deployment / public visibility | NOT PERFORMED | Outside authorized scope |

Backend tests have one non-fatal Starlette TestClient deprecation warning. Browser
runs have non-fatal Node color-variable warnings. No dependency migration was made.

## Issues found and fixed

1. Moderate demo usability issue: context accepted 3000 characters while backend
   questions are limited to 1500. Reduced context to 1400, leaving room for the
   selected symptom. The existing 240 embedding-token limit remains enforced by
   the backend with an explicit shorten-question response.
2. Empty “Something else” requests reached backend validation. The form now labels
   context as required and disables submission until at least five trimmed
   characters are present. A browser regression first failed on the old 3000 limit,
   then passed with the correction. Existing design and API contracts are unchanged.
3. Repository hygiene: explicitly ignore generated next-env.d.ts, Ruff cache and
   local logs. Real environment files/backups, SQLite data, dependencies, build and
   test outputs remain excluded. Redacted .env.example files are included.
4. Documentation now reflects the authorized private commit/push and explicitly
   deferred rotation. Screenshot/recording guidance distinguishes live, recorded and
   mocked responses from synthetic source data.

No new critical software/security issue was found. The known credential exposure
remains unresolved; a successful inference call does not establish token safety.

## Live demonstration measurements

One final authenticated browser rehearsal used real local embeddings, an isolated
temporary synthetic database and the existing AMD adapter:
- CNC-01 default spindle-vibration question: HTTP 200, `answered`, model
  `self-dploy/DeepSeek-V4-Flash`, 12659ms provider latency, 574 input + 128 output =
  702 total tokens, zero reasoning tokens. UI displayed SOP-001-v1 and NOTE-002-v1
  citations and an inspectable source excerpt. Quotations remained source text.
- CNC-02: HTTP 200, `insufficient_evidence`, zero citations, model/usage/latency null.
  The approved scope is empty and the service abstains before inference.

These are single observations, not SLAs or quality benchmarks. Tests use mocked
AMD separately. Credential rotation remains PENDING despite live success.
Real embedding evaluation durations: 6496.7ms cold, then 26.1, 26.0, 13.0, 0.9 and
12.1ms. Six synthetic fixtures are not an industrial accuracy evaluation.

## Security and repository review

GitHub CLI confirmed the existing repository is PRIVATE. Local main and origin/main
matched at the initial commit before changes; fetch showed no divergence. No remote
URL, repository visibility or branch protection was changed. Push must be normal
fast-forward only. Repository state and push outcome are also reported in chat.

Pre-staging scan: 86 tracked/unignored candidate files, no issues. Application index
scan: 79 total index files, no issues. Audit checks compared staged bytes against
configured local AMD credentials without printing values, plus selected secret
patterns and sensitive/generated paths. Both .env and .env.save are excluded.
Earlier acceptance also scanned 88 reachable historical blobs with no matches for
the then-current key or selected patterns. Scans do not prove absence of every
possible secret format or exposure outside Git.

The complete application candidate list and tracked documentation changes were
reviewed. Largest files are normal dependency lockfiles (about 240KB and 206KB),
not model weights or media. Synthetic test credentials belong only to an isolated
test server and are not development-account defaults. No original factory data,
private recordings, environment files, database sessions or uploads are committed.

Authorized commit structure:
1. `feat: implement SHIFT approval-gated RAG MVP` — application, tests, migrations,
   synthetic fixtures, lockfiles, ignore rules and redacted environment examples.
   Commit: `3d8ce0a69c6e6393074c3ea833404f4096959dc9`.
2. `docs: prepare SHIFT hackathon submission` — README and reviewed documentation.
   Its hash is available from Git history; it cannot be embedded in its own contents.

Each index must pass a credential/path audit and `git diff --cached --check` before
commit. Reconfirm PRIVATE visibility before pushing both commits to origin/main.
No force push, repository creation, visibility change or deployment is authorized.

## Remaining limitations and actions

- **PENDING security:** revoke the exposed AMD token and configure a replacement.
  Keep values out of chat/logs/Git. Private-repository status does not make it safe.
- Provider availability, quota and latency can disrupt a recording; no fabricated
  answer or automatic model fallback exists. Record and label actual behavior.
- Attachments/audio persist but are not parsed/transcribed. Ragas, broader retrieval
  metrics, durable jobs, conversation history and free-form synthesis are deferred.
- Exact quotations validate provenance, not semantic completeness or safe diagnosis.
  Approval checks occur before inference and delivery; later revocation cannot erase
  text already displayed. Single-workspace/machine scope is not tenant isolation.
- Relevance gating may abstain on paraphrases; long passages may be excluded. One
  process/worker and a small synthetic corpus are the intended deployment shape.
- Application license has not been selected. Do not describe SHIFT itself as licensed
  open source merely because its dependencies are open source.
- Finish the recording and hackathon submission form. Organizer requirements and
  any judge access to the private repository must be checked by the presenter.
  Do not promise a deployed public URL; no hosting was performed.

See DEMO_GUIDE.md for exact startup, isolated presenter database, 90-second script,
screenshot recommendations and recording instructions. SUBMISSION.md contains the
technically accurate overview, stack, AMD/LlamaIndex explanation and submission copy.
