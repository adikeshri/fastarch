"""The Unit-of-Work port.

The application layer depends only on this abstraction; the concrete
SQLAlchemy implementation lives in
``app.infrastructure.persistence.unit_of_work``. A Unit of Work is the
transaction boundary for exactly one use case: handlers open it with
``async with``, do their work through the repositories it exposes, and
either let it commit (falling out of the block normally) or it rolls back
automatically on exception.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from types import TracebackType
from typing import Self

from app.domain.users.repositories.user_repository import UserRepository


class UnitOfWork(ABC):
    """Coordinates one atomic transaction across one or more repositories."""

    users: UserRepository

    @abstractmethod
    async def __aenter__(self) -> Self: ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    @abstractmethod
    async def commit(self) -> None:
        """Commit the transaction and flush any collected domain events to the outbox."""

    @abstractmethod
    async def rollback(self) -> None:
        """Roll back the transaction, discarding any uncommitted changes."""


UnitOfWorkFactory = Callable[[], UnitOfWork]
"""Handlers depend on a factory rather than a shared instance, so each use
case gets its own transaction scope regardless of how it's invoked."""
