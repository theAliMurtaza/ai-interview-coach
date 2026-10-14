"""Managed URL compatibility and fail-closed hosting startup."""

import ssl
import subprocess
from unittest.mock import Mock

import pytest
from sqlalchemy.engine import make_url

from app.core.database_urls import async_database_url, async_engine_options, sync_database_url
from tests.test_deployment import production_settings

NEON_URL = "postgresql://user:p%40ss%25word@ep-demo.neon.tech/neondb?sslmode=require&channel_binding=require"


def test_neon_url_is_accepted_and_async_tls_verifies_host():
    configured = production_settings(DATABASE_URL=NEON_URL)
    url, options = async_engine_options(configured.DATABASE_URL)
    assert url.drivername == "postgresql+asyncpg"
    assert url.password == "p@ss%word"
    assert "sslmode" not in url.query
    assert "channel_binding" not in url.query
    tls = options["connect_args"]["ssl"]
    assert tls.check_hostname
    assert tls.verify_mode == ssl.CERT_REQUIRED


def test_migration_url_retains_neon_libpq_options_and_password():
    url = make_url(sync_database_url(NEON_URL))
    assert url.drivername == "postgresql+psycopg2"
    assert url.password == "p@ss%word"
    assert dict(url.query) == {"sslmode": "require", "channel_binding": "require"}


def test_sqlite_and_plain_postgres_development_keep_working():
    url, options = async_engine_options("sqlite+aiosqlite:///:memory:")
    assert url.drivername == "sqlite+aiosqlite"
    assert options == {}
    url, options = async_engine_options("postgresql+asyncpg://user:password@localhost/db")
    assert "ssl" not in options["connect_args"]
    assert async_database_url("postgres://user:p@host/db").startswith("postgresql+asyncpg://")


def test_render_hostname_is_allowed_without_wildcards():
    configured = production_settings(RENDER_EXTERNAL_HOSTNAME="coach.onrender.com")
    assert "coach.onrender.com" in configured.ALLOWED_HOSTS
    assert "*" not in configured.ALLOWED_HOSTS
    with pytest.raises(ValueError):
        production_settings(RENDER_EXTERNAL_HOSTNAME="https://coach.onrender.com")


def test_startup_migration_failure_never_starts_server(monkeypatch):
    import start

    monkeypatch.setattr(start.os, "chdir", lambda _: None)
    monkeypatch.setenv("PORT", "10000")
    migration = Mock(side_effect=subprocess.CalledProcessError(1, "alembic"))
    server = Mock()
    monkeypatch.setattr(start.subprocess, "run", migration)
    monkeypatch.setattr(start.os, "execv", server)
    with pytest.raises(subprocess.CalledProcessError):
        start.main()
    server.assert_not_called()


def test_startup_uses_host_port_and_one_worker(monkeypatch):
    import start

    monkeypatch.setattr(start.os, "chdir", lambda _: None)
    monkeypatch.setenv("PORT", "10000")
    migration = Mock()
    server = Mock()
    monkeypatch.setattr(start.subprocess, "run", migration)
    monkeypatch.setattr(start.os, "execv", server)
    start.main()
    args = server.call_args.args[1]
    assert args[args.index("--port") + 1] == "10000"
    assert args[args.index("--workers") + 1] == "1"
    assert migration.call_args.kwargs["check"] is True
