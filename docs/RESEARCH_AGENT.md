# Research Agent

## Purpose

Research Agent menghasilkan insight eksternal yang relevan setelah Requirement Baseline berstatus `READY`. Ia membantu tahap analisis berikutnya memahami praktik umum dan risiko tanpa memilih final solution.

## Gate and input

`POST /api/v1/projects/{project_id}/research` menerima `requirement_id`. Backend wajib menemukan:

- project berstatus `READY_FOR_ANALYSIS`;
- requirement dengan `analysis_readiness=READY`;
- current `REQUIREMENT_BASELINE` artifact.

Agent menerima current baseline content saja. Raw ORM object, clarification transcript, dan artifact yang belum tervalidasi tidak diberikan.

## Responsibility

Structured output mencakup:

- research objective;
- common practices;
- comparable workflows;
- common metadata;
- UX patterns;
- technical considerations;
- relevant risks;
- sources dan pernyataan yang didukung tiap sumber;
- open questions.

Technical consideration adalah constraint atau trade-off untuk analisis berikutnya, bukan technical design.

## Web search

Research Agent memakai hosted `web_search` tool pada OpenAI Responses API bila `RESEARCH_WEB_SEARCH_ENABLED=true`. Sumber yang digunakan disimpan sebagai title, URL, dan supported claim. Saat ditampilkan di UI, URL dibuat visible dan clickable.

Web search dapat dimatikan untuk environment terbatas. Dalam mode tersebut agent tetap menghasilkan insight dari configured model tetapi tidak boleh mengarang sumber; `sources` dapat kosong.

## Forbidden responsibility

Research Agent tidak boleh:

- menentukan final solution;
- memilih arsitektur atau teknologi final;
- membuat database design atau API specification;
- membuat UI design;
- mengubah Requirement Baseline;
- menyatakan praktik umum sebagai mandatory rule tanpa evidence.

## Persistence and audit

Output divalidasi sebagai `ResearchAgentOutput` dan `ResearchContent`, lalu disimpan sebagai immutable `RESEARCH` artifact version. Re-run menambah version baru. `AgentExecution` menyimpan exact request, configured web-search tool, structured response, provider response ID, token usage, status, error, dan produced artifact-version ID.

Model berasal dari `OPENAI_RESEARCH_MODEL` dengan fallback ke `OPENAI_DEFAULT_MODEL`.

## Errors

- requirement belum `READY`: `409 REQUIREMENT_NOT_READY`;
- baseline tidak ditemukan: `409 ARTIFACT_DEPENDENCY_MISSING`;
- API key tidak tersedia: `503 SERVICE_UNAVAILABLE`;
- provider, refusal, parse, validation, atau persistence failure: `502 AGENT_EXECUTION_FAILED` dan failed execution audit.

