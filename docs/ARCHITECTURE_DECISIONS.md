# Architecture Decisions

Dokumen ini adalah append-only decision log. Nomor Phase 0 direkonsiliasi pada Phase 0.5 agar baseline berikut menjadi canonical; keputusan REST dicatat sebagai ADR tambahan.

## ADR-001 — Modular Monolith

- **Status:** Accepted
- **Decision:** MVP menggunakan satu FastAPI backend dengan boundary API, application/domain service, repository, agent, workflow, artifact, dan integration. Frontend adalah deployable Next.js terpisah. Agent bukan microservice.
- **Consequence:** Transaction dan deployment sederhana; module boundary harus dijaga dan extraction hanya dilakukan berdasarkan kebutuhan operasional nyata.

## ADR-002 — PostgreSQL Primary Database

- **Status:** Accepted
- **Decision:** PostgreSQL adalah source of truth. SQLAlchemy 2.x async/asyncpg digunakan untuk akses, dan Alembic untuk seluruh migration.
- **Consequence:** Relational integrity, JSONB, dan persistent workflow tersedia; application tidak boleh memakai `create_all` sebagai deployment mechanism.

## ADR-003 — Versioned Structured Artifact

- **Status:** Accepted
- **Decision:** Artifact metadata bersifat relational dan content tervalidasi disimpan sebagai immutable ArtifactVersion JSONB. Revision membuat version baru.
- **Consequence:** Traceability dan audit kuat dengan tambahan storage serta explicit current-version management.

## ADR-004 — OpenAI-only LLM Provider for MVP

- **Status:** Accepted
- **Decision:** Official OpenAI SDK dan Responses API adalah integration tunggal. Agent memakai `LLMService`, configuration environment, dan structured output validation.
- **Consequence:** Scope tetap fokus dan business logic tidak bergantung pada raw request. Multi-provider compatibility bukan target MVP.

## ADR-005 — LangGraph Workflow Orchestration

- **Status:** Accepted
- **Decision:** LangGraph digunakan saat multi-agent workflow diimplementasikan untuk routing, conditional branch, clarification, approval, revision, dan quality gate; bukan untuk CRUD.
- **Consequence:** Workflow dapat ekspresif, tetapi persistent state PostgreSQL tetap authoritative dan LangGraph belum menjadi dependency sampai digunakan.

## ADR-006 — Local File Storage with S3-ready Abstraction

- **Status:** Accepted
- **Decision:** Generated/uploaded file memakai `FileStorageService`. Development adapter menggunakan local named volume; production adapter dapat menggunakan S3-compatible storage.
- **Consequence:** Business logic bebas dari filesystem, sementara MVP tidak membutuhkan object-storage infrastructure.

## ADR-007 — No Redis or Queue for Initial MVP

- **Status:** Accepted
- **Decision:** Workflow awal berjalan synchronous/application-background tanpa Redis, RabbitMQ, atau Kafka.
- **Consequence:** Operasi sederhana dan murah. Queue dievaluasi bila duration, retry durability, concurrency, atau scale memberikan requirement nyata.

## ADR-008 — Human-in-the-loop Approval Gate

- **Status:** Accepted
- **Decision:** Approval adalah persistent workflow transition terkait actor, timestamp, note, dan artifact version. Technical design tidak berjalan sebelum solution approved.
- **Consequence:** Keputusan dapat diaudit dan UI tidak menjadi source of truth.

## ADR-009 — Versioned REST API

- **Status:** Accepted
- **Decision:** Backend mengekspos Pydantic JSON contract di bawah `/api/v1`; ORM object tidak dikembalikan langsung.
- **Consequence:** Client terpisah dari persistence implementation dan breaking API changes memiliki version boundary.

