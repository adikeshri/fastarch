"""Redis implementation of the :class:`IdempotencyStore` port.

Uses a ``SET NX`` for the short-lived processing lock and a separate key for
the durable cached result, both namespaced under ``idempotency:``.
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from redis.asyncio import Redis

from app.application.common.interfaces.idempotency import IdempotencyStore

_RESULT_PREFIX = "idempotency:result:"
_LOCK_PREFIX = "idempotency:lock:"


class RedisIdempotencyStore(IdempotencyStore):
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def get_cached_result(self, idempotency_key: str, fingerprint: str) -> Any | None:
        raw = await self._client.get(_RESULT_PREFIX + idempotency_key)
        if raw is None:
            return None
        record = json.loads(raw)
        if record["fingerprint"] != fingerprint:
            return None
        return record["result"]

    async def store_result(
        self, idempotency_key: str, fingerprint: str, result: Any, *, ttl: timedelta
    ) -> None:
        record = {"fingerprint": fingerprint, "result": result}
        await self._client.set(
            _RESULT_PREFIX + idempotency_key,
            json.dumps(record, default=str),
            ex=int(ttl.total_seconds()),
        )

    async def try_acquire_lock(self, idempotency_key: str, *, ttl: timedelta) -> bool:
        acquired = await self._client.set(
            _LOCK_PREFIX + idempotency_key, "1", nx=True, ex=int(ttl.total_seconds())
        )
        return bool(acquired)

    async def release_lock(self, idempotency_key: str) -> None:
        await self._client.delete(_LOCK_PREFIX + idempotency_key)
