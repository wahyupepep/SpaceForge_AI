# System Architecture

## Phase 10 hardening

The modular-monolith boundary remains unchanged. Hardening adds a database-backed single-run lease around the resumable LangGraph workflow, append-only and uniqueness constraints around artifacts, indexed execution history, bounded OpenAI timeout/retry configuration, structured JSON telemetry, and safe API error handling. These are cross-cutting controls rather than new product capabilities.

Runtime logs intentionally contain metadata only. Detailed AI request/response data remains in protected execution audit records. See [Security](SECURITY.md), [Observability](OBSERVABILITY.md), [Error Handling](ERROR_HANDLING.md), and [MVP Limitations](MVP_LIMITATIONS.md).

## Ringkasan

SpecForge AI menggunakan modular monolith untuk MVP. Frontend dan backend terpisah sebagai deployable unit, sedangkan domain, application, dan infrastructure dipisahkan secara logis di backend. Pilihan ini menjaga delivery sederhana sambil menyediakan boundary yang dapat dikembangkan.

```text
Browser
  │
  ▼
Next.js frontend
  │ REST /api/v1
  ▼
FastAPI API layer
  ▼
Application services / domain rules
  ├── AI agents → LLMService → OpenAI Responses API
  ├── Workflows → LangGraph StateGraph → existing specialist services
  ├── Repositories → SQLAlchemy async → PostgreSQL
  └── FileStorageService → local volume (MVP) / S3-compatible (later)
```

## Frontend

Next.js 16 App Router, TypeScript, React, dan Tailwind CSS 4 menyediakan dashboard, project workspace, artifact viewer, approval action, serta export experience. Server Components digunakan secara default. Browser memakai centralized API client dengan base URL `/api/v1`; frontend tidak mengakses database atau OpenAI dan tidak menentukan validitas transisi workflow.

## Backend

Python 3.12+ dan FastAPI menyediakan REST API async serta validasi transport menggunakan Pydantic v2. Struktur modular monolith:

- `api`: HTTP request/response, dependency injection, dan `/api/v1` routing.
- `services`/`application`/`domain`: use case, provider port, dan business invariant.
- `repositories`: database access boundary.
- `db`/`models`: SQLAlchemy engine, metadata, dan relational mapping.
- `agents`: specialist implementation dalam process yang sama.
- `workflows`: LangGraph orchestration dan state machine.
- `artifacts`: artifact schema, validation, serta version management.
- `integrations`: OpenAI dan file-storage adapter.
- `core`: configuration, error, logging, serta cross-cutting concern.

Dependency mengarah ke dalam: adapter boleh bergantung pada application/domain, tetapi domain tidak mengetahui FastAPI, database, atau provider AI.

## Database

PostgreSQL menyimpan project, context, requirement, artifact version, workflow state, approval, clarification, dan execution history. SQLAlchemy 2.x async dan asyncpg menjadi persistence stack. Semua schema change memakai Alembic; Phase 0.5 menyediakan empty baseline migration tanpa mendahului model Phase 1. UUID, timezone-aware timestamps, relational columns, dan JSONB artifact digunakan sesuai aturan `DATABASE_ARCHITECTURE.md`.

Phase 1 menambahkan aggregate `Project` dengan one-to-one `ProjectContext`. Route memanggil `ProjectService`, service menerapkan readiness invariant, dan `SQLAlchemyProjectRepository` menjadi satu-satunya akses persistence. Nullable `owner_id` menjaga ownership boundary untuk authentication berikutnya tanpa menambahkan user model prematur.

Phase 2 menambahkan `RequirementService` dan `ArtifactService`. Requirement Intake hanya menerima create setelah project berstatus `READY_FOR_ANALYSIS`; read/update/delete tetap tersedia melalui resource yang berada di dalam boundary project. Raw requirement, fakta yang sudah diketahui, constraint, dan dependency disimpan tanpa menjalankan LLM atau menyusun solusi.

## AI layer

OpenAI GPT adalah satu-satunya provider MVP. Official SDK memakai Responses API melalui `LLMService`; model dan output limit berasal dari configuration, bukan agent implementation. Structured response wajib lolos Pydantic validation. Phase 3 mengaktifkan Requirement Analyst; Phase 4 menambahkan Research dan Existing System Analyst; Phase 5 menambahkan Solution Analyst dan human approval; Phase 6 menambahkan Flow Designer, UI Prototype, serta Technical Architect; Phase 7 menambahkan QA Analyst dan SA Reviewer; Phase 8 menambahkan Development Planner. Handoff Generator tidak memakai AI. Research dapat meminta hosted `web_search`; specialist lain tetap artifact/evidence-only. Provider tidak pernah dipanggil dari route, repository, atau frontend.

## Orchestration layer

Phase 9 mengaktifkan `SAOrchestratorService` berbasis LangGraph `StateGraph`. Setiap node hanya mengatur routing dan memanggil application service specialist yang sudah ada; orchestrator tidak menduplikasi prompt, agent, atau artifact writer. Node berkomunikasi melalui typed artifact, ID, status, dan version pointer—bukan free-form agent chat.

State domain disimpan pada `orchestrator_workflows`: current stage, current agent, completed stage, pending user action, artifact snapshot, revision history, serta minimal resume input. Setiap node menulis append-only `orchestrator_executions` dengan input/output routing, status, error, dan timestamp. Commit dilakukan pada boundary node, sehingga request `resume` dapat memuat cursor PostgreSQL yang sama setelah process restart. Tabel dikelola Alembic; library tidak membuat schema checkpoint tersembunyi.

Graph berhenti secara eksplisit pada clarification, Solution approval, maximum-revision intervention, dan Development Task preview/export. Existing API tetap menjadi authority untuk jawaban clarification, approval, dan export; `resume` hanya merekonsiliasi state tersebut lalu melanjutkan node yang sah.

## Artifact storage

Metadata relational dan JSONB artifact version disimpan di PostgreSQL. File seperti source prototype menggunakan `FileStorageService`; development adapter menulis ke named local volume dan dapat diganti S3-compatible adapter. Version bersifat immutable; revisi membuat record baru, bukan overwrite.

Artifact schema registry memetakan seluruh artifact type ke Pydantic model. `Artifact` menyimpan current-version pointer dan status, sedangkan `ArtifactVersion` menyimpan snapshot JSONB, creator, serta timestamp. Requirement Baseline dapat ditelusuri ke `Requirement` melalui nullable foreign key. Contract rinci terdapat di `ARTIFACT_MODEL.md`.

## Workflow dan state management

PostgreSQL adalah source of truth untuk current stage, pending user action, attempt, dan execution history. LangGraph invocation selalu di-seed dari persisted cursor dan menyimpan checkpoint domain pada setiap node boundary. API action menggunakan gate/version guard pada operasi yang dapat dieksekusi ulang.

Phase 5 menyimpan solution stage pada `SolutionWorkflow`, bukan pada browser atau chat. Human action menunjuk exact immutable version dan memakai optimistic expected-version guard. Hanya `APPROVED` yang membuka technical-design gate; revision dan rejection tidak dapat melewatinya.

Phase 6 mengekspos independent Flow dan Technical commands setelah approval. UI command memiliki dependency ke current Process Flow. Prototype HTML disimpan melalui `FileStorageService` dan disajikan dengan CSP sandbox; database menyimpan manifest di immutable artifact version.

Phase 7 menyimpan authoritative quality state pada `QualityWorkflow`. Reviewer decision menunjuk version snapshot seluruh input sehingga PASS otomatis stale bila artifact berubah. Revision command merutekan issue ke owning specialist dan guard persisten menghentikan loop setelah configured maximum.

Phase 8 menyimpan task-preview state dan immutable package history pada Handoff Workflow. Generator membaca exact reviewed artifact versions, memasukkan prototype source dari FileStorageService, lalu menulis JSON/Markdown/Trello-ready export melalui abstraction yang sama.

Phase 9 menambahkan end-to-end cursor per requirement. Routing `ENHANCEMENT` selalu melewati Existing System Analysis; requirement yang belum `READY` tidak mencapai solution; design memeriksa current Solution `APPROVED`; Handoff memeriksa quality `PASSED`; reviewer revision kembali ke owning specialist satu group per loop dan tunduk pada `QUALITY_MAX_REVISIONS`.

## Hubungan komponen

1. Frontend mengirim command atau query melalui API.
2. API memvalidasi payload dan memanggil application use case.
3. Use case memeriksa domain invariant dan workflow gate.
4. Infrastructure memuat/menyimpan aggregate serta memanggil model atau hosted tool hanya bila stage dan agent contract mengizinkannya.
5. Orchestrator mengeksekusi specialist yang diizinkan state.
6. Artifact tervalidasi disimpan sebagai versi baru dalam transaction yang sama dengan state transition.
7. Frontend menampilkan state server dan meminta user action bila workflow berhenti pada gate.

## Development topology

Docker Compose menjalankan `frontend`, `backend`, dan `db`. Source di-mount untuk hot reload. Hanya secret/configuration yang berasal dari environment; repository menyediakan `.env.example` tanpa secret production.

Qdrant, Redis, RabbitMQ, dan Kafka tidak dijalankan karena belum memiliki requirement aktif. Job queue dan vector retrieval adalah extension point, bukan infrastructure baseline.
