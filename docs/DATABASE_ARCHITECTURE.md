# Database Architecture

## Role

PostgreSQL adalah primary database dan authoritative store untuk data bisnis, artifact metadata/version, serta workflow state. Semua akses aplikasi melalui SQLAlchemy 2.x repository; frontend dan agent tidak mengakses database secara langsung.

## Data categories

Model domain mencakup atau akan mencakup:

- project dan project context;
- requirement dan clarification;
- artifact dan artifact version;
- workflow execution dan workflow state;
- agent execution;
- approval dan revision;
- audit log;
- user/ownership ketika authentication ditambahkan.

`projects` dan `project_contexts` diimplementasikan pada Phase 1. `requirements`, `artifacts`, dan `artifact_versions` diimplementasikan pada Phase 2. `agent_executions` dan `requirement_clarifications` diimplementasikan pada Phase 3. `solution_workflows` dan `solution_approvals` diimplementasikan pada Phase 5. `quality_workflows` diimplementasikan pada Phase 7. `handoff_workflows` dan `handoff_package_versions` diimplementasikan pada Phase 8. Item lain tetap target fase berikutnya, bukan izin untuk membuat tabel sebelum fasenya.

## Modeling rules

- UUID adalah identifier utama kecuali terdapat alasan terukur untuk tipe lain.
- Timestamp menggunakan timezone-aware `TIMESTAMPTZ` dan disimpan dalam UTC.
- Relasi, identity, status, ownership, dan field yang dicari/filter tetap relational.
- JSONB hanya digunakan untuk structured artifact atau metadata fleksibel yang schema aplikasinya tetap tervalidasi.
- Foreign key, unique constraint, dan index ditentukan dari invariant/query, bukan ditambahkan secara spekulatif.
- ORM object tidak pernah dikembalikan langsung dari API; Pydantic response schema membentuk contract.

## Migration policy

Alembic adalah satu-satunya mekanisme deployment schema. Perubahan model wajib disertai revision dengan `upgrade` dan `downgrade` yang direview. Application startup tidak menjalankan `metadata.create_all()`.

Phase 0.5 menyediakan baseline revision `20260927_0001`. Phase 1 menambahkan Project/ProjectContext, menghapus index redundant yang ditemukan schema-drift check, dan menambahkan nullable ownership boundary sampai revision `20260927_0004`. Docker backend menjalankan `alembic upgrade head` sebelum server dimulai.

Phase 2 menambahkan Requirement dan versioned Artifact pada revision `20260927_0005`.

Phase 3 menambahkan readiness, agent execution audit, dan clarification pada revision `20260927_0006`.

Phase 5 menambahkan persistent Solution approval state dan append-only human actions pada revision `20260927_0007`.

Phase 7 menambahkan quality decision, revision counter/limit, current review execution, issue list, dan reviewed artifact-version snapshot pada revision `20260927_0008`.

Phase 8 menambahkan handoff task pointer, lifecycle, immutable package versions, source snapshots, dan export storage keys pada revision `20260928_0009`.

## Phase 7 quality workflow model

`quality_workflows` memiliki satu row per requirement dan menyimpan `READY_FOR_REVIEW`, `REVISION_REQUIRED`, `PASSED`, atau `MAX_REVISIONS_REACHED`, revision count/maximum, current reviewer execution, structured issue JSON, dan reviewed-version JSON. Agent execution serta artifact version tetap menjadi audit detail; workflow row hanya menyimpan current authoritative gate state.

## Phase 8 handoff model

`handoff_workflows` memiliki satu row per requirement, menunjuk current Development Task ArtifactVersion, status `TASKS_READY`/`PACKAGE_READY`, dan current package number. `handoff_package_versions` bersifat append-only serta menyimpan exact source versions, canonical package JSON, task-version FK, dan JSON/Markdown/Trello storage keys.

## Phase 1 relational model

- `projects`: UUID identity, name, description, project type, business objective, status, nullable future `owner_id`, dan audit timestamps.
- `project_contexts`: one-to-one project foreign key dengan cascade delete, field AS-IS, constraints, notes, dan audit timestamps.
- PostgreSQL enums mengunci `NEW_SYSTEM`, `NEW_FEATURE`, `ENHANCEMENT` serta `DRAFT`, `CONTEXT_INCOMPLETE`, `READY_FOR_ANALYSIS`.

## Phase 2 relational model

- `requirements`: project foreign key, raw and structured intake fields, `DRAFT`/`BASELINED` status, dan audit timestamps.
- `artifacts`: project foreign key, nullable requirement trace, type, current version pointer, `DRAFT`/`VALIDATED` status, dan audit timestamps.
- `artifact_versions`: immutable JSONB snapshot, creator, version number, dan timestamp; unique per artifact/version.
- JSONB pada requirement hanya menyimpan list terstruktur; identity, status, ownership, serta relasi tetap relational.

## Async session and transaction

`asyncpg` dan SQLAlchemy async engine digunakan untuk I/O database. Satu application use case memiliki transaction boundary yang eksplisit. Operasi yang menerbitkan artifact version dan mengubah workflow state harus atomic ketika diimplementasikan.

## Phase 3 analysis model

- `requirements.analysis_readiness`: `READY`, `NEEDS_CLARIFICATION`, atau `BLOCKED`.
- `agent_executions`: request/response JSON, model, provider response ID, token usage, status, error, dan artifact-version link.
- `requirement_clarifications`: pertanyaan, jawaban user, status, actor, timestamp, dan source execution.
- AI response, artifact version, readiness transition, dan pertanyaan baru disimpan dalam satu transaction. Jawaban user di-commit sebelum re-analysis sehingga tidak hilang bila provider gagal.

## Phase 5 solution workflow model

- `solution_workflows`: one per requirement, menunjuk Solution artifact dan current pending/approved version, dengan lifecycle state terindeks.
- `solution_approvals`: append-only action dengan note, actor, timestamp, dan exact artifact-version foreign key.
- Aksi memakai expected-version guard. Successful agent output dan workflow transition disimpan atomically; revision request user di-commit sebelum provider dipanggil.

## Connectivity

`GET /api/v1/health` mengeksekusi `SELECT 1`. API mengembalikan `503 SERVICE_UNAVAILABLE` bila PostgreSQL tidak dapat dijangkau. Ini adalah readiness signal; container database memiliki `pg_isready` healthcheck.

## Backup and production concerns

Backup, point-in-time recovery, connection pooling eksternal, encryption policy, retention, dan tenant isolation ditunda sampai deployment target ditentukan. Penundaan ini tidak mengubah kewajiban migration, auditability, dan referential integrity.
