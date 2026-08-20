"""End-to-end fixtures: a real FastAPI app, over ASGI, backed by real
(testcontainers) Postgres + Redis — the closest thing to hitting the
deployed service without actually deploying it.

Schema setup/teardown uses its own short-lived engine per test (rather than
one shared across the session) because an ``AsyncEngine`` is bound to the
event loop it was created on, and pytest-asyncio gives each test its own
loop by default.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from app.infrastructure.authentication.jwt import JwtTokenService
from app.infrastructure.configuration.settings import Settings
from app.infrastructure.persistence.model_registry import Base
from app.main import create_app


@pytest.fixture(scope="session")
def postgres_url() -> str:
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def redis_url() -> str:
    with RedisContainer("redis:7-alpine") as redis:
        host = redis.get_container_host_ip()
        port = redis.get_exposed_port(6379)
        yield f"redis://{host}:{port}/0"


@pytest.fixture
def settings(postgres_url: str, redis_url: str) -> Settings:
    return Settings(
        database={"url": postgres_url},
        redis={"url": redis_url},
        security={"cors_allow_origins": ["*"], "trusted_hosts": ["*"]},
        observability={"otlp_endpoint": None, "json_logs": False},
    )


@pytest_asyncio.fixture(autouse=True)
async def _schema(settings: Settings) -> AsyncIterator[None]:
    engine = create_async_engine(str(settings.database.url))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    await engine.dispose()


@pytest_asyncio.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as async_client:
            yield async_client


@pytest.fixture
def auth_headers(settings: Settings) -> dict[str, str]:
    """A bearer token granting ``users:write``, for endpoints that require it."""
    token = JwtTokenService(settings.auth).issue_access_token(
        user_id=uuid4(), permissions=frozenset({"users:write"})
    )
    return {"Authorization": f"Bearer {token}"}
