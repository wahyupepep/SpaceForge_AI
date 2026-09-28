# Error Handling

## API contract

Expected failures use a stable envelope containing `error.code`, `error.message`, optional `error.details`, and `request_id`. Validation errors return `422`; missing resources return `404`; state/version/concurrency conflicts return `409`; oversized declared payloads return `413`; unavailable dependencies return `503`. Unexpected exceptions return a generic `500` response while details remain server-side.

## LLM failures

Provider timeout and retry behavior is configured by `OPENAI_TIMEOUT_SECONDS` and `OPENAI_MAX_RETRIES`. The application does not add a second nested provider retry loop. A response must parse as JSON and validate against the agent's strict Pydantic contract before any artifact is persisted. Invalid JSON, schema mismatch, timeout, or provider failure creates a failed execution audit and no valid artifact version.

Never continue a gated workflow from partially parsed or unvalidated model output. A failed stage is resumable from its persisted state after the underlying problem is corrected.

## Transaction and recovery rules

- Artifact content is append-only; revision creates a new numbered version.
- Optimistic expected-version checks reject stale human approval and handoff requests.
- Logical artifact and artifact-version uniqueness constraints are the final race-condition guard; conflicts roll back and return `409 ARTIFACT_CONFLICT`.
- An orchestrator execution owns a time-bounded database lease. A second execution receives a conflict; an expired lease permits recovery after a crashed process.
- State transitions are explicit and checked before specialist execution.
- Quality revision count is bounded by `QUALITY_MAX_REVISIONS`; task dependency validation rejects cycles and duplicate task IDs.

A timeout does not prove that an external provider performed no work. Recovery is safe for SpaceForge persistence because artifacts are written only after a valid response, but the MVP does not claim provider-side exactly-once execution.
