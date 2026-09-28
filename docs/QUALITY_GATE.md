# Quality Gate

## Purpose

Phase 7 memastikan seluruh specification artifact konsisten sebelum Development Handoff dapat dibuat. PostgreSQL menyimpan state gate; hasil chat atau state browser bukan authority.

## Preconditions

QA Analyst hanya dapat berjalan bila exact current Solution masih `APPROVED` dan artifact berikut tersedia serta `VALIDATED`:

- `REQUIREMENT_BASELINE`;
- `SOLUTION`;
- `PROCESS_FLOW`;
- `UI_PROTOTYPE`, termasuk source HTML setiap screen;
- `DATABASE_DESIGN`;
- `API_SPECIFICATION`.

## QA Analyst

Satu execution menghasilkan dua immutable artifact version:

- `TEST_SCENARIO`, dengan coverage `POSITIVE`, `NEGATIVE`, `VALIDATION`, `BOUNDARY`, `PERMISSION`, `WORKFLOW`, `INTEGRATION`, dan `REGRESSION`;
- `ACCEPTANCE_CRITERIA`, dengan field eksplisit `given`, `when`, dan `then`.

Setiap test case memiliki `id`, `category`, `scenario`, `precondition`, ordered `steps`, `expected_result`, dan `related_requirement`. Setiap acceptance criterion memiliki stable ID dan requirement reference.

## SA Reviewer

Reviewer membaca seluruh input QA beserta Test Scenario dan Acceptance Criteria. Pemeriksaan minimal:

- Requirement vs Flow;
- Requirement vs UI;
- UI vs Database;
- UI vs API;
- Business Rule vs Test;
- Permission vs API;
- AS-IS vs TO-BE;
- Acceptance Criteria vs Requirement.

Keputusan hanya `PASS` atau `REVISION_REQUIRED`. `PASS` tidak boleh memiliki issue. Setiap issue revision wajib menyimpan `artifact`, `issue`, `severity`, `reason`, dan `recommended_revision`.

Requirement Baseline dan approved Solution diperlakukan sebagai authority pada quality loop. Reviewer merutekan koreksi ke artifact downstream: `PROCESS_FLOW`, `UI_PROTOTYPE`, `DATABASE_DESIGN`, `API_SPECIFICATION`, `TEST_SCENARIO`, atau `ACCEPTANCE_CRITERIA`.

## Revision routing

```text
REVISION_REQUIRED
  ├── PROCESS_FLOW ───────────────► Flow Designer
  ├── UI_PROTOTYPE ───────────────► UI Prototype Agent
  ├── DATABASE_DESIGN / API_SPEC ─► Technical Architect
  └── TEST_SCENARIO / AC ─────────► QA Analyst
                                     │
                                     ▼
                              READY_FOR_REVIEW
                                     │
                                     ▼
                               SA Reviewer again
```

Issue lengkap diberikan kembali kepada agent pemilik sebagai `revision_feedback`. Technical Architect selalu menerbitkan Database dan API artifact bersama. QA Analyst selalu menerbitkan Test Scenario dan Acceptance Criteria bersama.

## Maximum revision guard

`QUALITY_MAX_REVISIONS` menentukan jumlah revision execution maksimum per requirement, default `5`. Counter disimpan pada `quality_workflows`. Ketika limit tercapai, state menjadi `MAX_REVISIONS_REACHED`, revision otomatis ditolak, dan user harus melakukan intervensi terhadap requirement/solution atau konfigurasi workflow.

## Version freshness and handoff gate

Setiap review menyimpan snapshot version seluruh delapan artifact. Development Handoff hanya unlocked bila:

1. workflow berstatus `PASSED`; dan
2. version seluruh artifact current sama persis dengan snapshot passing review.

Perubahan artifact setelah `PASS` membuat hasil review stale dan mengunci handoff tanpa menghapus audit sebelumnya. Generic Artifact API juga menolak pembuatan atau revisi `DEVELOPMENT_TASK` selama invariant ini tidak terpenuhi.

Setelah gate terbuka, Phase 8 tetap memisahkan Development Task preview dari package generation. Detail terdapat di `DEVELOPMENT_HANDOFF.md`.

## API

- `POST /api/v1/projects/{project_id}/quality/qa`
- `POST /api/v1/projects/{project_id}/quality/review`
- `POST /api/v1/projects/{project_id}/requirements/{requirement_id}/quality/revise`
- `GET /api/v1/projects/{project_id}/quality-workflows`
- `GET /api/v1/projects/{project_id}/requirements/{requirement_id}/quality-workflow`

Semua AI attempt menggunakan `AgentExecution`, environment-driven model, Pydantic Structured Outputs, provider metadata, token usage, dan sanitized failure audit yang sama dengan specialist lain.
