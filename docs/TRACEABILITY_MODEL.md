# Traceability Model

## Goal

Traceability menghubungkan business intent sampai test dan handoff tanpa bergantung pada urutan tampilan atau narasi chat. Relasi utama berada pada `project_id`, `requirement_id`, artifact identity, immutable version, serta logical requirement reference di dalam content.

## Trace chain

```text
Requirement
  └── REQUIREMENT_BASELINE reference
      ├── SOLUTION functional requirement / business rule
      ├── PROCESS_FLOW step.requirement_refs
      ├── UI_PROTOTYPE screen.requirement_refs
      ├── DATABASE_DESIGN entity.requirement_refs
      ├── API_SPECIFICATION endpoint.requirement_refs
      ├── TEST_SCENARIO test_case.related_requirement
      ├── ACCEPTANCE_CRITERIA criterion.requirement_ref
      └── DEVELOPMENT_TASK requirement + acceptance_criteria + reference_artifact
```

## Reference rules

- Reference harus menunjuk requirement atau rule yang benar-benar ada pada current baseline/approved solution.
- Flow step dan prototype screen tidak boleh tanpa requirement reference.
- Database entity dan API endpoint mencantumkan requirement references yang menjelaskan alasan keberadaannya.
- Setiap test case memakai tepat satu primary `related_requirement`; additional coverage dapat dijelaskan pada scenario atau aggregate traceability.
- Acceptance Criteria memakai stable `id` dan `requirement_ref` serta field Given/When/Then terpisah.
- Aggregate `requirement_traceability` dapat menyimpan ringkasan mapping, tetapi tidak menggantikan item-level reference.

## Version-aware review

`quality_workflows.reviewed_versions` menyimpan map `artifact_type → current_version` pada setiap SA Review. Map mencakup:

- `REQUIREMENT_BASELINE`;
- `SOLUTION`;
- `PROCESS_FLOW`;
- `UI_PROTOTYPE`;
- `DATABASE_DESIGN`;
- `API_SPECIFICATION`;
- `TEST_SCENARIO`;
- `ACCEPTANCE_CRITERIA`.

Passing decision hanya berlaku untuk map tersebut. Bila salah satu current version berubah, trace chain dianggap belum direview dan Development Handoff kembali terkunci.

## Revision ownership

| Artifact | Owning agent |
| --- | --- |
| `PROCESS_FLOW` | Flow Designer |
| `UI_PROTOTYPE` | UI Prototype Agent |
| `DATABASE_DESIGN`, `API_SPECIFICATION` | Technical Architect |
| `TEST_SCENARIO`, `ACCEPTANCE_CRITERIA` | QA Analyst |

SA Reviewer tidak mengedit artifact. Ia menghasilkan issue terstruktur; orchestrator meneruskan issue ke owning agent dan version hasil revisi ditambahkan secara immutable.

## Current limitation

MVP menggunakan logical string reference karena Requirement Baseline belum memiliki normalized child IDs. Reviewer memvalidasi kecocokan reference secara semantik. Future normalization dapat menambahkan durable requirement-item IDs tanpa mengubah artifact identity/version model.

## Handoff traceability

Development Planner hanya boleh memilih exact requirement string dan Acceptance Criteria ID dari approved inputs. Setiap task juga menunjuk artifact type yang mendasari pekerjaannya. Package menyalin mapping ini sebagai traceability table dan menyimpan exact version seluruh sumber. Dengan demikian export dapat ditelusuri dari task kembali ke requirement, testable outcome, artifact, dan immutable version.
