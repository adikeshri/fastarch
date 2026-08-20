"""Redis Streams implementation of the ``Publisher``/``Consumer`` ports.

Each ``OutboundMessage.topic`` maps to a Redis stream (``stream:<topic>``).
Consumers use a consumer group so multiple worker instances can share the
load; messages that fail repeatedly are moved to a ``<stream>:dead-letter``
stream instead of being retried forever. Swap this module out for a Kafka or
RabbitMQ adapter behind the same ports (``app.application.common.interfaces.publisher``)
without touching application code — see ``docs/messaging.md``.
"""

from __future__ import annotations

import asyncio
import json

import structlog
from redis.asyncio import Redis

from app.application.common.interfaces.publisher import (
    Consumer,
    MessageHandler,
    OutboundMessage,
    Publisher,
)

logger = structlog.get_logger(__name__)

_MAX_DELIVERIES = 5


class RedisStreamsPublisher(Publisher):
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def publish(self, message: OutboundMessage) -> None:
        stream = f"stream:{message.topic}"
        fields: dict[str, str] = {
            "key": message.key,
            "event_type": message.event_type,
            "payload": json.dumps(message.payload),
            **message.headers,
        }
        await self._client.xadd(stream, fields)  # type: ignore[arg-type]


class RedisStreamsConsumer(Consumer):
    def __init__(self, client: Redis, *, group: str, consumer_name: str) -> None:
        self._client = client
        self._group = group
        self._consumer_name = consumer_name
        self._handlers: dict[str, MessageHandler] = {}
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()

    def register(self, event_type: str, handler: MessageHandler) -> None:
        self._handlers[event_type] = handler

    async def start(self) -> None:
        streams = {f"stream:{topic}" for topic in self._topics_for_registered_handlers()}
        for stream in streams:
            await self._ensure_group(stream)
        self._stopping.clear()
        self._task = asyncio.create_task(self._run(streams))

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            await self._task

    def _topics_for_registered_handlers(self) -> set[str]:
        # In this template, topic == aggregate_type == outbox row's aggregate_type,
        # which handlers register against implicitly via their event_type prefix.
        return {"users"}

    async def _ensure_group(self, stream: str) -> None:
        try:
            await self._client.xgroup_create(stream, self._group, id="0", mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def _run(self, streams: set[str]) -> None:
        stream_ids = dict.fromkeys(streams, ">")
        while not self._stopping.is_set():
            response = await self._client.xreadgroup(
                self._group,
                self._consumer_name,
                stream_ids,  # type: ignore[arg-type]
                count=10,
                block=1000,
            )
            for stream, entries in response or []:
                for entry_id, fields in entries:
                    await self._handle_entry(stream, entry_id, fields)

    async def _handle_entry(self, stream: str, entry_id: str, fields: dict[str, str]) -> None:
        event_type = fields.get("event_type", "")
        handler = self._handlers.get(event_type)
        if handler is None:
            await self._client.xack(stream, self._group, entry_id)
            return

        message = OutboundMessage(
            topic=stream.removeprefix("stream:"),
            key=fields.get("key", ""),
            event_type=event_type,
            payload=json.loads(fields.get("payload", "{}")),
            headers={k: v for k, v in fields.items() if k not in {"key", "event_type", "payload"}},
        )
        try:
            await handler.handle(message)
        except Exception:
            logger.exception("consumer.handler_failed", event_type=event_type, entry_id=entry_id)
            pending = await self._client.xpending_range(
                stream, self._group, min="-", max="+", count=1, consumername=self._consumer_name
            )
            deliveries = pending[0]["times_delivered"] if pending else 1
            if deliveries >= _MAX_DELIVERIES:
                await self._client.xadd(f"{stream}:dead-letter", fields)  # type: ignore[arg-type]
                await self._client.xack(stream, self._group, entry_id)
        else:
            await self._client.xack(stream, self._group, entry_id)
