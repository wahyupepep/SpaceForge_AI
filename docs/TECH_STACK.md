# Technical Stack

Dokumen ini adalah **source of truth** untuk pilihan teknologi SpecForge AI. Perubahan stack wajib dicatat di sini dan, bila mengubah trade-off arsitektur, di `ARCHITECTURE_DECISIONS.md`.

## Runtime dan application stack

| Area | Technology | Purpose | Reason selected | MVP scope |
| --- | --- | --- | --- | --- |
| Frontend | Next.js 16.x App Router | Web application dan server rendering | Typed React framework dengan Server Components sebagai default | Dashboard, workspace, review, approval, export |
| UI | React 19, TypeScript, Tailwind CSS 4.x | Component UI dan styling | Type safety, composability, dan utility-first design token | Responsive product UI |
| Backend | Python 3.12+, FastAPI | REST API dan application host | Async-capable, Pydantic-native, OpenAPI otomatis | Satu modular monolith |
| Validation | Pydantic v2, pydantic-settings | API/artifact validation dan configuration | Typed contract dan environment-driven settings | Semua boundary eksternal dan artifact |
| ORM | SQLAlchemy 2.x async | Relational persistence | Mature unit-of-work dan async PostgreSQL support | Repository adapter |
| Database driver | asyncpg | Async PostgreSQL transport | Sesuai async SQLAlchemy/FastAPI stack | Backend only |
| Migration | Alembic | Versioned database schema | Terintegrasi SQLAlchemy dan repeatable deployment | Semua schema change |
| Database | PostgreSQL 16 | Primary system of record | Transaction, relational integrity, UUID/timestamp/JSONB support | Business data, artifact, workflow state |
| AI integration | Official OpenAI Python SDK, Responses API | Structured model execution | First-party API dan structured output support | OpenAI-only pada MVP |
| Workflow | LangGraph | Stateful multi-agent orchestration | Conditional routing dan human-in-the-loop workflow | Ditambahkan saat workflow multi-agent diimplementasikan |
| Tests | pytest, pytest-asyncio, HTTPX/TestClient | Backend behavior verification | Mendukung async service/API tests | Service, API, artifact, workflow rules |
| Development | Docker Compose | Reproducible local stack | Satu perintah untuk frontend/backend/PostgreSQL | Development only |

## Architectural scope

- Product menggunakan modular monolith; agent adalah module dalam backend, bukan service terpisah.
- Frontend hanya mengakses backend melalui centralized REST client.
- Backend route berada di bawah `/api/v1`.
- PostgreSQL adalah source of truth untuk business data, artifact version, dan workflow state.
- Secret hanya berasal dari environment variable.
- Single-user development mode diperbolehkan, tetapi ownership field akan dipertahankan saat model project dibuat.

## Deferred technology

| Technology | Status | Trigger untuk evaluasi |
| --- | --- | --- |
| Qdrant/vector database | Deferred | Document/source-code ingestion dan semantic knowledge search benar-benar dibutuhkan |
| Redis | Deferred | Coordination, cache, rate limit, atau durable job requirement terukur muncul |
| RabbitMQ/Kafka | Deferred | Workflow panjang tidak lagi aman dijalankan oleh application worker sederhana |
| S3-compatible storage | Deferred | File perlu shared storage, scale-out, lifecycle, atau production durability |
| Microservices | Deferred | Terdapat boundary organisasi/scale/reliability yang tidak dapat dipenuhi modular monolith |
| Complex authentication | Deferred | Productization dan multi-user authorization dimulai |
| Multi-provider LLM | Out of MVP | Ada requirement provider portability yang nyata |

## Dependency policy

Dependency ditambahkan ketika memiliki peran langsung pada baseline atau fase aktif. LangGraph belum menjadi runtime dependency sampai workflow diimplementasikan. Qdrant, Redis, queue, authentication framework, dan alternate LLM SDK tidak dipasang pada Phase 0.5.

