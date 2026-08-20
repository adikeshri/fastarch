"""arq worker entrypoint: ``arq app.infrastructure.background_jobs.worker.WorkerSettings``.

Registers every background job function and the periodic outbox-relay
cron job. Job functions are plain async callables — they build whatever
infrastructure they need from ``ctx`` (populated in :func:`on_startup`)
rather than going through the FastAPI composition root, since the worker
process is independent of the web process (PRD §64/§74: the API stays
stateless and horizontally scalable; workers scale separately).
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any, ClassVar

from arq import cron
from arq.connections import RedisSettings as ArqRedisSettings
from arq.cron import CronJob

from app.application.users.handlers.user_registered_integration_handler import (
    UserRegisteredIntegrationHandler,
)
from app.domain.users.events.user_events import UserRegistered
from app.infrastructure.configuration.settings import get_settings
from app.infrastructure.external.email.console_email_sender import ConsoleEmailSender
from app.infrastructure.messaging.redis_streams import RedisStreamsConsumer, RedisStreamsPublisher
from app.infrastructure.persistence.database import create_engine, create_session_factory
from app.infrastructure.persistence.outbox.relay import OutboxRelay


async def relay_outbox(ctx: dict[str, Any]) -> int:
    session_factory = ctx["session_factory"]
    relay: OutboxRelay = ctx["outbox_relay"]
    async with session_factory() as session:
        return await relay.relay_once(session)


async def on_startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    engine = create_engine(settings.database)
    ctx["engine"] = engine
    ctx["session_factory"] = create_session_factory(engine)

    from redis.asyncio import Redis as AsyncRedis

    redis_client = AsyncRedis.from_url(str(settings.redis.url))
    ctx["redis_client"] = redis_client
    ctx["outbox_relay"] = OutboxRelay(
        publisher=RedisStreamsPublisher(redis_client),
        batch_size=settings.outbox_relay_batch_size,
        max_attempts=settings.outbox_max_attempts,
    )

    consumer = RedisStreamsConsumer(redis_client, group="users-worker", consumer_name="worker-1")
    consumer.register(
        UserRegistered.__name__, UserRegisteredIntegrationHandler(ConsoleEmailSender())
    )
    await consumer.start()
    ctx["consumer"] = consumer


async def on_shutdown(ctx: dict[str, Any]) -> None:
    await ctx["consumer"].stop()
    await ctx["engine"].dispose()
    await ctx["redis_client"].aclose()


class WorkerSettings:
    functions: ClassVar[list[Callable[..., Coroutine[Any, Any, Any]]]] = [relay_outbox]
    cron_jobs: ClassVar[list[CronJob]] = [cron(relay_outbox, second=set(range(0, 60, 2)))]
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = ArqRedisSettings.from_dsn(str(get_settings().redis.url))
