# Agent Workflow

## Pipeline

```text
Project Context
  → Requirement
  → Clarification (bila diperlukan)
  → Research
  → Existing System Analysis
  → Solution
  → Human Approval
  → UI / Flow
  → Technical Design
  → QA
  → SA Review
  → Development Handoff
```

## Stage intent dan gate

1. **Project Context** menetapkan tipe pekerjaan, objective, constraint, dan AS-IS wajib untuk enhancement.
2. **Requirement** mengubah input mentah menjadi baseline terstruktur tanpa mendesain solusi.
3. **Clarification** menghentikan workflow sampai unknown information material dijawab.
4. **Research** memberi insight praktik, pattern, risiko, dan pertimbangan—bukan final solution.
5. **Existing System Analysis** mengelompokkan komponen sebagai `REUSE`, `MODIFY`, `NEW`, atau `DEPRECATE` dan menyusun gap untuk enhancement.
6. **Solution** menyusun scope, functional requirement, business rule, proses, exception, dependency, data, assumption, dan risk.
7. **Human Approval** menghentikan workflow sampai solution di-approve. Revision menghasilkan versi baru.
8. **UI / Flow** menghasilkan flow dan prototype berdasarkan solution approved.
9. **Technical Design** menghasilkan database design dan API specification; tahap ini tidak mengimplementasikan fitur target.
10. **QA** menghasilkan test scenario serta acceptance criteria yang traceable.
11. **SA Review** memeriksa konsistensi lintas artifact dan mengembalikan artifact bermasalah ke specialist dengan batas revision.
12. **Development Handoff** hanya menyusun artifact approved setelah reviewer `PASS`.

## Aturan komunikasi

- Agent membaca artifact melalui typed contract dan menghasilkan structured output.
- Free-form message dapat menjadi penjelasan, tetapi bukan sumber utama workflow state.
- Setiap output divalidasi sebelum disimpan dan tidak dapat menimpa versi sebelumnya.
- Error teknis tidak diterjemahkan menjadi keputusan bisnis; state tetap dapat dipulihkan.
- Orchestrator menentukan routing, bukan isi analisis specialist.

## Project Context gate implementation

Phase 1 mengimplementasikan gate pertama tanpa agent dan tanpa LangGraph. `submit-for-analysis` hanya mengubah project menjadi `READY_FOR_ANALYSIS` bila invariant context terpenuhi. Untuk enhancement yang belum lengkap, state menjadi `CONTEXT_INCOMPLETE` dan response menyebut field AS-IS yang kurang.

## Requirement analysis implementation

Phase 3 mengimplementasikan Requirement Analyst sebagai synchronous application workflow. Output `NEEDS_CLARIFICATION` membuat record pertanyaan dan menghentikan workflow secara persisten. Setelah seluruh jawaban disimpan, analysis dijalankan ulang dan menghasilkan Requirement Baseline version baru. LangGraph tetap ditunda sampai orchestration multi-agent benar-benar dimulai.

## Discovery analysis implementation

Phase 4 membuka Research dan Existing System Analysis hanya untuk Requirement Baseline `READY`. Research menghasilkan insight dengan optional hosted web search. Existing System Analyst memakai evidence user, Project AS-IS, dan Research Artifact terbaru untuk klasifikasi `REUSE`, `MODIFY`, `NEW`, atau `DEPRECATE`. Keduanya synchronous, versioned, dan diaudit; keduanya tidak membuat final solution.

## Solution approval implementation

Phase 5 mengaktifkan Solution Analyst setelah Requirement Baseline `READY` dan Research Artifact tersedia. Existing System Analysis disertakan bila ada. Agent menghasilkan functional solution tanpa database, API, UI, atau keputusan arsitektur teknis. Untuk enhancement, schema dan semantic validation mewajibkan `as_is`, `gap`, dan `to_be` tetap terpisah.

Setiap hasil baru berhenti pada `WAITING_USER_APPROVAL`. `APPROVE`, `REQUEST_REVISION`, dan `REJECT` adalah transition server-side yang ditautkan ke exact Solution ArtifactVersion. Revision note wajib, aksi disimpan sebelum re-execution, dan hasil revisi menambah immutable version. Technical design tetap terkunci kecuali state current solution adalah `APPROVED`. Detail state terdapat di `WORKFLOW_STATE_MACHINE.md`.

## Parallel design implementation

Phase 6 membuka dua branch independen setelah exact current Solution version `APPROVED`: Flow Designer dan Technical Architect. UI Prototype bergantung pada current validated Process Flow, sehingga dapat dimulai setelah branch flow selesai sementara technical architecture tetap independen.

Flow Designer menghasilkan structured flow dan raw Mermaid. UI Prototype menghasilkan self-contained HTML/CSS/vanilla-JavaScript per screen melalui file-storage abstraction. Technical Architect menghasilkan `DATABASE_DESIGN` dan `API_SPECIFICATION` dalam satu execution tanpa mengimplementasikan backend target. Seluruh branch membuat immutable artifact versions dan `AgentExecution` audit.

## Quality gate implementation

Phase 7 menjalankan QA Analyst setelah enam input specification tersedia. QA menghasilkan `TEST_SCENARIO` dan `ACCEPTANCE_CRITERIA` bersama, kemudian SA Reviewer membandingkan seluruh delapan artifact dan menyimpan version snapshot.

`REVISION_REQUIRED` dirutekan ke owning Phase 6/7 specialist dengan issue terstruktur sebagai feedback. Setiap hasil menambah artifact version, lalu reviewer harus dijalankan ulang. Revision counter persisten dan dibatasi `QUALITY_MAX_REVISIONS`. Development Handoff hanya terbuka untuk `PASS` yang snapshot versinya masih current.

## Development handoff implementation

Phase 8 menjalankan Development Planner setelah fresh quality `PASS`. Planner membuat dependency-aware `DEVELOPMENT_TASK` untuk preview. User kemudian mengekspor exact previewed task version melalui deterministic Handoff Generator. Generator menggabungkan 13 ordered sections ke JSON, Markdown, dan Trello-ready JSON; ia tidak memanggil model atau membuat requirement baru.

## End-to-end orchestration implementation

Phase 9 menghubungkan stage melalui LangGraph tanpa membuat ulang specialist. Cursor dan setiap node execution disimpan di PostgreSQL. Graph otomatis berjalan sampai human gate, gagal secara auditable, lalu dapat dilanjutkan melalui resume API setelah clarification, Solution approval, reviewer intervention, atau Handoff export diselesaikan pada API authority masing-masing.
