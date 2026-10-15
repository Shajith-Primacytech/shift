# SHIFT — Development Roadmap

## Project

SHIFT — Industrial Knowledge Intelligence

Hackathon: AMD Developer Hackathon ACT III

Budget: Zero out-of-pocket cost.

## Development Rules

- Build one milestone at a time.
- Validate each milestone before continuing.
- Use GitHub for version control.
- Use Codex for implementation assistance.
- Never commit API keys.
- Use synthetic factory data.
- Avoid unnecessary complexity.

## Phase 1 — Environment and Repository

Tasks:
1. Configure Git identity.
2. Create local project structure.
3. Write architecture documentation.
4. Create GitHub repository.
5. Connect local repository to GitHub.
6. Install and configure Codex.

Validation:
- Git configuration is correct.
- Project files exist.
- GitHub remote is connected.
- Initial commit is pushed.

## Phase 2 — Application Foundation

Tasks:
1. Initialize Next.js frontend.
2. Initialize FastAPI backend.
3. Implement backend health endpoint.
4. Connect frontend to backend.
5. Create application navigation.
6. Build initial dashboard.

Validation:
- Frontend runs on localhost:3000.
- Backend runs on localhost:8000.
- Frontend successfully calls backend.

## Phase 3 — Database

Tasks:
1. Create Supabase project.
2. Enable pgvector.
3. Create database tables.
4. Configure backend database connection.
5. Implement machine and knowledge APIs.
6. Add backend tests.

Validation:
- Database connection succeeds.
- CRUD operations work.
- Tests pass.

## Phase 4 — AMD Gemma Integration

Tasks:
1. Verify AMD Token Factory access.
2. Confirm model ID and API endpoint.
3. Configure backend environment variables.
4. Test real Gemma inference.
5. Implement structured extraction.
6. Validate AI output using Pydantic.

Validation:
- Gemma API responds.
- Extraction returns valid structured data.
- AI records remain pending approval.

## Phase 5 — Hybrid RAG

Tasks:
1. Install Sentence Transformers.
2. Generate 384-dimensional embeddings.
3. Implement document chunking.
4. Store embeddings in pgvector.
5. Implement keyword search.
6. Implement vector similarity search.
7. Merge results using RRF.
8. Generate cited answers with Gemma.

Validation:
- Approved records are searchable.
- Pending records are excluded.
- Relevant evidence is retrieved.
- Answers contain valid citations.

## Phase 6 — Technician Workflow

Tasks:
1. Build knowledge capture screen.
2. Implement expert approval interface.
3. Implement PDF text ingestion.
4. Add browser voice capture.
5. Connect AI assistant to RAG.
6. Implement repair outcome capture.

Validation:
- Complete capture-to-answer workflow works.
- Approval rules are enforced.
- Errors are handled correctly.

## Phase 7 — Evaluation and Demo

Tasks:
1. Create synthetic machine scenarios.
2. Seed demonstration knowledge.
3. Create evaluation questions.
4. Measure retrieval and answer quality.
5. Test failure scenarios.
6. Record product demonstration.

Validation:
- End-to-end tests pass.
- Evaluation metrics are recorded.
- Demo is reproducible.

## Phase 8 — Deployment and Submission

Tasks:
1. Verify available free hosting.
2. Deploy frontend.
3. Deploy backend.
4. Configure production environment.
5. Apply security controls.
6. Run production smoke tests.
7. Prepare hackathon submission.

Validation:
- Public demo works where deployed.
- No credentials are exposed.
- GitHub repository is synchronized.
- Submission materials are ready.

## MVP Definition of Done

SHIFT is complete when:

1. A technician submits maintenance knowledge.
2. Gemma extracts structured information.
3. A supervisor approves the knowledge.
4. Approved knowledge is indexed.
5. A technician asks a maintenance question.
6. Hybrid RAG retrieves relevant evidence.
7. Gemma generates a grounded answer.
8. SHIFT displays valid source citations.
9. Unapproved records are excluded.
10. The complete workflow passes tests.
