# Hosting SpaceForge AI

## Vercel compatibility

The project can use Vercel, but the current Docker Compose configuration is a local development setup, not a complete Vercel deployment configuration. Vercel currently supports both native Next.js/FastAPI deployments and OCI containers (Container runtime beta). Neither option makes the Compose database and named volumes available automatically.

References checked on 2026-11-07:

- [Vercel container deployments](https://vercel.com/kb/guide/does-vercel-support-docker-deployments)
- [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi)
- [Vercel Function limits](https://vercel.com/docs/functions/limitations)
- [Vercel environment variables](https://vercel.com/docs/environment-variables)

## Suggested deployment layout

- Deploy `frontend/` to Vercel with the Next.js framework preset, `npm ci` for installation, and `npm run build` for the build. Its existing Dockerfile runs the development server and should not be used unchanged for production.
- Run the FastAPI backend on a container host with persistent storage, or adapt it to Vercel's FastAPI/Container runtime. The existing backend Dockerfile uses `--reload`, which should be removed for production; configure the port expected by the selected host.
- Use an external PostgreSQL database. Set `DATABASE_URL` to the provider connection URL using the SQLAlchemy `postgresql+asyncpg://` dialect and configure its required TLS settings. The Docker hostname `db` works only inside the Compose network.
- Run `alembic upgrade head` as a controlled release step. The current migration command lives in Docker Compose and will not run automatically when deploying the backend without Compose.
- Persist evidence and generated prototype files. `LocalFileStorageService` writes under `FILE_STORAGE_ROOT`; on a container host, mount a persistent disk there. For Vercel, implement a durable object-storage adapter instead of relying on instance-local files.

For an all-Vercel deployment, configure separate frontend/backend services and API routing, external PostgreSQL, durable file storage, and an execution strategy for long AI workflows before publishing it.

## API routing and login

The browser currently uses `NEXT_PUBLIC_API_BASE_URL`, while server-rendered pages use `BACKEND_URL`. Both must point to the deployed backend through the appropriate route; their current Docker/localhost values are not production URLs.

Login needs particular care: the backend sets a host-only session cookie with `SameSite=Lax`, and `ServerApiClient` forwards the cookies received by the frontend. Sending browser requests directly to a separate backend hostname leaves that cookie unavailable to frontend server rendering. Different provider domains can also trigger cross-site cookie restrictions.

A suitable approach is to route `/api/v1/*` through the frontend origin to the backend, including login, logout, evidence downloads, and prototype routes. Then set:

```dotenv
# Frontend environment variables; example values only.
BACKEND_URL=https://backend.example.com
NEXT_PUBLIC_API_BASE_URL=/api/v1
```

The proxy/rewrite is not implemented in the current source. Configure and verify it before using these example values. Confirm that login's `Set-Cookie` reaches the browser on the frontend hostname and that server-rendered pages receive the session cookie.

On the backend, set `AUTH_COOKIE_SECURE=true`, restrict `CORS_ORIGINS` to the actual frontend origins where direct browser access is needed, and use `APP_ENV=production`. `APP_ENV` is only a label; it does not automatically enable these protections.

## AI execution and uploads

The orchestrator awaits a LangGraph workflow inside the HTTP request. Several sequential AI calls, retries, and quality revisions can exceed a hosting platform's request duration limit. On Vercel, configure supported function duration settings and move longer work to a durable worker/job mechanism as needed; do not assume an entire workflow fits in one invocation.

Vercel Functions also impose a 4.5 MB request/response payload limit. The application currently permits requests up to 5 MiB, so uploads that pass application validation can still fail at the platform boundary. Adjust the limit or use an authenticated direct-to-object-storage upload design if API traffic passes through Functions.

## Credentials and repository hygiene

- Keep real secrets in the hosting provider's environment-variable/secret settings. Set `OPENAI_API_KEY` and database credentials only on the backend.
- `NEXT_PUBLIC_*` values are included in browser code and must contain no secrets.
- `.gitignore` excludes environment files and common credential files throughout the repository; sanitized `.env.example`, `.env.sample`, and `.env.template` variants remain trackable.
- `.dockerignore` and `.vercelignore` additionally exclude common credential files from local deployment uploads/build contexts. Use the intended project root when invoking deployment tools; these files do not guarantee protection for arbitrarily named secret files.
- Ignore rules do not remove files already tracked by Git or erase prior commits. If a real credential is ever committed, revoke/rotate it first, then remove it from tracking and assess history cleanup.
- Replace the example `spaceforge` development database password in production.

The audit on 2026-11-07 checked the three commits reachable from GitHub's `main` (318 unique file blobs), plus the local backup history. It found no tracked private environment files, private-key files, common provider token patterns, or exact matches for sufficiently long secret values in the current local `.env`. Only `.env.example` is tracked. This is a targeted repository audit, not a guarantee that no other secret format exists.

Review [Security](SECURITY.md) before public deployment: the MVP currently lacks controls such as application rate limiting and account recovery/verification, and its own security guidance limits current use to trusted networks.
