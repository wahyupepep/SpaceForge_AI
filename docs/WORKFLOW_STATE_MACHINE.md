# Workflow State Machine

## Solution approval lifecycle

PostgreSQL adalah authority untuk lifecycle Solution. UI hanya mengirim command dan merender state server.

```text
No Solution
  │ generate (baseline READY + research tersedia)
  ▼
WAITING_USER_APPROVAL
  ├── APPROVE ───────────────► APPROVED ──► technical design unlocked
  ├── REJECT ────────────────► REJECTED
  └── REQUEST_REVISION(note) ► REVISION_REQUESTED
                                  │ Solution Analyst berhasil
                                  ▼
                            WAITING_USER_APPROVAL
                            (artifact version +1)
```

`REQUEST_REVISION` menyimpan aksi user terhadap versi aktif sebelum provider dipanggil. Bila provider gagal, state tetap `REVISION_REQUESTED`, note tidak hilang, dan execution gagal tetap diaudit. Hanya hasil revisi tervalidasi yang membuat versi baru dan mengembalikan state ke `WAITING_USER_APPROVAL`.

Command retry revision memakai note dan exact prior version yang sudah tersimpan tanpa menambah human-action record duplikat.

## Transition rules

| Current state | Command | Result | Artifact effect |
| --- | --- | --- | --- |
| none | Generate Solution | `WAITING_USER_APPROVAL` | create `SOLUTION` v1 as `DRAFT` |
| `WAITING_USER_APPROVAL` | `APPROVE` | `APPROVED` | current Solution becomes `VALIDATED` |
| `WAITING_USER_APPROVAL` | `REQUEST_REVISION` + non-empty note | `REVISION_REQUESTED`, then `WAITING_USER_APPROVAL` on success | append immutable version |
| `WAITING_USER_APPROVAL` | `REJECT` | `REJECTED` | Solution remains `DRAFT` |
| any other state | approval command | rejected with `409 SOLUTION_WORKFLOW_CONFLICT` | no change |

Setiap command membawa `expected_version`. Backend menolak command bila versi aktif sudah berubah, sehingga keputusan manusia tidak dapat diterapkan diam-diam ke versi yang berbeda.

## Technical design gate

Technical design diizinkan hanya bila `SolutionWorkflow.status == APPROVED` dan workflow menunjuk current immutable Solution ArtifactVersion. Application service technical-design berikutnya wajib memanggil `ensure_technical_design_allowed` sebelum membuat `PROCESS_FLOW`, `UI_PROTOTYPE`, `DATABASE_DESIGN`, atau `API_SPECIFICATION`. State lain menghasilkan `409 TECHNICAL_DESIGN_BLOCKED`.

Gate yang sama diterapkan pada Artifact API generik untuk seluruh artifact downstream (`PROCESS_FLOW`, `UI_PROTOTYPE`, `DATABASE_DESIGN`, `API_SPECIFICATION`, `TEST_SCENARIO`, `ACCEPTANCE_CRITERIA`, dan `DEVELOPMENT_TASK`), sehingga workflow tidak dapat dilewati dengan menulis artifact secara manual.

## Approved design fan-out

```text
APPROVED Solution
  ├── Flow Designer ──► PROCESS_FLOW ──► UI Prototype ──► UI_PROTOTYPE files
  └── Technical Architect ─────────────► DATABASE_DESIGN + API_SPECIFICATION
```

Flow Designer dan Technical Architect tidak saling bergantung dan dapat dipanggil paralel oleh client. UI Prototype selalu memeriksa Process Flow tervalidasi di server. Setiap re-run menambah immutable artifact version.

## Audit model

- `solution_workflows` menyimpan state dan pointer ke Solution serta versi aktif.
- `solution_approvals` append-only menyimpan action, note, actor, timestamp, dan exact artifact version.
- `artifact_versions` mempertahankan seluruh output Solution Analyst.
- `agent_executions` merekam request, response, configured model, token usage, error, dan produced version.

## Quality gate lifecycle

```text
All Phase 6 artifacts VALIDATED
  │ QA Analyst
  ▼
READY_FOR_REVIEW
  │ SA Reviewer
  ├── PASS ─────────────────► PASSED ──► Development Handoff unlocked
  └── REVISION_REQUIRED ────► REVISION_REQUIRED
                                  │ owning specialist revision
                                  ▼
                            READY_FOR_REVIEW
                                  │ review again
                                  └───────────────┐
                                                  │
revision_count == max ──────► MAX_REVISIONS_REACHED
```

Passing review menyimpan version snapshot Requirement, Solution, Flow, UI, Database, API, Test Scenario, dan Acceptance Criteria. Handoff hanya tetap unlocked selama seluruh current version sama dengan snapshot. Detail terdapat di `QUALITY_GATE.md`.

## Development handoff lifecycle

```text
fresh Quality PASS
  │ Plan Development Tasks
  ▼
TASKS_READY ── preview exact task version ──► Generate Package
                                                  │
                                                  ▼
                                            PACKAGE_READY
```

Planning ulang menambah `DEVELOPMENT_TASK` version dan kembali ke `TASKS_READY`. Generate command membawa `expected_task_version`; stale version ditolak. Setiap package generation menambah immutable HandoffPackageVersion dengan JSON, Markdown, dan Trello-ready export.
