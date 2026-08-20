"""Liveness/readiness endpoints (PRD §39).

Liveness only proves the process is up and responsive — it never touches
Postgres/Redis, so a slow/unreachable database can't cause the orchestrator
to kill and restart otherwise-healthy pods. Readiness does check downstream
dependencies, and is what should gate traffic/load-balancer routing.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.composition.container import Container
from app.presentation.api.dependencies.container import get_container

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", summary="Liveness probe")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe")
async def readiness(container: Annotated[Container, Depends(get_container)]) -> JSONResponse:
    checks: dict[str, str] = {}

    try:
        async with container.session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    try:
        await container.redis_client.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    healthy = all(value == "ok" for value in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ok" if healthy else "unhealthy", "checks": checks},
    )
