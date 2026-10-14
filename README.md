# Console — interview coach

This repository contains a connected React frontend and FastAPI backend:

- `ai-interview-coach/`: React/Vite browser app with account login, spoken or typed interviews, saved history, and PDF export.
- `console-backend/`: FastAPI service with authentication, interviews, optional AI evaluation, resume parsing, job matching, learning plans, analytics, private files, voice sockets, and Stripe callbacks.

The frontend calls the API for authentication, resume uploads, specialty-based interviews, scoring, follow-ups, reports, and history. In-progress interviews resume after refresh. Job matching and subscriptions do not yet have frontend screens.

## Run locally

Start both on Windows (Node 24 and Python 3.11):

```powershell
powershell -ExecutionPolicy Bypass -File .\run-local.ps1
```

Open http://127.0.0.1:5173 and create an account. The local launcher uses persistent SQLite and needs no Docker/API keys. See [local setup and troubleshooting](LOCAL_DEVELOPMENT.md).

## Verify

For the selected hosted setup, follow [Vercel + Render Free + Neon deployment](DEPLOY_FREE_TIER.md). The root Render Blueprint configures the API; Vercel's configuration automatically permits the API origin you supply.

```sh
cd ai-interview-coach
npm ci
npm run lint
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

For an installed browser, `PLAYWRIGHT_EXECUTABLE_PATH` can specify its executable instead of downloading Chromium. Browser tests use deterministic speech mocks; microphone permission, OS voices, and real audio transcription need a manual HTTPS smoke test.

Root GitHub Actions verifies both applications, runs PostgreSQL/Redis integration tests on disposable services, audits dependencies, and builds both container images.

See [deployment and release checks](DEPLOYMENT.md) before publishing. Do not commit `.env`, credentials, uploads, or local databases.
