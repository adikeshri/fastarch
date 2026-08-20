"""FastAPI application factory — the composition root's only consumer.

``create_app`` wires together configuration, the composition root
(:mod:`app.composition.container`), middleware, centralized exception
handling, and the versioned API router. ``uvicorn app.main:app`` (or the
Docker image's entrypoint) imports the module-level ``app`` below.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.composition.container import build_container, shutdown_container
from app.infrastructure.configuration.settings import Settings, get_settings
from app.infrastructure.observability.logging import configure_logging
from app.infrastructure.observability.tracing import configure_observability, instrument_fastapi
from app.presentation.api.exception_handlers.handlers import register_exception_handlers
from app.presentation.api.health import router as health_router
from app.presentation.api.middleware.correlation import CorrelationIdMiddleware
from app.presentation.api.middleware.request_logging import RequestLoggingMiddleware
from app.presentation.api.v1.router import api_router


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    container = await build_container(settings)
    app.state.container = container
    try:
        yield
    finally:
        await shutdown_container(container)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.observability)
    configure_observability(settings.observability)

    app = FastAPI(
        title=settings.project_name,
        description=(
            "Production-grade FastAPI template built on Clean Architecture, "
            "Domain-Driven Design, CQRS, and SOLID principles."
        ),
        version="0.1.0",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        lifespan=_lifespan,
        contact={"name": "fastarch"},
        license_info={"name": "MIT"},
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.security.trusted_hosts)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    register_exception_handlers(app, settings)

    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_prefix)

    instrument_fastapi(app)

    return app


app = create_app()
