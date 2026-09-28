# Artifact Model

## Purpose

Artifact adalah output terstruktur, tervalidasi, dan dapat diaudit dari setiap tahap analisis SpecForge AI. Artifact bukan chat transcript. PostgreSQL menjadi source of truth dan setiap perubahan content menghasilkan versi baru.

Phase 2 belum menjalankan LLM. Requirement Baseline dibuat dari input yang dikonfirmasi user melalui Requirement Workspace; sistem tidak mengarang solusi dari raw requirement.

## Persistence model

`artifacts` menyimpan identity dan current-state metadata:

- `id`, `project_id`, dan optional `requirement_id`;
- `artifact_type`;
- `current_version`;
- `status` (`DRAFT` atau `VALIDATED`);
- `created_at` dan `updated_at`.

`artifact_versions` menyimpan snapshot immutable:

- `id` dan `artifact_id`;
- version number yang unik per artifact;
- `content_json` JSONB;
- `created_by`;
- `created_at`.

Endpoint revisi mengunci row metadata, menambah version berikutnya, lalu memindahkan `current_version` dalam satu transaction. Version lama tidak diubah.

Create dan create-version hanya diizinkan ketika project berstatus `READY_FOR_ANALYSIS`. Dengan demikian perubahan konteks yang mengembalikan project ke `DRAFT` juga menutup penulisan artifact sampai gate dijalankan lagi.

## Artifact types and schemas

Setiap tipe terdaftar pada `ARTIFACT_SCHEMA_REGISTRY` dan memiliki Pydantic model dengan unknown field ditolak.

| Artifact type | Schema purpose |
| --- | --- |
| `PROJECT_CONTEXT` | Snapshot konteks dan tujuan project |
| `REQUIREMENT_BASELINE` | Intent, fakta, asumsi, dan informasi yang belum diketahui |
| `RESEARCH` | Tujuan riset, temuan, sumber, dan pertanyaan terbuka |
| `EXISTING_SYSTEM_ANALYSIS` | Ringkasan sistem, komponen, flow, dan gap |
| `SOLUTION` | Scope, functional solution, process, AS-IS/GAP/TO-BE, dependency, data, assumption, dan risk |
| `PROCESS_FLOW` | Main, alternative, dan exception flow |
| `UI_PROTOTYPE` | Screen, interaction, dan reference prototype |
| `DATABASE_DESIGN` | Entity, relationship, dan database constraint |
| `API_SPECIFICATION` | Base path, endpoint, dan authentication contract |
| `TEST_SCENARIO` | Scenario, precondition, dan expected result |
| `ACCEPTANCE_CRITERIA` | Acceptance criteria terstruktur |
| `DEVELOPMENT_TASK` | Task, dependency, dan definition of done |

`REQUIREMENT_BASELINE` wajib berisi:

- `feature`;
- `business_objective`;
- `problem_statement`;
- `actors`;
- `known_requirements`;
- `business_rules`;
- `constraints`;
- `dependencies`;
- `assumptions`;
- `unknown_information`.
- `readiness`;
- `clarification_questions`;
- `blocked_reason`.

Field list boleh kosong agar ketidaklengkapan dinyatakan eksplisit. Tiga field naratif pertama wajib tersedia. Phase 3 menambahkan readiness dan clarification state pada content sehingga seluruh hasil agent ikut terversi. Payload yang tidak cocok dengan schema ditolak dengan `422 ARTIFACT_CONTENT_INVALID`.

Phase 4 memperluas `RESEARCH` menjadi common-practice, comparable-workflow, metadata, UX-pattern, technical-consideration, risk, source, dan open-question contract. `EXISTING_SYSTEM_ANALYSIS` menyimpan AS-IS summary, typed/classified component, affected component, gap analysis, regression risk, dan unknown information.

Phase 5 memperluas `SOLUTION` menjadi functional contract lengkap. Untuk enhancement, `as_is`, `gap`, dan `to_be` wajib non-empty. Solution tetap `DRAFT` ketika menunggu approval, revision, atau rejected; approval current version mengubah status artifact menjadi `VALIDATED`. Lifecycle persetujuan disimpan terpisah agar status artifact generik tidak menjadi workflow engine.

Phase 6 memperluas `PROCESS_FLOW` dengan Mermaid dan typed flow steps; `UI_PROTOTYPE` menjadi versioned file manifest dengan screen-level requirement references; `DATABASE_DESIGN` menjadi typed entity/field/relationship specification; dan `API_SPECIFICATION` menjadi typed endpoint/request/response/error contract. Seluruh artifact downstream hanya dapat ditulis setelah exact current Solution version approved.

Phase 7 memperluas `TEST_SCENARIO` menjadi typed test case dengan category, ID, precondition, steps, expected result, dan requirement trace. `ACCEPTANCE_CRITERIA` menyimpan stable ID, requirement reference, serta Given/When/Then terpisah. QA revision menerbitkan kedua artifact bersama dan tidak menimpa version sebelumnya.

Phase 8 memperluas `DEVELOPMENT_TASK` menjadi typed dependency graph. Setiap task menyimpan workstream, objective, scope, exact requirement, technical notes, dependency IDs, Acceptance Criteria IDs, dan artifact references. `execution_order` wajib topologis. Development Handoff Package bukan artifact type baru; ia adalah versioned compilation yang menunjuk exact ArtifactVersion sumber.

## API contract

- `POST /api/v1/projects/{project_id}/artifacts` membuat metadata dan version 1.
- `GET /api/v1/projects/{project_id}/artifacts` membaca current content dan version history.
- `GET /api/v1/projects/{project_id}/artifacts/{artifact_id}` membaca satu artifact.
- `POST /api/v1/projects/{project_id}/artifacts/{artifact_id}/versions` menambahkan revisi immutable.

API response menampilkan `version`, `content_json`, dan `created_by` dari current version serta array `versions` untuk audit history.

## Requirement traceability

Artifact dapat dihubungkan ke requirement melalui `requirement_id`. Pembuatan `REQUIREMENT_BASELINE` yang terhubung mengubah status requirement dari `DRAFT` menjadi `BASELINED`. Foreign key memakai `SET NULL` saat requirement dihapus agar history artifact tetap dipertahankan selama project masih ada.
