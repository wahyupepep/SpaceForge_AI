# Security

## Trust boundary

The browser talks only to the FastAPI backend. OpenAI credentials, database credentials, and storage paths are server-side configuration loaded from environment variables. `NEXT_PUBLIC_*` values must never contain secrets.

The MVP has no authentication, authorization, tenant isolation, or application rate limiting. It must therefore run only on a trusted network until those controls are added.

## Implemented controls

- Pydantic validates API payloads, bounds text/list sizes, and rejects unknown structured-output fields.
- Middleware rejects declared request bodies above `MAX_REQUEST_BODY_BYTES`, validates inbound request IDs, and emits `nosniff`, frame-denial, and referrer-policy headers.
- CORS origins are explicit environment configuration.
- Logs omit request bodies, prompts, API keys, and database URLs. Persisted error messages pass through credential redaction.
- Prototype files are served from a scoped storage adapter and rendered with a restrictive sandbox/CSP boundary.
- Artifact versions are append-only. Database uniqueness prevents duplicate logical artifacts and duplicate version numbers.
- Workflow gates are enforced server-side; callers cannot bypass requirement readiness, solution approval, or reviewer approval through generic artifact routes.
- A database-backed orchestrator lease prevents concurrent execution of the same workflow. Invalid or expired transitions fail closed.

## Sensitive data

Agent execution audit intentionally stores exact AI input and output for traceability. Treat project context, requirements, evidence, and agent audit records as sensitive business data. Production deployments need database encryption, encrypted backups, access control, retention rules, and documented deletion procedures.

## Production checklist

1. Add identity, project-scoped RBAC, tenant isolation, and rate limiting before internet exposure.
2. Terminate TLS at a trusted ingress and restrict API/database/storage network access.
3. Replace all development credentials; use a secret manager or injected environment variables and rotate keys regularly.
4. Restrict CORS to production origins and disable public API documentation if not required.
5. Put an ingress request-size limit in front of the application, including chunked requests.
6. Configure encrypted PostgreSQL backups, storage durability, audit retention, and recovery tests.
7. Alert on repeated validation failures, LLM failures, expired leases, and revision-limit exhaustion.

See [MVP Limitations](MVP_LIMITATIONS.md) for controls intentionally deferred.
