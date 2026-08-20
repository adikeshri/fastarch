"""Cache port.

The application layer depends on this abstraction rather than on Redis
directly (PRD §25). See ``app.infrastructure.caching.redis_cache`` for the
Redis implementation and ``docs/infrastructure.md`` for invalidation /
consistency trade-offs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Cache(ABC):
    @abstractmethod
    async def get(self, key: str) -> Any | None: ...

    @abstractmethod
    async def set(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...

    @abstractmethod
    async def invalidate_prefix(self, prefix: str) -> None:
        """Invalidate every key under a namespace prefix (e.g. ``user:123:*``)."""
