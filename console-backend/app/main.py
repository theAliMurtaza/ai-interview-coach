"""Application setup, health endpoints, observability, and orderly shutdown."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.deps import get_db
from app.core.exceptions import ServiceUnavailableError, register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestPolicyMiddleware
from app.core.redis import get_redis_pool


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    if settings.SENTRY_DSN:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
            send_default_pii=False,
            max_request_body_size="never",
        )
    try:
        yield
    finally:
        await engine.dispose()
        await get_redis_pool().aclose()
        from app.agents.llm_provider import get_llm_provider

        if get_llm_provider.cache_info().currsize:
            provider = get_llm_provider()
            if hasattr(provider, "client"):
                await provider.client.close()
            get_llm_provider.cache_clear()


def create_app() -> FastAPI:
    production = settings.APP_ENV in {"staging", "production"}
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url=None if production else "/docs",
        redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
    )
    app.add_middleware(RequestPolicyMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)

    @app.get("/", include_in_schema=False)
    async def index() -> dict:
        return {
            "service": settings.APP_NAME,
            "message": "Backend API. Open your Vercel frontend to use the interview coach.",
            "health": "/health",
            "readiness": "/ready",
            "api": settings.API_V1_PREFIX,
        }

    @app.get("/health", tags=["health"])
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/ready", tags=["health"])
    async def ready(db: AsyncSession = Depends(get_db)) -> dict:
        try:
            await db.execute(text("SELECT 1"))
            if settings.RATE_LIMIT_ENABLED:
                await get_redis_pool().ping()
        except (SQLAlchemyError, RedisError) as exc:
            raise ServiceUnavailableError("A required service is unavailable") from exc
        return {"status": "ready"}

    return app


app = create_app()
