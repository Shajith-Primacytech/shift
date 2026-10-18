# SHIFT hackathon: model visibility and voice-to-knowledge

Implemented and verified 17 October 2026. Existing branding and earlier Gemma
integration remain in place. No deployment, push, credential edit, role change or
new database migration was performed in this phase.

## Audit before implementation

| Capability | Initial classification | Evidence / gap |
| --- | --- | --- |
| Microphone recording controls | Working and tested | Existing VoiceRecorder and browser recording test |
| Microphone permissions | Working and tested | Explicit interaction; denial tested; no-device message was generic |
| Recording start/stop | Working and tested | Real browser MediaRecorder exercised using a generated audio stream |
| Audio preview/playback | Partially implemented | Object URL and audio controls tested; human audible playback unverified |
| Upload and private storage | Working and tested | Existing attachments, authenticated downloads and ownership checks |
| Speech-to-text | Missing | Voice UI explicitly stated no transcription |
| Transcript editing | Missing | No transcript field |
| Knowledge capture integration | Partially implemented | Audio attachment worked; no transcript-to-text step |
| Voice-to-Gemma integration | Missing | Existing Gemma used written fields only |
| Supervisor transcript access | Missing | Audio download existed, but no transcript was produced |
| Automated voice tests | Partially implemented | Recording/preview/removal/permission denial existed; no transcription coverage |

The audit did not assume a microphone icon demonstrated physical microphone
capture. Existing and new automated browser recording tests do not establish the
quality of a real microphone in the presentation room.

## Part A: model visibility, implemented first

`AIModelIndicator` is reused for capture, saved execution receipts and troubleshooting.
Before execution, authenticated configuration metadata shows:

- Powered by Google Gemma
- Gemma-4-31B-IT
- Inference via AMD Token Factory
- Configured, not executed for this draft (or explicitly unavailable)

After a request, the indicator uses sanitized execution metadata. **AI Execution
Details** expands provider, requested model, actual returned model, success/failure,
UTC timestamp, latency, available token usage, upstream status and safe failure code.
Configured and returned model IDs are separate. Older receipts that did not store a
separate returned model show "not recorded" rather than inferring it.

Capture's verified model call, prompt, JSON schema, validation, model pin, token
limit and no-retry/no-fallback behavior were not changed. Its metadata adds the
explicit returned model field. No presentation/demo flag was necessary.

The actual troubleshooting adapter is AMD, with `AMD_MODEL=DeepSeek-V4-Flash` in the
backend configuration inspected for this task. This is **configured identity**, not
proof of a live DeepSeek response in this phase. The UI attributes an answer only
to the provider and returned model in that completion's metadata. If no model ID
was returned, it says so; it no longer substitutes the requested ID as an actual
returned model. Retrieval abstentions show no execution; model abstentions preserve
actual execution details without showing an unsupported answer. Failures with
available sanitized metadata display failure details.

RAG changes are metadata-only. Approved evidence selection, quote matching, citation
IDs, source ordering and approval rechecks remain intact. No answer text, citation
or retrieval eligibility logic was replaced.

Part A was validated before voice implementation: 104 focused backend tests,
frontend lint/typecheck/build, and all 18 then-existing browser tests passed.

## Part B: selected speech engine

A single authenticated AMD `GET /models` returned HTTP 200. No model advertised
audio input. The only speech candidate, `OmniVoice`, advertised text input and audio
output; it was not treated as a speech-to-text service. No audio was uploaded to an
AMD endpoint and no speculative speech requests were made.

Selected local engine:

- Recognition model: **Systran/faster-whisper-tiny.en** (OpenAI Whisper tiny.en,
  converted for CTranslate2).
- Pinned model revision: `0d3d19a32d3338f10357c0889762bd8d64bbdeba`.
- Engine: **faster-whisper 1.2.1**, local CPU int8, four CPU threads, English only.
- Decoder: **PyAV**, using its bundled audio codecs; no system FFmpeg install.
- Provider displayed: **Local CPU · faster-whisper**. This is not AMD transcription.
- Optional dependency group: `voice`; existing base dependencies were not upgraded.

The implementation follows the [faster-whisper project documentation](https://github.com/SYSTRAN/faster-whisper).
The optional package and pinned model were installed/prepared and actually tested
on this host. Public model weights are downloaded only by an explicit preparation
command. Transcription uses local files only, offline flags and no audio service.
Browser-native speech recognition was not used, avoiding its browser/service
variability and any implicit external speech transmission.

## Technician and supervisor workflow

The existing VoiceRecorder now offers:

1. Explicit microphone start; visible active status; stop or automatic two-minute stop.
2. Existing audio preview and removal.
3. **Transcribe recording**, with progress and fixed error states.
4. Original automatic transcript, editable **Reviewed voice transcript**, and an
   explicit **Use Transcript** action.
5. Use Transcript fills an empty written observation or appends a clearly labeled
   reviewed transcript to existing text. It never silently replaces existing text.
   An over-limit append is refused and the original stays intact. Repeated use is
   disabled until the transcript is edited.
6. The unchanged **Structure with AI** step then sends only the current reviewed
   written fields to Gemma. Applying a transcript after an earlier AI proposal
   makes that proposal stale through the existing source-consistency check.
7. Technician review/confirmation and normal submission produce **Pending** knowledge.
8. A different supervisor sees the reviewed text as the original written observation,
   the reviewed AI categories, execution details and the protected audio attachment.
   Only normal approval makes that latest version RAG-eligible.

Title, symptom and machine still require technician input. Audio is not inferred
into equipment identifiers or machine states, and no missing maintenance fact is
filled automatically. Nothing transcribes, sends to Gemma or submits automatically.

## Reliability, privacy and boundaries

- Permission denial, missing microphone, unsupported recording APIs, empty clips,
  interruptions, local service errors, unavailable model and network failures are
  explicit; ordinary written capture remains available.
- Recording stops on leaving the Voice tab, hiding the page, unmounting, errors or
  the duration limit. Pending permission requests are discarded if the page becomes
  hidden or the user leaves Voice before permission is granted.
- Microphone tracks stop; preview object URLs are revoked using the existing
  AudioPreview lifecycle. No browser speech-recognition service is invoked.
- Transcription requires the existing authenticated session and CSRF/origin controls.
  Sessions are checked again after processing before returning the transcript.
- Uploads are nonempty audio, at most 10 MiB. Decoder output is bounded to 120 seconds
  at 16 kHz; silence/too-short clips are rejected. One in-flight local job is allowed
  per application process. The isolated worker has a 60-second deadline and no
  automatic retries.
- Worker audio/result files are in a private temporary directory removed after
  processing, failure or timeout. Audio/transcripts are not printed or logged;
  worker diagnostics are suppressed and failures use fixed messages.
- The worker does not receive AMD credentials or Hugging Face tokens and is launched
  with local-only/offline settings. Preparation downloads weights, not audio.
- Audio is retained only when the user explicitly submits it as an existing
  authenticated source attachment, under the application's existing retention and
  access behavior. No extra public audio URLs or STT storage tables were created.
- Audio attachments themselves are not indexed by RAG. Only approved written
  content, including the reviewed transcript and reviewed categories, is indexed.

## Validation and evidence

Final regression results:

- **144 backend tests passed**, including new model identity, speech service,
  privacy/cleanup, real bounded-decoder, session, transcript and approval/RAG tests.
- **29 browser tests passed**, including all existing functionality and eleven new
  voice/model-state scenarios. The tests exercised real browser MediaRecorder in
  the pre-existing recording test; edge cases use recording doubles. Speech/Gemma
  responses in routine browser tests are explicitly mocked through the isolated
  test backend, never production code.
- Frontend lint, TypeScript validation and production build passed.
- Ruff checks passed for the new AI/speech API, speech service and speech tests.
- Axe accessibility checks passed with voice transcript and AI proposal controls
  visible. Overflow checks passed at 390px, 768px and 1440px. The expanded voice
  screenshot was actually inspected (`frontend/test-results/voice-transcript-review.png`,
  an ignored local test artifact with synthetic/mocked content).
- Tests verify configured vs returned IDs, success and unavailable/failed states,
  sanitization, unchanged original text, explicit transcript use, editing, no
  double application, reviewed-text-only Gemma input, supervisor-only approval,
  Pending exclusion, approved retrieval and exclusion of raw audio bytes.
- Browser tests ran with a production frontend and temporary synthetic backend/DB
  on 3001/8001 because the user's normal ports were occupied. Existing servers and
  development data were not stopped or changed. Temporary config/suite copies were
  removed and the production build restored to its normal API configuration.
- Existing non-failing Starlette/httpx deprecation warning remains in backend tests.

Real local ASR checks used synthetic English speech, not mocked transcripts:

| Check | Result |
| --- | --- |
| Direct local ASR, first test | 7.68 s audio, 9,673.2 ms processing |
| Authenticated transcription endpoint with WAV | HTTP 200, 797.2 ms processing |
| Local WebM/Opus decoder + ASR | 801.1 ms processing |
| Key content | Vibration/tool change and negative root-cause/inspection statements retained |
| Normal voice-text/audio submission | HTTP 201, Pending, original reviewed text retained, approved library exclusion |

These measurements are sample results, not guaranteed latency or maintenance
accuracy. Sanitized evidence, without full transcript/audio, is stored in
`docs/VOICE_LOCAL_SMOKE.json`. Temporary smoke databases/audio were removed.

No new live AMD completion was needed in this phase. The previously verified live
Gemma integration and `docs/GEMMA_CAPTURE_LIVE.json` remain available as historical
execution evidence; that earlier result is not presented as a new voice/Gemma run.
No live troubleshooting/DeepSeek execution is claimed here. Routine integration
and model-indicator tests used mocked AMD responses and real application gates.

## Current limitations / remaining rehearsal

- English only. Tamil and other languages are neither offered nor claimed tested.
- Chromium and local CPU execution were tested on this host. Safari/mobile device
  permissions/codecs and other operating systems are unverified.
- Physical microphone acoustics, audible playback and room noise have not been
  verified by a human. Rehearse with the actual presentation browser/microphone.
- ASR can mishear equipment identifiers, codes and negations. Tiny.en is chosen for
  local speed, not a safety guarantee. Technician edits and independent review are
  mandatory before trusted retrieval.
- The original automatic transcript is available in the current capture session;
  the reviewed written text and submitted audio persist via the existing model.
  Draft transcript recovery after refresh is not implemented.
- Uploaded documents/audio in Documents retain their existing attachment behavior;
  the new Transcribe action targets the microphone recording. Document extraction
  is unchanged and remains deferred.
- The local worker is bounded and intentionally simple; a production job queue or
  multi-instance speech scheduling is outside this hackathon phase.
- Missing optional dependencies/model show an unavailable state. They do not break
  recording attachments, manual capture, Gemma or troubleshooting.

No software blocker was observed on this prepared host. Hardware/browser rehearsal
is the remaining demo validation, not an asserted completed test.

## Files added in this phase

- `backend/app/api/ai.py`
- `backend/app/api/speech.py`
- `backend/app/speech/__init__.py`
- `backend/app/speech/constants.py`
- `backend/app/speech/prepare.py`
- `backend/app/speech/worker.py`
- `backend/app/speech/service.py`
- `backend/tests/speech_fakes.py`
- `backend/tests/test_speech.py`
- `frontend/src/lib/ai-models.ts`
- `frontend/src/components/ai-model-indicator.tsx`
- `frontend/src/components/use-ai-configuration.ts`
- `frontend/tests/voice.spec.ts`
- `docs/VOICE_LOCAL_SMOKE.json`
- `docs/VOICE_DEMO_REPORT.md`

## Existing files modified in this phase

- `backend/app/main.py`: register authenticated presentation and speech routes.
- `backend/app/config.py`, `backend/.env.example`: optional speech model location.
- `backend/app/capture/service.py`: explicit returned-model metadata only.
- `backend/app/rag/service.py`: sanitized execution metadata and truthful model attribution.
- `backend/app/api/troubleshooting.py`: propagate sanitized failure metadata.
- `backend/pyproject.toml`, `backend/uv.lock`: optional locked local speech dependencies.
- `backend/tests/e2e_server.py`: isolated speech double and test-only voice technician.
- `backend/tests/test_capture.py`, `backend/tests/test_rag.py`,
  `backend/tests/test_amd.py`: model metadata and exact API route regression coverage.
- `frontend/src/components/capture-ai.tsx`, `capture-execution.tsx`: reuse model indicator.
- `frontend/src/components/grounded-answer.tsx`, `troubleshooting.tsx`: response model evidence.
- `frontend/src/components/voice-recorder.tsx`: extend existing recording controls.
- `frontend/src/components/knowledge-capture.tsx`: explicit reviewed transcript append.
- `frontend/src/lib/api.ts`, `capture-structure.ts`: typed execution and speech contracts.
- `frontend/tests/capture-ai.spec.ts`, `workflows.spec.ts`: metadata/progress assertions.
- `README.md`: voice launch instructions and current capability description.

Earlier uncommitted branding/Gemma files remain separate prior work. This phase
made no logo, palette, global layout CSS, knowledge schema, permission, citation,
credential or demo-data changes.

## Exact launch steps

Restart the existing backend with the optional voice extra (do not run a duplicate
server on an occupied port):

```sh
cd /Users/mohamedshajith/Projects/shift/backend
uv sync --locked --extra voice
uv run --locked --extra voice python -m app.speech.prepare
uv run --locked --extra voice uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The model is already prepared on this host; the preparation command is repeatable.
Keep `--extra voice` on uv launch so optional dependencies stay installed. The
existing backend-only AMD key in ignored `.env` is reused without edits. Do not
place secrets in frontend variables. No demo environment flag is required.

In another terminal, restart the frontend with its ordinary build/start commands:

```sh
cd /Users/mohamedshajith/Projects/shift/frontend
npm run build
npm run start
```

Open `http://127.0.0.1:3000`. Use the same hostname for the backend/frontend.
For ordinary troubleshooting, keep the existing prepared RAG model/index setup
from the repository's demo guide; no RAG preparation behavior was changed here.

Reproduce regression checks with:

```sh
cd /Users/mohamedshajith/Projects/shift/backend
uv run --locked --extra voice pytest -q
cd /Users/mohamedshajith/Projects/shift/frontend
npm run lint
npm run typecheck
npm run build
npm run test:e2e
```

The default Playwright command requires free 3000/8000 ports as documented in the
repository. Its AMD/STT doubles are test-only and must not be shown as real inference.

## Five-minute demonstration

1. **0:00–0:40:** Sign in as an existing technician and open Knowledge capture.
   Show the Google Gemma model name, AMD provider and configured/not-executed status.
   Select a machine, enter a short title and symptom, and open Voice.
2. **0:40–1:20:** Record 10–15 seconds of synthetic English maintenance observations.
   Explicitly state what is unknown, e.g. cause not confirmed and inspection not yet
   performed. Stop and show preview controls. Select **Transcribe recording** once.
3. **1:20–2:00:** Review/edit the transcript, especially identifiers and negations.
   Select **Use Transcript**. Show preserved pre-existing text and the reviewed text
   in Written observation. No automatic submission or AMD audio upload occurs.
4. **2:00–3:00:** Select **Structure with AI** once. Show actual returned model and
   **AI Execution Details** from this real request, not a prior screenshot. Review
   the proposed categories, keep unknowns blank, correct errors and confirm review.
5. **3:00–3:40:** Submit. Show Pending status. Open the technician queue and compare
   original reviewed text, structured fields and protected audio. The technician
   cannot approve; the record is absent from the approved library/RAG.
6. **3:40–4:30:** Sign out and use a different supervisor account. Review the transcript
   and proposal, then approve using the existing action. Show the approved library
   entry and note that this latest approved version is now eligible for retrieval.
7. **4:30–5:00:** Open a prepared troubleshooting question. Show citations and the
   actual provider/returned model beside the answer. If retrieval abstains or the
   provider is unavailable, show that state honestly; do not claim an unexecuted
   model or replace it with mocked results.

If the room microphone or local transcription fails, preserve the recording,
continue with written observations and demonstrate the already-working Gemma step.
