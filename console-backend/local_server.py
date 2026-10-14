"""Loopback-only development API with persistent SQLite; never use in production."""

import asyncio
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / os.environ.get("CONSOLE_LOCAL_DATA_DIR", ".local")
DATA.mkdir(exist_ok=True, parents=True)
secret_file = DATA / "secret.key"
if not secret_file.exists():
    try:
        with secret_file.open("x", encoding="utf-8") as file:
            file.write(secrets.token_hex(32))
    except FileExistsError:
        pass

# Explicit development settings isolate this launcher from any production .env.
os.environ.update(
    {
        "APP_ENV": "development",
        "DEBUG": "false",
        "SECRET_KEY": secret_file.read_text(encoding="utf-8").strip(),
        "DATABASE_URL": f"sqlite+aiosqlite:///{(DATA / 'console.db').as_posix()}",
        "DATABASE_URL_SYNC": "",
        "RATE_LIMIT_ENABLED": "false",
        "AI_ENABLED": "false",
        "STORAGE_BACKEND": "local",
        "LOCAL_STORAGE_DIR": str(DATA / "uploads"),
        "ALLOWED_HOSTS": '["localhost","127.0.0.1","test"]',
        "BACKEND_CORS_ORIGINS": '["http://localhost:5173","http://127.0.0.1:5173","http://127.0.0.1:4173"]',
        "API_V1_PREFIX": "/api/v1",
    }
)


async def initialize():
    import app.models  # noqa: F401
    from app.core.database import Base, engine
    from app.core.local_migrations import upgrade_local_database

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(upgrade_local_database)
    await engine.dispose()


if __name__ == "__main__":
    import uvicorn

    asyncio.run(initialize())
    uvicorn.run(
        "app.main:app", host="127.0.0.1", port=int(os.environ.get("CONSOLE_LOCAL_PORT", "8000"))
    )
