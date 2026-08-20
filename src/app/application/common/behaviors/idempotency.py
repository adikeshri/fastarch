from __future__ import annotations

import dataclasses
import hashlib
import json
from datetime import timedelta
from typing import Any, TypeVar

import structlog

from app.application.common.behaviors.base import NextStep, PipelineBehavior
from app.application.common.exceptions import ConflictException
from app.application.common.interfaces.idempotency import IdempotencyStore
from app.application.common.messages import Command, Request
from app.application.common.request_context import RequestContext

TResult = TypeVar("TResult")

logger = structlog.get_logger(__name__)

_LOCK_TTL = timedelta(seconds=30)
_RESULT_TTL = timedelta(hours=24)


def _fingerprint(request: Request[Any]) -> str:
    """A stable hash of the request's data, used to detect key reuse with a different payload."""
    payload = dataclasses.asdict(request) if dataclasses.is_dataclass(request) else vars(request)
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


class IdempotencyBehavior(PipelineBehavior):
    """Makes command execution idempotent when the caller supplies an idempotency key.

    Only applies to :class:`Command`\\ s carrying a non-``None``
    ``context.idempotency_key`` (set by the presentation layer from the
    ``Idempotency-Key`` HTTP header) — queries are naturally safe to repeat
    and are never intercepted here.

    Caveat: the concrete :class:`IdempotencyStore` implementations
    JSON-serialize the handler's result. Command DTOs used here should stay
    JSON-plain (str/int/float/bool/dict/list) — if a handler returns a
    richer dataclass, convert it with ``dataclasses.asdict`` before
    returning, or give the store a typed codec for that command.
    """

    def __init__(self, store: IdempotencyStore) -> None:
        self._store = store

    async def handle(
        self,
        request: Request[TResult],
        context: RequestContext,
        call_next: NextStep[TResult],
    ) -> TResult:
        if context.idempotency_key is None or not isinstance(request, Command):
            return await call_next(request, context)

        key = context.idempotency_key
        fingerprint = _fingerprint(request)

        cached = await self._store.get_cached_result(key, fingerprint)
        if cached is not None:
            logger.info("idempotency.replay", idempotency_key=key)
            return cached  # type: ignore[no-any-return]

        if not await self._store.try_acquire_lock(key, ttl=_LOCK_TTL):
            raise ConflictException(
                "A request with this idempotency key is already being processed"
            )

        try:
            result = await call_next(request, context)
            await self._store.store_result(key, fingerprint, result, ttl=_RESULT_TTL)
            return result
        finally:
            await self._store.release_lock(key)
