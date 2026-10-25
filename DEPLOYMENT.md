# Deployment

## Supported deployment scope

The frontend connects to FastAPI for accounts, interviews, scoring, and history. Transcripts are saved in the backend database. Browser speech recognition may additionally send audio to the browser vendor. Typing avoids that speech service but still sends answers to your backend. PDF export uses the saved results.

The API requires production secrets and managed PostgreSQL (with pgvector), Redis, and private S3-compatible storage. AI and billing need their respective provider credentials. Google login requires a public OAuth Web client ID and an authorized frontend origin; follow [Google sign-in setup](GOOGLE_SIGN_IN.md). Billing does not yet have a frontend screen. Use [the local launcher](LOCAL_DEVELOPMENT.md) to test the connected core flow first.

## Vercel frontend with a separate backend (selected target)

Use [the step-by-step Vercel + Render Free + Neon guide](DEPLOY_FREE_TIER.md) for the selected budget deployment. It includes the root `render.yaml` Blueprint, external Redis/private storage setup, automatic startup migrations, and all dashboard environment values.

Import this repository into Vercel and set **Root Directory** to `ai-interview-coach`, **Framework Preset** to Vite, and **Node.js Version** to 24.x. The checked-in `vercel.ts` sets `npm ci`, `npm run build`, output `dist`, SPA deep-link rewrites, and security headers. The configuration follows [Vercel's programmatic configuration guidance](https://vercel.com/docs/project-configuration/vercel-ts).

Set Vercel's `VITE_API_URL` to `https://your-api-domain/api/v1` and rebuild. This URL is public configuration. Never put backend secrets in `VITE_*` variables: these are public build-time values. Assign the production frontend domain after the preview smoke tests pass.

Deploy the API's `console-backend/docker/Dockerfile` on a container host with working directory/build context `console-backend`. Configure the settings below through that host's secret manager. Run `alembic upgrade head` as a one-off release job before starting the API. The image listens on port 8000; configure the host's internal service port accordingly. Readiness is `/ready`. Ensure the health check uses a host allowed by `ALLOWED_HOSTS`.

Set backend CORS to the exact Vercel production origin (and any explicitly approved preview origins), plus the API's hostname in `ALLOWED_HOSTS`. On Render its assigned hostname is added automatically. `vercel.ts` derives the exact CSP `connect-src` origin from `VITE_API_URL` and fails if it is missing or malformed. Local Vite development still uses the same-origin API proxy.

## Optional frontend container

```sh
docker build -t console-frontend:release ./ai-interview-coach
docker run --rm -p 127.0.0.1:8080:8080 console-frontend:release
```

Put an HTTPS reverse proxy in front of port 8080. The image runs unprivileged and includes SPA route fallback, asset caching, a content security policy, and `/health`. Its `/api` proxy expects a backend service named `api` on the same Docker network (as in the provided production Compose file); the standalone frontend container command above alone cannot handle API calls. Include the frontend hostname in the backend's `ALLOWED_HOSTS` when using this same-origin proxy.

For a static host, build in `ai-interview-coach` with `npm ci` and `npm run build`, then publish `dist`. Configure all application routes to serve `index.html`, retain 404s for missing assets, and apply headers equivalent to `nginx.conf`. Do not use `vite preview` as the public production server.

## Frontend and API with managed services

1. Copy `console-backend/.env.example` to `console-backend/.env`.
2. Generate a unique random secret (`python -c "import secrets; print(secrets.token_hex(32))"`). Replace all example passwords. Set:
   - `APP_ENV=production`, `DEBUG=false`.
   - `DATABASE_URL=postgresql+asyncpg://...` and the equivalent `DATABASE_URL_SYNC=postgresql+psycopg2://...`; URL-encode credentials and configure database TLS as required by your provider.
   - `REDIS_URL=rediss://...` for a managed TLS Redis instance, `RATE_LIMIT_ENABLED=true`.
   - `ALLOWED_HOSTS=["api.your-domain.com"]` and `BACKEND_CORS_ORIGINS=["https://your-domain.com"]`. Origins have no trailing slash or path.
   - `STORAGE_BACKEND=s3`, bucket/region and credentials (or workload identity). The bucket must block public access. Custom storage endpoints must use HTTPS.
   - `AI_ENABLED=false` for deterministic operation, or set the selected provider credentials. Embeddings and speech currently require an OpenAI key even when completions use another provider.
3. Back up an existing database before a release. Enable pgvector using a migration role with extension privileges. Run migrations once per release.
4. Build and start from this repository root:

```sh
docker compose -f docker-compose.production.yml build
docker compose -f docker-compose.production.yml up -d
```

The migration service must succeed before the API starts. Keep image tags/digests for rollback; set `IMAGE_TAG` to a unique release identifier in the shell. In a registry-based workflow, push reviewed images and deploy those exact digests. Take database compatibility into account before rolling back application images; do not automatically downgrade production data.

5. Route HTTPS frontend traffic to port 8080 and API traffic to port 8000. Preserve the original `Host`, forward WebSocket upgrades, and enforce request size/time limits at the proxy. Configure Uvicorn `FORWARDED_ALLOW_IPS` to the exact trusted proxy addresses so client-based limits work; do not trust arbitrary public forwarded headers. Configure HSTS at the HTTPS edge after validating the domain.
6. Verify `/health` (liveness) and `/ready` (database and Redis). API documentation is disabled in production. Configure monitored backups and retention for PostgreSQL and private uploads.

## Release checks

- Run the root CI workflow successfully, including real PostgreSQL migrations, vector search, concurrent refresh rotation, Redis limits, browser tests, dependency audits, and container builds.
- Smoke-test direct navigation and refresh on `/setup`, `/dashboard`, and a saved `/results/:id` URL. Complete a typed interview, follow-up, skip, history view, and PDF download.
- Test speech on HTTPS with microphone allowed and denied, changing input modes, silence ending recognition, and navigating away during playback.
- With deployment-specific test credentials, verify registration/login/refresh, ownership isolation, uploads/downloads, and any enabled AI/speech provider. Stripe test-mode checkout, cancellation, signatures, and retries must pass before enabling live billing.
- Set provider spending limits and appropriate per-user/IP request limits. The API does not currently enforce paid-plan quotas; Stripe plan synchronization alone is not a paywall.

## Verification in this workspace

After hosting preparation, checks on 2026-10-14 passed: 114 backend tests plus 2 real PostgreSQL/Redis integration tests, 11 frontend unit tests, 5 connected browser tests, frontend build/lint, and backend lint/format checks. PostgreSQL verification covers upgrade/schema check/downgrade/upgrade, vector retrieval, and atomic refresh rotation. The production startup command was smoke-tested with a disposable database: migrations, `/ready`, exact-origin Vercel CORS, and disabled production docs passed. The Python dependency audit reported no known vulnerabilities; the earlier npm audit also reported zero after compatible updates.

Apply `alembic upgrade head` before starting the updated production API. Revision `0003` adds interview resume references and specialty snapshots. The development SQLite launcher applies its equivalent additive upgrade automatically. Configure the API's public proxy to allow a 10 MB resume plus multipart framing; the optional Nginx frontend proxy allows 11 MB while the API checks the file-size limit itself.

The earlier network blockers for PostgreSQL and the Python dependency audit are resolved. Full container release builds still belong to CI. Real Vercel/Render deployment, Neon TLS connections, Upstash/R2 credentials, live AI provider calls, and real microphone behavior require the account-specific smoke tests in the hosting guide. No production credentials were supplied and no application was deployed.
