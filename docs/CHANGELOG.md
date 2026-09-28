# Changelog

Format mengikuti prinsip [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) dengan versi produk selama development awal.

## [Unreleased]

### Added

- Phase 0 repository foundation untuk frontend, backend, docs, dan Docker.
- Next.js dashboard shell dengan sidebar dan placeholder project workspace.
- FastAPI `GET /health` endpoint beserta test dasar.
- PostgreSQL, backend, dan frontend development services via Docker Compose.
- Product context, vision, architecture, workflow, development guide, dan architecture decision log.
- Frontend dependency baseline menggunakan Next.js 16 dengan audit production dependency bersih.
- Phase 0.5 async persistence baseline dengan SQLAlchemy 2.x, asyncpg, Alembic, dan empty initial migration.
- Versioned `/api/v1` health readiness endpoint dengan PostgreSQL connectivity check dan consistent error envelope.
- `LLMService`/OpenAI Responses API adapter serta `FileStorageService`/local-volume adapter.
- Structured request logging tanpa request body atau secret.
- Technical stack, database, AI, artifact storage, dan environment source-of-truth documents.
- Frontend centralized API client serta `features`, `lib`, `services`, dan `types` boundaries.
- Docker build-context exclusions dan migration-complete backend image.
- Backend readiness healthcheck sebelum frontend container dimulai.
- Phase 1 Project dan ProjectContext SQLAlchemy models dengan UUID, timezone-aware audit fields, one-to-one cascade, dan future ownership boundary.
- Alembic migrations sampai `20260927_0004` dengan schema-drift validation.
- Project CRUD API di `/api/v1/projects` dan explicit `submit-for-analysis` context gate.
- Project list, dynamic new-project form, detail/edit workspace, readiness action, dan delete action.
- AS-IS validation untuk enhancement dengan structured missing-field error.
- Backend service/API tests untuk project lifecycle dan readiness gate.
- Phase 2 Requirement entity, project-scoped CRUD API, dan `READY_FOR_ANALYSIS` intake gate.
- Requirement Workspace pada project detail untuk raw requirement, known facts, constraints, dependencies, dan manual baseline structuring.
- Artifact dan immutable ArtifactVersion persistence dengan JSONB content serta Alembic revision `20260927_0005`.
- Pydantic schema registry untuk seluruh 12 artifact type awal dan strict content validation.
- Project-scoped Artifact API untuk create, list, detail, dan append-only version creation.
- Requirement-to-artifact traceability dan automatic `BASELINED` status setelah baseline dibuat.
- Artifact model documentation serta backend schema/API contract tests.
- Phase 3 Requirement Analyst Agent melalui OpenAI Responses API dan Pydantic Structured Outputs.
- Environment-driven `OPENAI_REQUIREMENT_ANALYST_MODEL` dengan fallback ke configured reasoning model.
- `POST /api/v1/projects/{id}/analyze-requirement` untuk menghasilkan versioned Requirement Baseline.
- Persistent readiness `READY`, `NEEDS_CLARIFICATION`, dan `BLOCKED` pada requirement.
- Clarification gate, bulk answer endpoint, dan automatic re-analysis setelah seluruh jawaban tersimpan.
- Agent execution audit untuk AI request/response, provider response ID, token usage, failure, dan artifact version.
- Requirement Workspace action untuk menjalankan AI serta menjawab clarification.
- Alembic revision `20260927_0006` dan Requirement Analyst contract/test coverage.
- Phase 4 Research Agent dengan Requirement Baseline readiness gate dan hosted Responses API web search.
- Structured `RESEARCH` artifact untuk common practice, comparable workflow, metadata, UX pattern, technical consideration, risk, source, dan open question.
- Existing System Analyst dengan typed evidence intake serta automatic Project AS-IS dan Research Artifact context.
- Structured component inventory dan classification `REUSE`, `MODIFY`, `NEW`, atau `DEPRECATE`.
- Mandatory AS-IS summary, affected component, dan gap analysis validation untuk enhancement.
- Project-scoped research/existing-analysis APIs, versioned artifact persistence, shared execution audit, dan workspace actions.
- `RESEARCH_AGENT.md` dan `EXISTING_SYSTEM_ANALYST.md` specialist documentation.
- Phase 5 Solution Analyst dengan environment-driven model dan structured functional-solution contract.
- Mandatory `AS-IS`, `GAP`, dan `TO-BE` semantic validation untuk enhancement Solution.
- Persistent Solution approval lifecycle dan append-only human action audit per exact artifact version.
- `APPROVE`, `REQUEST_REVISION`, dan `REJECT` API dengan optimistic `expected_version` guard.
- Revision loop yang menyimpan note sebelum re-analysis dan menambah immutable Solution version.
- Central technical-design approval gate serta workspace review dan approval actions.
- Artifact API downstream gate agar technical-design restriction tidak dapat dilewati lewat CRUD generik.
- Alembic revision `20260927_0007`, test coverage, dan `WORKFLOW_STATE_MACHINE.md`.
- Phase 6 Flow Designer dengan Mermaid, structured main/alternative/exception flow, state transition, dan traceability.
- UI Prototype Agent dengan browser-openable self-contained HTML/CSS/vanilla-JavaScript screens.
- Versioned prototype file manifest, local file storage, scoped browser endpoint, dan CSP sandbox isolation.
- Technical Architect yang menghasilkan typed `DATABASE_DESIGN` dan `API_SPECIFICATION` dalam satu execution.
- Database classification `REUSE`/`ALTER`/`NEW` dan API classification `REUSE`/`MODIFY`/`NEW`/`DEPRECATED`.
- Parallel post-approval Flow/Technical commands serta UI dependency gate pada validated Process Flow.
- Environment-driven model overrides dan larger prototype output-token ceiling.
- `UI_PROTOTYPE_STANDARD.md` dan `TECHNICAL_ARTIFACT_STANDARD.md`.
- Phase 7 QA Analyst dengan typed positive/negative/validation/boundary/permission/workflow/integration/regression scenarios.
- Given/When/Then `ACCEPTANCE_CRITERIA` contract dengan item-level requirement traceability.
- SA Reviewer consistency analysis untuk Requirement, Solution, Flow, UI, Database, API, Test, permission, serta AS-IS/TO-BE.
- Persistent quality workflow dengan `PASS`, `REVISION_REQUIRED`, reviewed-version snapshot, dan stale-review detection.
- Reviewer-driven revision routing ke Flow Designer, UI Prototype Agent, Technical Architect, atau QA Analyst.
- Configurable `QUALITY_MAX_REVISIONS` guard dan terminal `MAX_REVISIONS_REACHED` state.
- Development Handoff gate yang hanya membuka `DEVELOPMENT_TASK` setelah current artifacts memperoleh reviewer PASS.
- Alembic revision `20260927_0008`, quality API/workspace, `QUALITY_GATE.md`, dan `TRACEABILITY_MODEL.md`.
- Phase 8 Development Planner dengan validated dependency graph, topological execution order, dan authority-only traceability.
- Two-step task preview dan Development Handoff generation dengan optimistic task-version guard.
- Immutable 13-section Handoff Package yang menyertakan HTML prototype source dan deterministic Technical Specification.
- JSON, Markdown, dan Trello-ready JSON exports melalui `FileStorageService`, tanpa Trello API mutation.
- Dedicated Development Handoff page dengan artifact navigation, task preview, traceability table, dan downloads.
- Alembic revision `20260928_0009`, handoff workflow/package history, serta `DEVELOPMENT_HANDOFF.md`.
- Phase 9 SA Orchestrator berbasis LangGraph yang memakai ulang seluruh specialist service dan structured artifact contract.
- End-to-end routing dari Project Context hingga Completed dengan conditional clarification, Existing System Analysis, human approval, quality revision loop, dan handoff preview gate.
- PostgreSQL-resumable `orchestrator_workflows` serta append-only `orchestrator_executions` untuk current stage, current agent, pending action, artifact snapshot, revision history, dan failure recovery.
- Orchestrator start/resume/detail/history/list API serta project dashboard untuk stage, agent, completed stage, pending user action, artifact status, dan revision/execution history.
- Alembic revision `20260928_0010` dan integration coverage untuk enhancement approval bertingkat berdasarkan nominal.
- Phase 10 structured JSON logging dengan validated request ID, security headers, safe exception responses, dan request-size guard.
- LLM execution telemetry untuk agent, actual model, provider response ID, token usage, execution time, dan terminal status.
- Environment-configured OpenAI timeout/retry policy tanpa nested application retry serta bounded runtime configuration.
- Database-backed orchestrator execution lease untuk menolak duplicate concurrent workflow dan memungkinkan recovery setelah lease kedaluwarsa.
- Database uniqueness guard untuk logical artifact dan append-only version, plus query indexes untuk agent audit dan execution history.
- Credential redaction pada persisted failures, bounded API payload validation, global frontend error state, dan hardening regression tests.
- `SECURITY.md`, `OBSERVABILITY.md`, `ERROR_HANDLING.md`, dan `MVP_LIMITATIONS.md` sebagai operational hardening baseline.
- Alembic revision `20260928_0011` untuk duration telemetry, workflow lease, artifact uniqueness, dan audit indexes.

### Decisions

- Modular monolith, PostgreSQL source of truth, immutable artifact versioning, dan persistent human-approval gate sebagai fondasi MVP.
- OpenAI-only MVP, LangGraph khusus orchestration, local storage melalui S3-ready abstraction, dan tanpa Redis/message queue pada initial MVP.

### Changed

- Runtime backend dikunci ke Python 3.12+ dan frontend styling ke Tailwind CSS 4.x.
- Health route dipindahkan dari `/health` ke `/api/v1/health`.
- Artifact storage documentation diubah dari planned shape menjadi Phase 2 implementation contract.
