# MVP Limitations

- No authentication, RBAC, tenant isolation, or application rate limiting. Deploy only on a trusted network.
- No application-level field encryption or automatic PII classification/redaction. Exact prompts and responses are retained for audit.
- Agent calls run in the API process; there is no queue, cancellation protocol, background worker, or live progress stream.
- Workflow leases prevent concurrent persistence but cannot cancel an already-running remote LLM request and do not provide provider-side exactly-once semantics.
- Local-volume prototype/export storage is an adapter baseline, not production multi-node durable storage.
- Structured logs and database audit exist, but metrics, distributed tracing, alerting, archival, and retention automation are not bundled.
- The body-size middleware validates declared `Content-Length`; production ingress must also cap chunked/streamed traffic.
- Token usage is recorded when available, but there is no aggregate budget, quota, or cost-control engine.
- AI artifacts require human judgment. Traceability uses validated identifiers but is not a formal requirements proof system.
- Trello export is preview-only and performs no external card mutation.
- Generated database/API/UI outputs are specifications and prototypes, not implementation of the target business application.
