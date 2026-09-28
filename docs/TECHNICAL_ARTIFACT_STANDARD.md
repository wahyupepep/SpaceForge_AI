# Technical Artifact Standard

## Boundary

Technical Architect menghasilkan specification berdasarkan exact approved Solution. Agent menggabungkan Data Architect dan API Analyst untuk MVP, tetapi tidak membuat migration, ORM model, controller, business backend, deployment, atau source application target.

Flow Designer dapat berjalan paralel dengan Technical Architect setelah approval. UI Prototype menunggu Process Flow.

## Database Design

`DATABASE_DESIGN` wajib menyimpan summary, requirement traceability, entity, physical table, classification `REUSE`/`ALTER`/`NEW`, setiap field beserta datatype/PK/FK/nullable/default/index/unique/description, relationships, audit fields, constraints, dan assumptions.

Existing-system evidence harus menjadi dasar `REUSE` atau `ALTER`. Ketiadaan evidence tidak boleh diubah menjadi klaim bahwa table tertentu sudah tersedia.

## API Specification

`API_SPECIFICATION` wajib menyimpan base path, authentication, assumptions, traceability, method, endpoint, classification `REUSE`/`MODIFY`/`NEW`/`DEPRECATED`, purpose, actor, authorization, typed request/response fields, validations, business rules, serta error status/code/condition/fields.

Endpoint specification mendeskripsikan contract, bukan implementasi framework.

## Process Flow

`PROCESS_FLOW` memakai Mermaid source sebagai representasi utama dan structured companion fields untuk main flow, alternative flow, exception flow, serta state transition bila relevan. Mermaid disimpan tanpa Markdown fence. Setiap step mencantumkan actor, action, outcome, dan requirement references.

## Versioning and gate

Semua output disimpan sebagai immutable ArtifactVersion dan ditandai `VALIDATED` setelah schema validation. Re-run menambah version. Generation dan generic Artifact write sama-sama menolak artifact downstream bila current Solution bukan exact version yang disetujui.
