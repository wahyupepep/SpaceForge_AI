# Real Case Test Report — ProcureFlow Tiered Approval

## Test identity

- Date: 2026-11-01
- Workspace account: created with the demo analyst account, then transferred to the primary user account for review.
- Project: `ProcureFlow - Tiered Purchase Approval`
- Project ID: `4416caed-3903-4526-bd35-cd28ac0594fd`
- Requirement ID: `93f33508-7cdb-448c-8322-8ae217c8ed01`
- Workspace URL: `http://localhost:3001/projects/4416caed-3903-4526-bd35-cd28ac0594fd`

## Scenario

The existing procurement product uses a single direct-manager approval. The requested enhancement introduces sequential approval based on amount and risk, time-bounded delegation, SLA reminders and escalation, while preserving legacy history, the mobile decision contract, and exactly-once PO creation.

Thresholds used by the scenario:

- Up to Rp10 million: Direct Manager.
- Above Rp10 million through Rp100 million: Direct Manager, then Department Head.
- Above Rp100 million: Direct Manager, Department Head, then Finance Controller.
- `HIGH_RISK`: always includes Finance Controller.

## Evidence stored

1. `procureflow-approval-service.ts`: current single-manager authorization, decision, audit, and PO-creation behavior.
2. `procureflow-current-state.md`: current states, data, API/event integrations, and known weaknesses.

Both files are persisted through the project evidence storage adapter and can be opened from the workspace.

## Persisted artifacts

- Requirement Baseline v1 — `VALIDATED`
- Research v1 — `VALIDATED`, authored as a manual SA fallback
- Existing System Analysis v1 — `VALIDATED`, traceable to supplied evidence

Existing System Analysis identified:

- `MODIFY`: PurchaseRequest state model, managerDecision service, PO integration.
- `NEW`: versioned approval sequence/step and approval policy.
- `REUSE`: user directory and manager relation.
- Four material gaps: routing, decision authority, lifecycle, and SLA.
- Six regression risks, including premature mobile `APPROVED`, duplicate PO creation, self-approval through delegation, threshold boundaries, and policy changes affecting in-flight requests.

## Gates exercised

| Gate | Result |
|---|---|
| Enhancement without evidence | Correctly remained incomplete |
| Two evidence uploads | Passed and persisted |
| Submit project for analysis | Passed after evidence existed |
| Requirement persistence | Passed |
| Requirement Analyst AI | Failed audibly and persisted execution audit |
| Manual validated baseline fallback | Passed; requirement became `BASELINED` and `READY` |
| Workspace server rendering | Passed; project, evidence, discovery status, and baseline rendered |

## External blocker

The configured OpenAI organization returned HTTP 429 with `credit_balance_exhausted`. Therefore no model-generated result is represented as successful. The saved baseline, research summary, and existing-system analysis are explicitly attributed to `DEMO_SYSTEM_ANALYST`.

Adding API credits and rerunning the workflow is required to test AI solution generation, design agents, QA review, and final Development Handoff end to end.

## Product finding fixed during the test

A validated manual Requirement Baseline previously changed the requirement status to `BASELINED` but left `analysis_readiness` unset. The artifact service now marks a validated baseline with `readiness=READY` as ready, allowing an honest human-authored fallback when the AI provider is unavailable.
