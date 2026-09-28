# Development Handoff

## Purpose

Development Handoff adalah tahap kompilasi terakhir SpaceForge AI. Ia tidak membuat requirement, solution, atau technical decision baru. Generator hanya menyusun artifact yang current, approved, dan telah memperoleh passing SA Review.

## Gate

Development Planner dan package generator hanya berjalan bila:

1. Quality Workflow tersimpan sebagai `PASSED`;
2. snapshot delapan artifact pada passing review sama dengan seluruh current version;
3. exact current Solution version masih `APPROVED`;
4. seluruh artifact sumber berstatus `VALIDATED`;
5. Research tersedia; Existing System Analysis boleh tidak tersedia untuk konteks yang memang tidak memilikinya.

Perubahan artifact setelah PASS membuat review stale dan mengunci planning maupun package generation.

## Two-step workflow

```text
Quality PASS
  │ Development Planner
  ▼
TASKS_READY
  │ user previews all tasks
  │ Generate Package(expected_task_version)
  ▼
PACKAGE_READY
  ├── development-handoff.json
  ├── development-handoff.md
  └── trello-ready.json
```

`expected_task_version` mencegah user mengekspor task version yang berubah setelah preview. Menjalankan planner kembali membuat immutable `DEVELOPMENT_TASK` version baru dan mengembalikan workflow ke `TASKS_READY`. Package version lama tetap tersedia.

## Development Planner contract

Planner menerima seluruh artifact yang lolos review, Project Context, current Research, optional Existing System Analysis, dan exact source-version map. Ia menghasilkan dependency-aware `DEVELOPMENT_TASK` artifact.

Setiap task memiliki:

- stable `id`;
- `title`;
- `workstream`;
- `objective`;
- `scope`;
- satu exact `requirement` dari Requirement Baseline atau approved Solution;
- `technical_notes`;
- `dependency` berupa task ID;
- existing Acceptance Criteria ID;
- `reference_artifact`.

Schema dan semantic validation mewajibkan unique task ID, dependency yang valid, directed acyclic graph, serta `execution_order` topologis. Service menolak requirement, Acceptance Criteria, atau artifact reference yang tidak tersedia pada approved input. Urutan Database → Backend → Frontend → Integration → QA digunakan bila memang didukung specification, bukan sebagai requirement baru.

## Package sections

Package selalu memiliki urutan berikut:

1. `01 Project Context`
2. `02 Requirement Baseline`
3. `03 Research Summary`
4. `04 AS-IS / Existing System Analysis`
5. `05 Functional Specification`
6. `06 TO-BE Process Flow`
7. `07 HTML Prototype`
8. `08 Database Design`
9. `09 API Specification`
10. `10 Technical Specification`
11. `11 Test Scenarios`
12. `12 Acceptance Criteria`
13. `13 Development Tasks`

HTML Prototype section menyertakan immutable manifest dan source HTML setiap screen. Technical Specification dikompilasi secara deterministik dari approved Solution, Database Design, API Specification, dan Research; generator tidak meminta model membuat keputusan baru.

## Formats

- **JSON:** canonical package, 13 section, source versions, traceability, dan Trello-ready content.
- **Markdown:** human-readable ordered package dengan structured section payload.
- **Trello-ready JSON:** board name, ordered workflow lists, card descriptions, labels, dependencies, checklist Acceptance Criteria, dan artifact references.

Trello-ready export hanya struktur data. Phase 8 tidak mengakses Trello API dan tidak membuat board/card eksternal.

## Persistence and audit

- `DEVELOPMENT_TASK` memakai Artifact/ArtifactVersion yang sudah ada.
- `handoff_workflows` menyimpan current task pointer, lifecycle, dan current package version.
- `handoff_package_versions` menyimpan immutable package JSON, source-version snapshot, task-version pointer, dan tiga storage key.
- Export file memakai `FileStorageService` dan unique generation path.
- Development Planner memakai `AgentExecution`; deterministic package generation tidak membuat AI execution.

## API

- `POST /api/v1/projects/{project_id}/handoff/plan`
- `GET /api/v1/projects/{project_id}/requirements/{requirement_id}/handoff`
- `POST /api/v1/projects/{project_id}/requirements/{requirement_id}/handoff/generate`
- `GET /api/v1/projects/{project_id}/requirements/{requirement_id}/handoff/packages/{version}/download/{json|markdown|trello}`

Frontend route: `/projects/{project_id}/requirements/{requirement_id}/handoff`.
