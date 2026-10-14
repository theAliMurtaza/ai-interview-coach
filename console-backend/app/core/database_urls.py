"""Adapt managed PostgreSQL URLs without exposing connection credentials."""

import ssl

from sqlalchemy.engine import make_url


def async_database_url(value: str) -> str:
    if value.startswith(("postgres://", "postgresql://")):
        value = "postgresql+asyncpg://" + value.split("://", 1)[1]
    return value


def sync_database_url(value: str) -> str:
    url = make_url(async_database_url(value))
    if url.drivername != "postgresql+asyncpg":
        if url.drivername != "postgresql+psycopg2":
            raise ValueError("Migrations require a PostgreSQL connection URL")
    query = dict(url.query)
    # asyncpg URLs may use ssl=require; libpq calls this sslmode.
    if "ssl" in query:
        query.setdefault("sslmode", query.pop("ssl"))
    query.pop("prepared_statement_cache_size", None)
    return url.set(drivername="postgresql+psycopg2", query=query).render_as_string(
        hide_password=False
    )


def async_engine_options(value: str) -> tuple:
    url = make_url(async_database_url(value))
    if url.drivername != "postgresql+asyncpg":
        return url, {}
    query = dict(url.query)
    sslmode = query.pop("sslmode", query.pop("ssl", None))
    # libpq's channel_binding option is unsupported by asyncpg. The API uses
    # certificate + hostname verification instead; migrations keep libpq options.
    channel_binding = query.pop("channel_binding", None)
    connect_args = {"timeout": 15, "command_timeout": 30}
    if sslmode in {"require", "verify-ca", "verify-full"} or channel_binding == "require":
        connect_args["ssl"] = ssl.create_default_context()
    elif sslmode:
        if sslmode not in {"disable", "allow", "prefer"}:
            raise ValueError("Unsupported database SSL mode")
        connect_args["ssl"] = sslmode
    return url.set(query=query), {"connect_args": connect_args}
