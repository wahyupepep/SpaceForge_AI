# Observability

## Structured application logs

Backend logs are newline-delimited JSON. Request completion records include event name, request ID, method, path, status code, and duration. The service accepts a caller request ID only when it matches the bounded safe character set; otherwise it generates a UUID.

Request bodies, prompts, model responses, credentials, and exception messages are not written to application logs. Full AI input/output belongs in the protected audit tables, not the runtime log stream.

## LLM execution telemetry

Every provider call emits exactly one terminal event:

- `llm_execution_completed`: agent, actual model, duration, provider response ID, and input/output/total token usage when returned by the provider.
- `llm_execution_failed`: agent, configured model, duration, status, and exception type.

The `agent_executions` table is the durable audit source for agent name, model, request/response, status, provider ID, token usage, duration, errors, and resulting artifact version. `orchestrator_executions` records workflow stage attempts and recovery history.

## Operational signals

Recommended alerts:

- increasing HTTP 5xx or LLM failure/timeout rates;
- workflows whose lease repeatedly expires;
- workflows in `FAILED`, `BLOCKED`, or `MAX_REVISIONS_REACHED`;
- token usage or latency increasing materially by agent/model;
- repeated duplicate execution or invalid-transition conflicts;
- database/storage readiness failures.

The MVP produces logs and durable audit records but does not ship a metrics backend, distributed tracing, alert manager, or log-retention policy. Those are deployment responsibilities.
