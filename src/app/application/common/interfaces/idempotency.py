"""Idempotency port (PRD §43).

Commands that carry a client-supplied idempotency key are checked against
this store by the ``IdempotencyBehavior`` pipeline step
(``app.application.common.behaviors.idempotency``) before the handler runs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any


class IdempotencyStore(ABC):
    @abstractmethod
    async def get_cached_result(self, idempotency_key: str, fingerprint: str) -> Any | None:
        """Return the previously-stored result for this key, if the request fingerprint matches.

        A fingerprint mismatch (same key, different payload) should be
        treated as a distinct error by the caller, not a cache hit.
        """

    @abstractmethod
    async def store_result(
        self,
        idempotency_key: str,
        fingerprint: str,
        result: Any,
        *,
        ttl: timedelta,
    ) -> None: ...

    @abstractmethod
    async def try_acquire_lock(self, idempotency_key: str, *, ttl: timedelta) -> bool:
        """Best-effort lock so concurrent requests with the same key don't both execute.

        Returns False if another in-flight request already holds the lock.
        """

    @abstractmethod
    async def release_lock(self, idempotency_key: str) -> None: ...
