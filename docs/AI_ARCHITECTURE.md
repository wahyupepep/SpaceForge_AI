# AI Architecture

## Scope

MVP menggunakan OpenAI sebagai satu-satunya LLM provider melalui official Python SDK dan Responses API. Requirement Analyst aktif sejak Phase 3; Phase 4 menambahkan Research Agent dan Existing System Analyst; Phase 5 menambahkan Solution Analyst; Phase 6 menambahkan Flow Designer, UI Prototype, dan Technical Architect; Phase 7 menambahkan QA Analyst dan SA Reviewer; Phase 8 menambahkan Development Planner. Handoff Generator sendiri deterministik dan tidak memakai LLM.

## Boundary

```text
Validated structured artifact
  → specialist agent contract
  → LLMService port
  → OpenAI Responses API adapter
  → parsed structured output
  → Pydantic validation
  → new artifact version
```

Agent tidak memanggil raw SDK secara langsung. `LLMService` menerima prompt, model, output token limit, optional temperature, dan target Pydantic schema. `OpenAILLMService` menggunakan structured parsing dan menolak response tanpa parsed model. Contract ini mengikuti pola structured output pada [official OpenAI documentation](https://developers.openai.com/api/docs/guides/structured-outputs).

## Configuration

- `OPENAI_API_KEY`: secret, hanya environment variable.
- `OPENAI_DEFAULT_MODEL`: default agent non-reasoning/umum.
- `OPENAI_REASONING_MODEL`: model untuk task reasoning yang ditentukan contract.
- `OPENAI_REQUIREMENT_ANALYST_MODEL`: optional override Requirement Analyst.
- `OPENAI_RESEARCH_MODEL`: optional override Research Agent.
- `OPENAI_EXISTING_SYSTEM_ANALYST_MODEL`: optional override Existing System Analyst.
- `OPENAI_SOLUTION_ANALYST_MODEL`: optional override Solution Analyst.
- `OPENAI_FLOW_DESIGNER_MODEL`: optional override Flow Designer.
- `OPENAI_UI_PROTOTYPE_MODEL`: optional override UI Prototype Agent.
- `OPENAI_TECHNICAL_ARCHITECT_MODEL`: optional override Technical Architect.
- `OPENAI_QA_ANALYST_MODEL`: optional override QA Analyst.
- `OPENAI_SA_REVIEWER_MODEL`: optional override SA Reviewer.
- `OPENAI_DEVELOPMENT_PLANNER_MODEL`: optional override Development Planner.
- `RESEARCH_WEB_SEARCH_ENABLED`: mengaktifkan hosted web search untuk Research Agent.
- `AI_TEMPERATURE`: optional; tidak dikirim bila kosong.
- `AI_MAX_OUTPUT_TOKENS`: default output ceiling.
- `AI_PROTOTYPE_MAX_OUTPUT_TOKENS`: larger ceiling untuk multi-screen HTML source.
- `QUALITY_MAX_REVISIONS`: persistent revision-loop guard; default 5.

Nama model tidak ditulis di implementasi agent. Agent configuration memilih model dari centralized settings dan dapat mengaturnya secara independen.

## Agent contract

Setiap specialist mendefinisikan name, role, responsibility, input schema, output schema, allowed tools, dan forbidden actions. Agent bukan chatbot bebas. Requirement Analyst adalah contract pertama dan hanya boleh menghasilkan Requirement Baseline. Structured validation failure tidak disimpan sebagai artifact valid; execution failure dicatat.

## Execution record

Agent execution merekam agent, configured model, request/response JSON, start/end time, status, provider response ID, token usage bila tersedia, sanitized error, dan artifact version yang dihasilkan. Prompt/raw input tidak masuk application log; audit payload disimpan pada PostgreSQL dan harus mengikuti retention/access policy saat authentication diterapkan.

## Provider policy

Multi-provider abstraction sengaja tidak dibangun pada MVP. Port `LLMService` memisahkan business logic dari raw SDK untuk testability dan containment, bukan untuk menjanjikan provider portability.
