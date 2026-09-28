# Environment Setup

## Supported baseline

- Docker Desktop/compatible Docker daemon dan Docker Compose v2+
- Untuk native backend development: Python 3.12+
- Untuk native frontend development: Node.js 20.9+

## Configuration

Salin `.env.example` menjadi `.env`. Jangan commit `.env` atau credential.

| Variable | Required | Description |
| --- | --- | --- |
| `DATABASE_URL` | Yes | SQLAlchemy async PostgreSQL URL menggunakan `postgresql+asyncpg://` |
| `APP_ENV` | Yes | Runtime environment label |
| `BACKEND_URL` | Development | Internal backend origin bila diperlukan server-side frontend |
| `NEXT_PUBLIC_API_BASE_URL` | Yes | Browser-safe API base ending in `/api/v1`; tidak boleh mengandung secret |
| `CORS_ORIGINS` | Yes | JSON array berisi origin frontend yang diizinkan backend |
| `OPENAI_API_KEY` | Saat AI aktif | Server-only OpenAI API credential |
| `OPENAI_DEFAULT_MODEL` | Saat AI aktif | Default configured model |
| `OPENAI_REASONING_MODEL` | Saat AI aktif | Reasoning-task model |
| `OPENAI_REQUIREMENT_ANALYST_MODEL` | No | Override model khusus Requirement Analyst; fallback ke reasoning model |
| `OPENAI_RESEARCH_MODEL` | No | Override model Research Agent; fallback ke default model |
| `OPENAI_EXISTING_SYSTEM_ANALYST_MODEL` | No | Override Existing System Analyst; fallback ke reasoning model |
| `OPENAI_SOLUTION_ANALYST_MODEL` | No | Override Solution Analyst; fallback ke reasoning model |
| `OPENAI_FLOW_DESIGNER_MODEL` | No | Override Flow Designer; fallback ke default model |
| `OPENAI_UI_PROTOTYPE_MODEL` | No | Override UI Prototype Agent; fallback ke default model |
| `OPENAI_TECHNICAL_ARCHITECT_MODEL` | No | Override Technical Architect; fallback ke reasoning model |
| `OPENAI_QA_ANALYST_MODEL` | No | Override QA Analyst; fallback ke reasoning model |
| `OPENAI_SA_REVIEWER_MODEL` | No | Override SA Reviewer; fallback ke reasoning model |
| `OPENAI_DEVELOPMENT_PLANNER_MODEL` | No | Override Development Planner; fallback ke reasoning model |
| `OPENAI_TIMEOUT_SECONDS` | Yes | Per-request OpenAI timeout; default `120` detik |
| `OPENAI_MAX_RETRIES` | Yes | Retry SDK untuk transient provider failures; default `2` |
| `RESEARCH_WEB_SEARCH_ENABLED` | No | Enable hosted OpenAI web search untuk Research Agent; default `true` |
| `AI_TEMPERATURE` | No | Optional sampling control; kosong berarti SDK/model default |
| `AI_MAX_OUTPUT_TOKENS` | Yes | Default structured output ceiling |
| `AI_PROTOTYPE_MAX_OUTPUT_TOKENS` | Yes | Output ceiling untuk multi-screen prototype source |
| `QUALITY_MAX_REVISIONS` | Yes | Maximum automated quality revision executions; default `5` |
| `ORCHESTRATOR_LEASE_SECONDS` | Yes | Lease untuk mencegah concurrent workflow execution; default `900` |
| `MAX_REQUEST_BODY_BYTES` | Yes | Batas request berdasarkan declared content length; default `5242880` |
| `FILE_STORAGE_ROOT` | Yes | Root local file adapter pada development |

## Docker workflow

```bash
cp .env.example .env
docker compose up --build
```

Backend menunggu PostgreSQL healthy, menjalankan `alembic upgrade head`, lalu memulai Uvicorn. Verify:

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:3000
docker compose exec backend alembic current
```

Expected health response:

```json
{"status":"ok","service":"spaceforge-api","environment":"development","database":"ok"}
```

## Native workflow

Backend:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Validation commands

```bash
cd backend && ruff check . && pytest
cd frontend && npm run lint && npm run typecheck && npm run build
docker compose config --quiet
```

If Docker reports a missing socket, start Docker Desktop/daemon before retrying. PostgreSQL is intentionally not replaced with SQLite because the application relies on PostgreSQL behavior and will use JSONB in later phases.
