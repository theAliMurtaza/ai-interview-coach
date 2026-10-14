# Bug and deployment review — 2026-10-13

**Integration update:** the frontend/backend connection, resume uploads, and specialty-based questions have since been implemented. See [local development](LOCAL_DEVELOPMENT.md) for the launcher and supported connected flow, and [deployment checks](DEPLOYMENT.md) for current verification. The independent-frontend limitation below describes the initial review, before those follow-up changes.

## Fixed

- Typed submissions could evaluate a stale React-state transcript. Submission now uses the current controlled input and a synchronous guard against duplicate actions.
- Follow-ups retained the old input and reused only the latest answer's duration. The transcript is now cleared between turns, combined once, and timed across both answers. The follow-up is visible in typing mode.
- Async speech completion could start a microphone after navigation or StrictMode cleanup. Lifecycle guards ignore canceled work; speech cancellation settles pending promises. Synchronous microphone failures and unexpected recognition endings fall back to typing and preserve captured text.
- Empty/skipped frontend answers received communication points. They now score zero. Concept matching no longer rewards unrelated substrings; punctuated fillers are detected correctly. Technical sessions prioritize the chosen difficulty.
- Corrupt history could crash result/dashboard pages, and full/blocked storage could prevent results from appearing. Invalid records are filtered and current reports survive in memory with a visible persistence warning. Failed history deletion is reported.
- Long PDF transcripts could overflow off a page. Text now paginates line by line.
- Unknown client routes rendered an empty page. A recovery route is present, and Vercel/Nginx hosting configuration supports SPA deep links.
- The production secret validator accepted the distributed example secret. Placeholder/low-diversity secrets, malformed CORS origins, wildcard/malformed hosts, and insecure storage endpoints are rejected; enabled AI requires its provider configuration.
- Webhooks bypassed all request-rate limits. They now have a separately configurable admission limit.
- Unauthorized interview requests could acquire locks on another user's interview before rejecting access. Mutation locks are now restricted to the authenticated owner.
- Competing Stripe webhooks could apply an older provider snapshot after waiting for an owner lock. Subscription state is fetched again after acquiring the lock.
- Control characters in storage keys could reach filesystem handling. They are rejected.
- Production container health checks could fail when only the public API hostname was allowed. They now send an allowed Host header.
- CI was under the backend subdirectory, where GitHub does not discover it. The root workflow now checks frontend/backend, real database/Redis behavior, audits, and container builds.
- Updated vulnerable DOMPurify and source-map-js dependencies. Added Node 24 configuration, Vercel settings, deployment guidance, and optional container deployment. Lazy-loaded reports/charts reduce the initial JavaScript bundle.

## Verified and remaining

85 backend tests, 9 frontend unit tests, 3 browser regression tests, a separate real Redis integration test, frontend build/lint, and backend lint/format checks passed. npm audit reported zero vulnerabilities. Browser regression tests cover typed follow-ups, skips, report persistence/reload/PDF download, storage failure, corrupt history, and route recovery. Speech hardware is mocked.

PostgreSQL/pgvector integration, complete container builds, and Python vulnerability auditing remain unverified because of external network failures. CI contains these required checks. Provider credentials, deployed HTTPS microphone behavior, and production infrastructure still require smoke testing.

The React frontend remains independent of the backend. Accounts, server history, billing UI, and AI grading are not available in the browser app until an authenticated API integration is implemented. This review does not certify that the project is free of all possible defects.

The backend directory was already untracked when this review started. Include its intended source files when committing the release; do not assume a frontend-only commit includes the API.
