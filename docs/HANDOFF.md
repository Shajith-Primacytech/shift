# SHIFT — Final preparation handoff

October 17, 2026. Deadline October 18, 2026. No new development phase.

Read FINAL_ACCEPTANCE.md for latest results and repository preparation;
DEMO_GUIDE.md for exact startup, 90-second script, screenshots and recording;
SUBMISSION.md for accurate project and submission copy. Stage reports are historical.

95 backend tests, 15 browser tests, lint/typecheck/build and 6/6 real embedding
checks pass. Fixed question length/empty custom-question validation without changing
backend contracts. Live browser: DeepSeek HTTP 200, 12659ms, 702 tokens, SOP-001 and
NOTE-002 citations. CNC-02 abstains with no citations/model usage.

AMD credential rotation is PENDING, intentionally deferred. Do not claim the exposed
credential is safe. Do not print/read out/copy secrets. The owner authorized private
repository commits and push despite this known unresolved requirement. Any newly
found critical security/repository issue must stop push. No deployment or visibility
change authorized.

Existing remote is private Shajith-Primacytech/shift; branch main. Application commit
3d8ce0a69c6e6393074c3ea833404f4096959dc9, followed by the documentation commit. Use Git
history and origin/main to confirm push state; do not infer it from this note.

Preserve local backend/data, .env and .env.save; all remain ignored. Browser tests
used temporary data and stopped their servers. Start the intended database using
DEMO_GUIDE.md; do not use test-server credentials as normal application accounts.
Remaining: credential rotation, presenter recording, submission form and judge access
to private source. Stop after the authorized push for review; no further features.
