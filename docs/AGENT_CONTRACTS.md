# Agent Contracts

## Requirement Analyst

### Responsibility

Requirement Analyst adalah specialist AI pertama SpaceForge AI. Ia membaca Project Context dan satu Raw Requirement, mengekstrak fakta menjadi Requirement Baseline, membuat ketidakjelasan eksplisit, dan menentukan readiness.

Agent tidak menentukan tahap berikutnya. Application service menyimpan output, menerapkan clarification gate, dan mengelola artifact version serta audit trail.

### Input

Input model berisi:

- `project_context`: nama, deskripsi, project type, business objective, constraint, dan AS-IS untuk enhancement;
- `raw_requirement`: teks asli user;
- `requirement_context`: title serta actor, rule, constraint, dan dependency yang sudah diketahui;
- `clarification_answers`: pasangan pertanyaan/jawaban dari putaran sebelumnya.

Semua input berasal dari PostgreSQL. Agent tidak membaca database, file, API sistem target, atau browser secara langsung.

### Output

Output memakai OpenAI Structured Outputs dan divalidasi sebagai `RequirementAnalysisOutput`:

```json
{
  "baseline": {
    "feature": "string",
    "business_objective": "string",
    "problem_statement": "string",
    "actors": ["string"],
    "known_requirements": ["string"],
    "business_rules": ["string"],
    "constraints": ["string"],
    "dependencies": ["string"],
    "assumptions": ["string"],
    "unknown_information": ["string"]
  },
  "readiness": "READY | NEEDS_CLARIFICATION | BLOCKED",
  "clarification_questions": ["string"],
  "blocked_reason": "string"
}
```

Semantic invariant:

- `READY`: tidak memiliki clarification question atau blocked reason;
- `NEEDS_CLARIFICATION`: memiliki minimal satu pertanyaan spesifik dan tidak memiliki blocked reason;
- `BLOCKED`: memiliki blocked reason dan tidak memiliki clarification question.

Output disimpan sebagai `REQUIREMENT_BASELINE`. Analisis pertama membuat artifact version 1; analisis ulang menambah version tanpa mengubah version sebelumnya. `READY` menghasilkan artifact `VALIDATED`; state lain menghasilkan artifact `DRAFT`.

### Clarification gate

Saat output `NEEDS_CLARIFICATION`, setiap pertanyaan disimpan sebagai record `PENDING` dan requirement workflow berhenti. Analysis endpoint menolak eksekusi baru dengan `409 CLARIFICATION_PENDING`.

User harus mengirim tepat satu jawaban non-empty untuk seluruh pertanyaan pending. Jawaban, actor, dan timestamp disimpan sebelum Requirement Analyst otomatis dijalankan ulang. History pertanyaan lama tidak dihapus.

### API

- `POST /api/v1/projects/{project_id}/analyze-requirement` menerima `requirement_id` dan menjalankan analysis.
- `GET /api/v1/projects/{project_id}/requirements/{requirement_id}/clarifications` membaca seluruh clarification history.
- `POST /api/v1/projects/{project_id}/requirements/{requirement_id}/clarifications/answer` menyimpan seluruh jawaban pending lalu menjalankan analysis ulang.
- `GET /api/v1/projects/{project_id}/requirements/{requirement_id}/analysis-history` membaca execution audit trail.

### Forbidden responsibility

Requirement Analyst tidak boleh:

- membuat atau merancang database;
- membuat UI atau prototype;
- menentukan API;
- memilih architecture atau technology;
- membuat implementation plan;
- mendesain solusi teknis atau TO-BE process;
- mengarang rule, actor, dependency, atau fakta yang tidak diberikan.

Ketidakpastian harus masuk `assumptions` atau `unknown_information`, bukan diubah menjadi keputusan solusi.

### Runtime configuration

- Provider: OpenAI official Python SDK.
- API: Responses API structured parsing.
- Model: `OPENAI_REQUIREMENT_ANALYST_MODEL`, dengan fallback ke `OPENAI_REASONING_MODEL`.
- Credential: `OPENAI_API_KEY` server-side.
- Output ceiling: `AI_MAX_OUTPUT_TOKENS`.
- Temperature: optional `AI_TEMPERATURE`.

Tidak ada nama model di agent atau application service. Implementasi mengikuti pola Pydantic Structured Outputs pada [official OpenAI documentation](https://developers.openai.com/api/docs/guides/structured-outputs).

### Audit trail

Setiap attempt membuat `AgentExecution` sebelum provider dipanggil. Record menyimpan:

- agent dan configured model;
- exact structured AI request;
- validated AI response;
- provider response ID dan token usage;
- status `RUNNING`, `SUCCEEDED`, atau `FAILED`;
- sanitized error bila gagal;
- artifact version ID yang dihasilkan.

Jawaban user tersimpan pada `RequirementClarification` dengan `answered_by` dan `answered_at`. Artifact version menyimpan creator `REQUIREMENT_ANALYST`.

### Error handling

- Project yang belum ready: `409 PROJECT_NOT_READY`.
- Pending clarification: `409 CLARIFICATION_PENDING`.
- Set jawaban tidak lengkap/duplikat: `422 CLARIFICATION_ANSWER_INVALID`.
- API key tidak tersedia: `503 SERVICE_UNAVAILABLE` tanpa provider call.
- Refusal, missing parsed output, provider failure, atau semantic-output violation: execution menjadi `FAILED` dan API mengembalikan `502 AGENT_EXECUTION_FAILED` dengan execution ID.
- Output gagal tidak disimpan sebagai artifact version valid.

## Research Agent

Research Agent menerima current Requirement Baseline yang `READY` dan menghasilkan `RESEARCH` artifact berisi common practices, comparable workflows, common metadata, UX patterns, technical considerations, risks, sources, dan open questions. Hosted web search dapat digunakan, tetapi agent hanya memberi insight dan dilarang memilih final solution. Contract lengkap terdapat di `RESEARCH_AGENT.md`.

## Existing System Analyst

Existing System Analyst menerima Project Context, Requirement Baseline, typed evidence, dan current Research Artifact bila tersedia. Ia menginventarisasi module, entity, master data, API, table, business rule, integration point, serta regression risk dan mengklasifikasikannya sebagai `REUSE`, `MODIFY`, `NEW`, atau `DEPRECATE`.

Untuk `ENHANCEMENT`, AS-IS summary, affected component, dan gap analysis wajib terisi. Agent dilarang membuat TO-BE atau final solution. Contract lengkap terdapat di `EXISTING_SYSTEM_ANALYST.md`.

Kedua agent memakai Responses API structured parsing, environment-driven model, immutable artifact version, dan `AgentExecution` audit contract yang sama dengan Requirement Analyst.

## Solution Analyst

Solution Analyst menerima Project Context, current Requirement Baseline yang `READY`, current Research Artifact, dan Existing System Analysis bila tersedia. Pada revision, agent juga menerima complete previous Solution serta note user.

Output `SOLUTION` berisi `summary`, `scope`, `out_of_scope`, `actors`, `functional_requirements`, `business_rules`, `proposed_process`, `alternative_flow`, `exception_flow`, `dependencies`, `integration_requirements`, `data_requirements`, `assumptions`, `risks`, `as_is`, `gap`, dan `to_be`. Untuk `ENHANCEMENT`, tiga field terakhir wajib non-empty dan AS-IS tidak boleh ditulis ulang sebagai TO-BE.

Agent tidak membuat database design, API specification, UI/prototype, implementation plan, pilihan architecture/technology, atau perubahan ke sistem target. Data dan integration requirement tetap pada level fungsional.

Model berasal dari `OPENAI_SOLUTION_ANALYST_MODEL` dengan fallback `OPENAI_REASONING_MODEL`. Output diparse melalui Pydantic Structured Outputs. Missing baseline/research, semantic output invalid, provider refusal/failure, dan persistence failure tidak menghasilkan versi valid dan dicatat pada `AgentExecution`. Setelah output tersimpan, workflow selalu `WAITING_USER_APPROVAL`; human action dan revision contract dijelaskan di `WORKFLOW_STATE_MACHINE.md`.

## Phase 6 design specialists

### Flow Designer

Menerima Project Context, Requirement Baseline, approved Solution, dan Existing System Analysis bila tersedia. Output `PROCESS_FLOW` berisi raw Mermaid, main flow, alternative flow, exception flow, optional state transitions, dan requirement traceability. Agent tidak membuat UI atau technical design.

### UI Prototype Agent

Menerima Requirement Baseline, approved Solution, dan validated Process Flow. Output berisi self-contained HTML screen dengan inline CSS, vanilla JavaScript, interaction summary, dan requirement references. Backend memindahkan source ke `FileStorageService` dan menyimpan manifest sebagai `UI_PROTOTYPE`. Agent dilarang memakai image mockup, framework, remote asset, network call, atau backend implementation.

### Technical Architect

Menerima input approved yang sama dengan Flow Designer. Satu execution menghasilkan `DATABASE_DESIGN` dan `API_SPECIFICATION`. Database entity diklasifikasi `REUSE`, `ALTER`, atau `NEW`; API endpoint diklasifikasi `REUSE`, `MODIFY`, `NEW`, atau `DEPRECATED`. Agent hanya membuat specification dan tidak menghasilkan implementation code.

Model berasal dari `OPENAI_FLOW_DESIGNER_MODEL`, `OPENAI_UI_PROTOTYPE_MODEL`, dan `OPENAI_TECHNICAL_ARCHITECT_MODEL`. Semua memakai Responses API structured parsing dan shared `AgentExecution` audit.

## QA Analyst

QA Analyst menerima Requirement Baseline, approved Solution, Process Flow, UI manifest beserta source HTML, Database Design, dan API Specification. Agent menghasilkan dua structured output: `TEST_SCENARIO` dan `ACCEPTANCE_CRITERIA`.

Test coverage wajib mencakup positive, negative, validation, boundary, permission, workflow, integration, dan regression. Test case wajib memiliki ID, scenario, precondition, ordered steps, expected result, dan related requirement. Acceptance criterion memakai ID, requirement reference, serta Given/When/Then eksplisit. Agent tidak boleh menciptakan business behavior atau implementation baru.

## SA Reviewer

SA Reviewer menerima seluruh input QA ditambah current Test Scenario dan Acceptance Criteria. Output `SAReviewerOutput` berisi `decision`, `summary`, dan `issues`. Decision hanya `PASS` atau `REVISION_REQUIRED`; invariant schema melarang PASS dengan issue dan revision tanpa issue.

Setiap issue memiliki target artifact, issue, severity, reason, serta recommended revision. Reviewer hanya menilai dan merutekan; ia tidak mengedit artifact. Target revision dibatasi pada artifact Phase 6/7, sementara Requirement Baseline dan approved Solution menjadi authority untuk loop ini.

Model berasal dari `OPENAI_QA_ANALYST_MODEL` dan `OPENAI_SA_REVIEWER_MODEL`, fallback ke `OPENAI_REASONING_MODEL`. Contract quality, revision, error, dan maximum guard dijelaskan di `QUALITY_GATE.md`.

## Development Planner

Development Planner hanya aktif setelah current quality snapshot memperoleh `PASS`. Input berisi Project Context, Requirement Baseline, Research, optional Existing System Analysis, approved Solution, Flow, UI manifest, Database, API, Test Scenario, Acceptance Criteria, dan source versions.

Output `DEVELOPMENT_TASK` memiliki task ID, title, workstream, objective, scope, exact authoritative requirement, technical notes, dependency IDs, existing Acceptance Criteria IDs, serta artifact references. Output juga memiliki topological `execution_order` dan aggregate traceability.

Planner dilarang membuat requirement/Acceptance Criteria baru, mengubah solution, menulis source implementation, atau mengklaim pekerjaan yang tidak didukung artifact. Application service memvalidasi authority references dan dependency graph setelah Structured Output parsing. Model berasal dari `OPENAI_DEVELOPMENT_PLANNER_MODEL`, fallback ke `OPENAI_REASONING_MODEL`.
