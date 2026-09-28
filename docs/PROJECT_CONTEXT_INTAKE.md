# Project Context Intake

## Purpose

Project Context Intake adalah workflow gate pertama. Ia menangkap jenis pekerjaan dan konteks bisnis sebelum requirement analysis atau agent AI boleh berjalan.

## Project types

- `NEW_SYSTEM`: membangun sistem baru secara keseluruhan.
- `NEW_FEATURE`: menambahkan menu, module, atau capability baru.
- `ENHANCEMENT`: mengubah feature atau proses yang sudah berjalan.

## Status lifecycle

```text
create → DRAFT
edit   → DRAFT, atau CONTEXT_INCOMPLETE bila enhancement masih kurang
submit + valid context   → READY_FOR_ANALYSIS
submit + incomplete AS-IS → CONTEXT_INCOMPLETE + HTTP 409
```

Setiap perubahan setelah ready mengembalikan project ke draft agar context yang berubah disubmit ulang. Sejak Phase 3, Requirement Analyst hanya dapat dijalankan setelah project mencapai `READY_FOR_ANALYSIS`.

## Enhancement invariant

Lima field berikut wajib memiliki non-whitespace content:

1. `current_flow`
2. `current_actors`
3. `current_rules`
4. `current_problem`
5. `requested_change`

Invariant diterapkan di service backend. Conditional form frontend membantu user, tetapi bukan security atau workflow authority.

## API

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/projects` | Membuat draft project dan context |
| `GET` | `/api/v1/projects` | Daftar project terbaru |
| `GET` | `/api/v1/projects/{id}` | Detail project/context |
| `PATCH` | `/api/v1/projects/{id}` | Memperbarui project/context dan menginvalidasi readiness |
| `DELETE` | `/api/v1/projects/{id}` | Menghapus aggregate dengan cascade context |
| `POST` | `/api/v1/projects/{id}/submit-for-analysis` | Menjalankan context gate |

## Frontend routes

- `/projects`: list, empty state, status, dan project type.
- `/projects/new`: create form dengan AS-IS section conditional.
- `/projects/{id}`: status, readiness action, edit form, dan delete action.

## Deliberate limitations

- Single-user development mode; `owner_id` belum diisi sampai authentication tersedia.
- Requirement Analyst, Research Agent, Existing System Analyst, Solution Analyst, Phase 6 design specialists, QA Analyst, SA Reviewer, dan Development Planner tersedia; end-to-end LangGraph execution belum diaktifkan.
- Pagination API tersedia melalui `offset`/`limit`; UI belum menyediakan pagination control.
