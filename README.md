# SpaceForge AI

SpaceForge AI is a Virtual System Analyst that turns software requirements into a structured, reviewable Development Handoff Package. The current implementation covers context intake, requirement clarification, research, existing-system analysis, human-approved solution design, flow/UI/technical specifications, QA, consistency review, and final handoff export.

## Repository layout

```text
frontend/  Next.js, TypeScript, and Tailwind CSS
backend/   FastAPI application organized by clean-architecture boundaries
docs/      Product, workflow, and architecture documentation
docker/    Container definitions for local development
```

## Quick start with Docker

1. Copy `.env.example` to `.env` if you want to override the development defaults.
2. Run `docker compose up --build`.
3. Open the dashboard at <http://localhost:3000>.
4. Check the API at <http://localhost:8000/api/v1/health> or its docs at <http://localhost:8000/docs>.

Docker Compose mounts source directories and enables reload for both applications.

## Run locally

Backend (Python 3.12+ and PostgreSQL):

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --reload
pytest
```

Frontend (Node.js 20+):

```bash
cd frontend
npm install
npm run dev
npm run lint
npm run typecheck
```

## Current scope

Phases 1–10 implement the complete MVP path from Project Context through a LangGraph-orchestrated, quality-gated Development Handoff. PostgreSQL-backed workflow state is resumable, specialist outputs remain structured and versioned, and the final package provides dependency-aware task preview, traceability, and JSON, Markdown, and Trello-ready downloads. Phase 10 adds workflow leases, bounded retries/timeouts, structured LLM telemetry, safer API errors, persistence guards, and operational documentation.

Direct Trello card creation, target-application implementation, and production identity/tenant controls remain outside the MVP. See [Development Handoff](docs/DEVELOPMENT_HANDOFF.md), [Quality Gate](docs/QUALITY_GATE.md), [Security](docs/SECURITY.md), [Observability](docs/OBSERVABILITY.md), [Error Handling](docs/ERROR_HANDLING.md), [MVP Limitations](docs/MVP_LIMITATIONS.md), and [System Architecture](docs/SYSTEM_ARCHITECTURE.md).
