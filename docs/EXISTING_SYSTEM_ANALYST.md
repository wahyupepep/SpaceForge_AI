# Existing System Analyst

## Purpose

Existing System Analyst memetakan bukti sistem saat ini terhadap Requirement Baseline. Specialist ini terutama dipakai untuk `NEW_FEATURE` dan `ENHANCEMENT`, tetapi contract tetap dapat dijalankan untuk `NEW_SYSTEM` ketika evidence sistem terkait tersedia.

## Gate and input

`POST /api/v1/projects/{project_id}/analyze-existing-system` menerima `requirement_id` dan maksimal 50 evidence item. Gate sama dengan Research Agent: project dan Requirement Baseline harus siap.

Evidence type:

- `USER_DESCRIPTION`;
- `SOURCE_CODE_METADATA`;
- `DATABASE_SCHEMA`;
- `API_DOCUMENTATION`;
- `EXISTING_DOCUMENTATION`;
- `SCREENSHOT_DESCRIPTION`;
- `PREVIOUS_ARTIFACT`.

Backend otomatis menambahkan Project Context/AS-IS dan current Research Artifact bila tersedia. Agent hanya menganalisis content yang diberikan; ia tidak mengakses repository, database target, API target, atau screenshot binary secara langsung.

## Output contract

Output `EXISTING_SYSTEM_ANALYSIS` berisi:

- `as_is_summary`;
- component inventory;
- affected components;
- gap analysis;
- regression risks;
- unknown information.

Setiap component memiliki name, type, evidence, rationale, impact, dan satu classification:

- `REUSE`: capability saat ini dapat dipakai tanpa perubahan material;
- `MODIFY`: capability ada tetapi evidence menunjukkan perubahan diperlukan;
- `NEW`: evidence menunjukkan capability belum ada;
- `DEPRECATE`: capability saat ini menjadi kandidat penghentian berdasarkan requirement/evidence.

Component type meliputi module, entity, master data, API, table, business rule, dan integration point.

## Enhancement invariant

Untuk `ENHANCEMENT`, output ditolak bila tidak memiliki:

- substantive AS-IS summary;
- minimal satu affected component;
- minimal satu gap-analysis item.

Klasifikasi `NEW` hanya menyatakan gap capability. Ia bukan izin untuk mendesain implementasi atau TO-BE solution.

## Forbidden responsibility

Agent tidak boleh mengarang component, table, endpoint, atau rule yang tidak didukung evidence. Agent tidak membuat final solution, database design, API specification, UI, source-code change, atau TO-BE process.

## Persistence, configuration, and errors

Output tervalidasi disimpan sebagai immutable artifact version; re-run menambah version. Seluruh request evidence, structured response, provider metadata, failure, dan artifact-version link menggunakan `AgentExecution` audit yang sama dengan agent lain.

Model berasal dari `OPENAI_EXISTING_SYSTEM_ANALYST_MODEL` dengan fallback ke `OPENAI_REASONING_MODEL`. Gate/error contract mengikuti Research Agent.

