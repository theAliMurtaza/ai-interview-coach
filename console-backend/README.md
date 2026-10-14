# Console API

FastAPI backend for interview practice. The sibling React app uses this API for accounts, interviews, scoring, saved reports, and history. See [local connected setup](../LOCAL_DEVELOPMENT.md), [the repository guide](../README.md), and [deployment instructions](../DEPLOYMENT.md).

## Implemented

- Argon2 passwords, JWT access tokens, hashed refresh tokens with atomic rotation, logout, verified Google ID-token sign-in, profile updates, and ownership checks.
- Seed or optional AI questions, interview progression, one adaptive follow-up, scoring, completion, topic memory, analytics, and PDF reports.
- PDF/DOCX/TXT resume uploads, job descriptions, matching, learning plans, and a shared knowledge base with lexical or pgvector search.
- Authenticated voice WebSockets. Send an initial JSON `access_token`, followed by complete binary audio clips or `speak_question`. Transcripts are returned; submit an answer through the answer endpoint to persist it.
- Private local development storage or S3 storage, authenticated download URLs, Redis limits, bounded requests, signed Stripe callbacks, and signed n8n acknowledgments.

`AI_ENABLED=false` explicitly selects deterministic scoring and keyword parsing/search. Google, Stripe, speech, and AI features return service errors when their required configuration is missing. There is no email-verification delivery or password-reset flow, paid-plan quota enforcement, or frontend billing UI. The n8n endpoint acknowledges a signed callback; it does not execute a workflow.

## Development

Requires Python 3.11. From this directory:

```sh
cp .env.example .env
# Replace SECRET_KEY and POSTGRES_PASSWORD with generated secrets.
docker compose --env-file .env -f docker/docker-compose.yml up --build
```

API: `http://localhost:8000`; development docs: `/docs`; liveness: `/health`; readiness: `/ready`. Compose runs Alembic in a separate migration service before starting API workers.

Without Docker, create a Python virtual environment, install `requirements-dev.txt`, and provide local PostgreSQL and Redis URLs in `.env`:

```sh
python -m venv .venv
# Activate .venv using your shell.
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Production requires PostgreSQL. Unit tests create a disposable SQLite schema and do not need local services.

For Render Free with Neon, use the root [deployment guide](../DEPLOY_FREE_TIER.md) and `render.yaml`. `python start.py` runs migrations under a PostgreSQL advisory lock, then starts one worker on the host's `PORT`. Paste Neon direct URLs into the database environment variables; the app handles driver/TLS conversion. Production resume storage stays in a private external bucket.

## Checks

```sh
pytest -q
ruff check app tests
black --check app tests
pip-audit -r requirements.txt --disable-pip --no-deps
```

Real database/Redis checks use an isolated test stack:

```sh
docker compose -f docker/compose.test.yml up -d --wait
# Set TEST_POSTGRES_URL=postgresql+asyncpg://console:test-only-password@localhost:55432/console_test
# Set TEST_REDIS_URL=redis://localhost:56379/0
pytest tests/test_postgres.py tests/test_redis.py
docker compose -f docker/compose.test.yml down
```

The PostgreSQL test requires a fresh empty database whose name ends in `_test`. It tests upgrade/check/downgrade/upgrade, vector retrieval, and concurrent refresh rotation. Recreate the disposable test containers before rerunning. Never point these checks at production.

The active CI workflow lives at repository root, `.github/workflows/ci.yml`.

## Configuration and production

All settings are in `app/core/config.py` and `.env.example`. Production rejects placeholder secrets, debug mode, SQLite, disabled rate limits, local storage, wildcard hosts, and malformed/non-HTTPS CORS origins. Private S3 access policy, database/Redis network isolation, TLS, provider credentials, backups, and an HTTPS reverse proxy remain operator responsibilities.

Use [the deployment guide](../DEPLOYMENT.md) for release commands and smoke tests. Do not use the development Compose stack as a public production deployment.
