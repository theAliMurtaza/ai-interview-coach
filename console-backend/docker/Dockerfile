# syntax=docker/dockerfile:1
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt     && useradd --create-home --uid 10001 app
COPY --chown=app:app app ./app
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app alembic.ini .
RUN mkdir /srv/uploads && chown app:app /srv/uploads
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3     CMD python -c "import json, os, urllib.request; host=json.loads(os.environ.get('ALLOWED_HOSTS', '[\"127.0.0.1\"]'))[0]; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/ready', headers={'Host':host}), timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--ws-max-size", "10485760", "--timeout-keep-alive", "5"]
