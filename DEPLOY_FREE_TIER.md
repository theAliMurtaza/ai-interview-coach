# Deploy on Vercel + Render + Neon

This setup runs the React frontend on Vercel, the Python API on Render Free, PostgreSQL on Neon, rate limits on Upstash Redis, and private resume files on Cloudflare R2. Neon supplies the database in this setup; Render runs FastAPI.

No AI subscription is required: `AI_ENABLED=false` supports resume skill detection, specialty questions, and deterministic grading. Optional AI providers are billed separately.

## 1. Prepare the repository

Push this repository to your Git provider, including **both application directories**, root `render.yaml`, the migration files, and frontend `vercel.ts`. Do not commit `.env`, `.local`, uploads, or credentials. The backend was initially untracked in this workspace, so review the files you include rather than committing only frontend changes.

Use the exact app names/URLs assigned by the hosting services in the steps below. The examples are placeholders, not working URLs.

## 2. Create the managed services

### Neon database

Create a free Neon project near your chosen Render region. In **Connect**, turn **connection pooling off** and copy the **direct** PostgreSQL connection string. Keep its TLS query parameters and URL-encoded password. Copy only the URL, not a `psql` command or surrounding quotes.

Use this same direct URL for both `DATABASE_URL` and `DATABASE_URL_SYNC`. Example format:

```text
postgresql://USER:PASSWORD@YOUR-DIRECT-HOST.neon.tech/neondb?sslmode=require&channel_binding=require
```

The app selects the asyncpg driver automatically. It adapts Neon TLS options to certificate and hostname verification; asyncpg does not implement libpq's `channel_binding` option. The migration connection retains libpq's TLS/channel-binding options. The small API pool allows at most five database connections per worker. Direct connections also allow migration advisory locks to span transactions; do not use a `-pooler` hostname for migrations.

Migrations enable the `vector` extension and create all tables, including resume specialties. Use the Neon project owner role for the initial migration. Existing local SQLite accounts and interviews are not automatically copied to Neon.

### Upstash Redis

Create a free Redis database. Copy its **TLS Redis connection URL** in the form `rediss://default:PASSWORD@HOST:6379` into `REDIS_URL`. This app uses the Redis protocol, so the REST HTTPS URL and REST token are not substitutes.

### Private R2 bucket

Create a **Standard** bucket such as `interview-coach-uploads`. Leave public access and the public development URL disabled. Create S3 API credentials with Object Read & Write access restricted to this bucket.

Record the bucket name, access key ID, secret access key, and account S3 endpoint (`https://ACCOUNT-ID.r2.cloudflarestorage.com`). Use `STORAGE_REGION=auto`. Uploads go through the API, so browser CORS on the bucket is not required for resume uploads.

## 3. Deploy the backend on Render

In Render, choose **New → Blueprint**, connect the repository, and select the root `render.yaml`. It creates one **Free** Python web service with:

| Setting | Value |
| --- | --- |
| Root directory | `console-backend` |
| Python | Latest 3.11 patch via `.python-version` |
| Build command | `pip install -r requirements.txt` |
| Start command | `python start.py` |
| Health check | `/health` |
| Workers | 1 |

The Blueprint prompts for these values:

| Environment variable | Value to enter |
| --- | --- |
| `DATABASE_URL` | Neon direct URL |
| `DATABASE_URL_SYNC` | Same Neon direct URL |
| `REDIS_URL` | Upstash `rediss://...` URL |
| `BACKEND_CORS_ORIGINS` | JSON array, e.g. `["https://your-app.vercel.app"]` |
| `STORAGE_ENDPOINT_URL` | R2 account's HTTPS S3 endpoint |
| `STORAGE_ACCESS_KEY_ID` | Bucket-scoped S3 access key ID |
| `STORAGE_SECRET_ACCESS_KEY` | Matching S3 secret |
| `STORAGE_BUCKET_NAME` | Your private bucket name |

The Blueprint generates a stable `SECRET_KEY` and configures production mode, private S3 storage, rate limits, and offline evaluation. It automatically permits Render's assigned hostname. For a custom API domain, add its hostname to `ALLOWED_HOSTS` as a JSON array. Preserve the generated secret across redeploys.

If you do not know the Vercel domain yet, use your intended HTTPS Vercel origin for now, then replace it with the exact assigned origin in step 4. Include no path or trailing slash. Avoid wildcard Vercel domains.

`start.py` runs `alembic upgrade head` before opening the server port and stops if migrations fail. PostgreSQL advisory locks serialize overlapping migration runs. This works around Render Free's lack of a pre-deploy command. It binds to Render's `PORT` and uses one worker to conserve memory. Render's native Python runtime supplies its trusted-proxy setting; when moving to another host, configure proxy trust for that host.

After deployment, open `https://YOUR-API.onrender.com/ready`. Expect `{"status":"ready"}`. `/health` checks only the running process; `/ready` checks PostgreSQL and Redis. Automated health probes use `/health` to avoid continually waking Neon and spending its compute allowance. Do not configure an uptime pinger for `/ready` on the free plan.

The example environment template is [console-backend/deploy/.env.example](console-backend/deploy/.env.example). Enter secrets in Render's environment settings, not Vercel.

## 4. Deploy the frontend on Vercel

Import the same repository into Vercel:

| Setting | Value |
| --- | --- |
| Root directory | `ai-interview-coach` |
| Framework | Vite |
| Node.js | 24.x |
| Install command | `npm ci` |
| Build command | `npm run build` |
| Output directory | `dist` |
| `VITE_API_URL` | `https://YOUR-API.onrender.com/api/v1` |

Set `VITE_API_URL` **before the first deployment**, for Production and any Preview environment you use. `vercel.ts` reads it to generate an exact API-origin Content Security Policy, SPA rewrites, and security/cache headers. Missing, non-HTTPS, or malformed API URLs fail configuration instead of producing a broken deployment. There is no need to edit the CSP manually. Keep only `vercel.ts`, not an additional `vercel.json`.

The frontend talks directly to the Render API, including multipart resume uploads. Database URLs, storage keys, Redis credentials, and `SECRET_KEY` must never appear in `VITE_*` variables.

Once Vercel assigns your domain, update Render's `BACKEND_CORS_ORIGINS` to that exact origin and redeploy the backend. For previews, add only the specific preview origins you intend to use. A preview URL is not automatically authorized by the production origin. Changes to `VITE_API_URL` require a new frontend build.

## 5. Verify the published app

1. Open the API `/ready` URL, then open the Vercel app. A sleeping free API can take roughly a minute to start; retry after it wakes.
2. Create an account and sign in. Upload a readable test PDF/DOCX/TXT and select its detected skills or enter specialties.
3. Start a three-question typed interview, submit an answer, complete it, and download the report.
4. Reload the report and dashboard. Start another session and confirm the saved resume is available.
5. Verify browser refresh directly on `/setup`, `/dashboard`, and a saved `/results/:id` URL.
6. Try voice input over HTTPS with microphone permission both allowed and denied.
7. Restart/redeploy the API and confirm the account, history, and resume still exist. Neon and R2 retain them independently of Render's filesystem.

If login is blocked by CORS, check the exact frontend origin in Render. If the console reports a CSP block, check `VITE_API_URL` and redeploy Vercel. If `/ready` fails, check Neon/Upstash credentials and quotas in Render's logs. If resume upload fails, check the private bucket credentials and endpoint. Production API documentation routes are disabled intentionally.

## Free-tier limits

Preparation verified on 2026-10-14: 114 backend tests, both real PostgreSQL/Redis integration tests, 11 frontend tests, all 5 connected browser tests, and the frontend production build passed. The production startup command, readiness, and Vercel CORS were exercised against disposable local services. The Python dependency audit found no known vulnerabilities. Cloud account credentials and a real hosted deployment remain to be verified after you configure the dashboards.

This is a deployable demo/hobby configuration, not guaranteed always-on production hosting. Limits checked on **2026-10-14**:

- Render Free sleeps after 15 idle minutes, can take about one minute to restart, and has an ephemeral filesystem. It has monthly usage limits and no free persistent disk. [Render documentation](https://render.com/docs/free)
- Neon Free has compute/storage allowances and automatic scale-to-zero. Monitor the project quotas and choose a paid plan for sustained production traffic. [Neon pricing](https://neon.com/pricing)
- Upstash has a free Redis allowance with command, bandwidth, and storage limits. Leave the database on its Free plan if avoiding paid usage. [Upstash pricing](https://upstash.com/pricing/redis)
- R2 Standard has free storage and operation allowances; usage beyond them is billed. Check activation/payment requirements in your account. [R2 pricing](https://developers.cloudflare.com/r2/pricing/)
- Check that your use fits Vercel's selected plan. [Vercel plans](https://vercel.com/docs/plans)

Source references for the checked-in host configuration: [Render Blueprint specification](https://render.com/docs/blueprint-spec), [Python selection](https://render.com/docs/python-version), [Render deployment commands](https://render.com/docs/deploys), [Vercel programmatic configuration](https://vercel.com/docs/project-configuration/vercel-ts).
