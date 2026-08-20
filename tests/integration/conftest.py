"""Shared testcontainers-backed fixtures for integration tests.

A single Postgres + Redis *container pair* is started once per test session
(``docker compose`` isn't required — this needs only a working Docker
daemon, see ``docs/testing.md``) since spinning up containers is the
expensive part. The async SQLAlchemy engine itself is rebuilt per test
function, because an ``AsyncEngine``/its connections are bound to the event
loop they were created on, and pytest-asyncio gives each test its own loop
by default — sharing one engine across tests invites hard-to-debug
cross-loop errors. Schema is created directly from ``Base.metadata`` for
speed/isolation; migration *history* correctness is verified separately by
the "migrations" CI job against a real Alembic upgrade/downgrade cycle.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from app.infrastructure.persistence.model_registry import Base


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


@pytest_asyncio.fixture
async def engine(postgres_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(postgres_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    await engine.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture
async def redis_client(redis_url: str) -> AsyncIterator[Redis]:
    client: Redis = Redis.from_url(redis_url, decode_responses=True)
    yield client
    await client.flushdb()
    await client.aclose()
