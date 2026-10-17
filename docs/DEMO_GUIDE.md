# SHIFT — Reproducible local demonstration

Use synthetic data only. Do not open `.env`, terminal environment output, credentials,
HTTP Authorization headers or session cookies while recording. AMD credential rotation
is PENDING and intentionally deferred by the owner. This is an unresolved security
requirement; it does not block the authorized private repository preparation. Do not
claim that the exposed credential is safe. Revoke and replace it as soon as possible.

## Launch sequence

Prerequisites: Node.js 24/npm, uv with Python 3.12, internet for initial dependencies
and model download, and configured free AMD hackathon access. Use one backend worker.
Commands below assume the repository is at `/Users/mohamedshajith/Projects/shift`;
substitute your checkout path on another computer.

Terminal 1, from the repository:

```sh
cd /Users/mohamedshajith/Projects/shift/backend
uv sync --locked
```

Keep the existing `backend/.env`. On a NEW checkout only, copy `.env.example` to
`.env`, set its permissions to 0600 and edit the three AMD variables in a local
editor. Never overwrite an existing configured file or put the token in a command.
Use AMD_BASE_URL=https://developer.amd.com.cn/radeon/api/v1 and
AMD_MODEL=DeepSeek-V4-Flash. Restart the backend after configuration changes.

For a reproducible, isolated presenter database, use a NEW filename below. If it
already exists, choose another filename instead of deleting existing data. Keep the
same exported path throughout preparation and server launch:

```sh
export SHIFT_DATABASE_PATH=data/submission-demo-01.sqlite3
uv run python -m app.manage init-db
uv run python -m app.manage create-user --username technician --name "Demo Technician" --role technician
uv run python -m app.manage create-user --username supervisor --name "Demo Supervisor" --role supervisor
uv run python -m app.rag.prepare
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Account commands prompt securely for passwords (12–256 characters). They are one-time
per fresh database; reuse existing accounts on subsequent starts. The preparation
command downloads the pinned embedding model if absent and indexes approved records;
it does not call AMD. The developer's normal database is preserved.

Terminal 2:

```sh
cd /Users/mohamedshajith/Projects/shift/frontend
npm ci
npm run build
npm run start
```

Frontend: http://localhost:3000
Backend docs: http://localhost:8000/docs
Health: http://localhost:8000/api/v1/health

Use matching hostnames. Health confirms process availability, not provider readiness.
Open a normal window as technician and a separate browser profile/private window as
supervisor. Regular tabs share cookies, so they are not separate login sessions.

## Happy path — recommended question

Machine: CNC-01. Symptom button: Unusual spindle vibration.
Additional context: `Vibration started after a tool change. What should I check?`

1. Sign in as technician; show dashboard synthetic telemetry.
2. Open `/troubleshoot`, choose CNC-01 and the symptom/context above.
3. Select Review evidence. Allow up to approximately a minute for provider inference,
   plus cold local model startup. Do not double-click or repeatedly retry.
4. Show AI-selected approved guidance and the uncertainty message. Expected retrieval
   includes SOP-001 and NOTE-002; the model may select one or both. Do not promise a
   fixed number of passages or identical selections on every request.
5. Expand Inspect retrieved passage and Open approved record. Show version/machine
   references. Explain that the text is quoted evidence, not a diagnosis.
6. Continue to checks, acknowledge the synthetic rehearsal, log a handover and submit.
   The result is Pending; it does not authorize machine operation.

## Insufficient evidence

Use CNC-03 on a fresh seeded database, choose Unusual spindle vibration and Review
evidence. It has no approved knowledge. Expect Insufficient approved evidence, no
source cards, and disabled continuation. Retrieval abstains before calling AMD.
A second option is CNC-01 → Something else → `What is the capital of France?`.

## Unapproved exclusion demonstration

1. In the supervisor profile, open `/approvals` and show pending SUB-005,
   “Intermittent vibration during finishing,” scoped to CNC-02. Leave it pending.
2. In the technician profile, open Knowledge and filter CNC-02: no approved record.
3. In Troubleshoot select CNC-02 / Unusual spindle vibration / Review evidence.
   Expect insufficient evidence even though a matching pending note exists.
4. Explain that the server finds no eligible source and makes no AMD call. The UI
   alone does not prove outbound exclusion; cite the automated transport checks.

Optional longer review-loop demonstration, AFTER recording the exclusion case:
Capture a new synthetic CNC-02 written note as technician, approve that exact entry
as the separate supervisor, refresh the technician library, and ask about its text.
A suitable note is: “Synthetic spindle vibration observation after a tool change.
Record the tool identifier and operating context. Refer the observation to the
maintenance supervisor. The cause is unconfirmed; no repair or operation is authorized.”
Show that it enters the library; a relevant model selection is possible but not
promised. Revoke that new record with a reason and requery to show its exclusion.
Do not approve SUB-005 if you intend to repeat the original pending-only scenario.

## Availability and fallback presentation

Only AMD selection requires live inference. Local capture, approval, library and
prepared embedding retrieval can be demonstrated without it. A timeout/provider
error displays no maintenance answer. Default deadlines: connect 5s, read 45s,
overall 55s; frontend request timeout 75s. No automatic replay after ambiguous read
or write timeouts and no automatic model fallback.

If AMD is unavailable, show the actual error, then demonstrate capture/review and
insufficient evidence. You may show a previously recorded successful live run only
if labeled as recorded. Do not present mocked test output as current live inference.
Before submission, rehearse once with the replacement credential and verify quota.

## 90-second script

Pre-open the supervisor pending record and technician troubleshooting tab. The
90-second target assumes a rehearsed warm request; live latency may extend it.

| Time | Screen/action | Narration |
| --- | --- | --- |
| 0–12s | Dashboard | “SHIFT preserves maintenance experience across shifts. Every machine and reading here is synthetic.” |
| 12–25s | Submit CNC-01 question | “A technician reports spindle vibration after a tool change. SHIFT searches approved knowledge for this specific machine.” |
| 25–40s | Loading / explain pipeline | “LlamaIndex combines local semantic retrieval with keyword search. AMD DeepSeek selects passages from that evidence.” |
| 40–57s | Answer and source card | “These are exact approved quotations. We verify source and version IDs, recheck approval, and show uncertainty. This is not a confirmed diagnosis.” |
| 57–70s | Supervisor pending SUB-005 | “Technician observations persist, but only a different supervisor can approve their contribution. This matching CNC-02 note is still pending.” |
| 70–82s | CNC-02 question → insufficient evidence | “SHIFT refuses an answer here: unapproved knowledge is excluded before inference.” |
| 82–90s | Library / closing | “The result is an inspectable human review loop, validated with backend, browser and retrieval tests—built around local storage and AMD hackathon inference.” |

## Re-run acceptance checks

Stop local servers on 3000/8000 before browser tests; they start isolated test servers.

```sh
cd /Users/mohamedshajith/Projects/shift/backend
uv run pytest -q
uv run python -m app.rag.evaluate
cd ../frontend
npm run lint
npm run build
npm run typecheck
npx playwright install chromium
npm run test:e2e
```

Playwright's Chromium install is needed once on a new machine. Browser tests use
synthetic test accounts and a mocked AMD transport, never the presenter database.
The separate real-embedding evaluation uses a temporary database and no AMD calls.


## Screenshot and recording plan

Use a dedicated browser window at 1440×900 (or 1920×1080), normal zoom, and hide
personal bookmarks, notifications and unrelated tabs. Do not record login passwords,
terminal configuration, network request headers or local environment files.

Recommended frames:
1. Dashboard with SHIFT branding and the synthetic-data notice visible.
2. CNC-01 answer with “AI-selected approved guidance,” uncertainty and an expanded
   source passage showing record/version/machine references.
3. Supervisor queue showing pending CNC-02 SUB-005 (synthetic content only).
4. CNC-02 insufficient-evidence result with no source cards.
5. Optional mobile-width view demonstrating responsive source citations.

Record the actual UI. Identify all telemetry and records as synthetic. Label any
historical clip “Previously recorded live AMD inference”; label test-server output
“Mocked integration test.” A real live AMD result still uses synthetic evidence.
Do not hide errors or splice a mocked answer into a live request. If editing out
waiting time, label the cut rather than implying the shortened duration is latency.

Rehearse the 90-second script above, then capture one take. Allow a longer take when
provider latency exceeds the schedule; correctness takes priority over timing. Save
recordings outside the repository, review every frame for personal/credential data,
and share only deliberately selected media. No recording/upload is automated here.
