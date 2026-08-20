"""SQLAlchemy implementation of the :class:`UnitOfWork` port.

On :meth:`commit`, every domain event collected from repositories during
this transaction is written to the outbox *in the same database
transaction* as the aggregate changes, then both are committed together —
this is what makes the outbox pattern transactionally safe (PRD §22): an
event can never exist without its originating change, and vice versa.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.common.interfaces.unit_of_work import UnitOfWork
from app.domain.shared.domain_event import DomainEvent
from app.infrastructure.configuration.settings import Settings
from app.infrastructure.persistence.outbox.model import OutboxModel
from app.infrastructure.persistence.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], settings: Settings
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._session: AsyncSession | None = None
        self._pending_events: list[DomainEvent] = []

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self._pending_events = []
        self.users = SqlAlchemyUserRepository(self._session, self._pending_events)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        assert self._session is not None
        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        assert self._session is not None, "commit() called outside an 'async with' block"
        for event in self._pending_events:
            self._session.add(
                _outbox_row_for(event, max_attempts=self._settings.outbox_max_attempts)
            )
        self._pending_events = []
        await self._session.commit()

    async def rollback(self) -> None:
        assert self._session is not None, "rollback() called outside an 'async with' block"
        self._pending_events = []
        await self._session.rollback()


def _outbox_row_for(event: DomainEvent, *, max_attempts: int) -> OutboxModel:
    payload = {
        key: (str(value) if isinstance(value, uuid.UUID | datetime) else value)
        for key, value in vars(event).items()
        if key not in {"event_id", "occurred_at", "aggregate_id", "event_version"}
    }
    now = datetime.now(UTC)
    module_parts = type(event).__module__.split(".")
    aggregate_type = (
        module_parts[module_parts.index("domain") + 1] if "domain" in module_parts else "unknown"
    )
    return OutboxModel(
        id=event.event_id,
        aggregate_type=aggregate_type,
        aggregate_id=event.aggregate_id,
        event_type=event.event_type,
        payload=payload,
        attempt_count=0,
        max_attempts=max_attempts,
        created_at=now,
        available_at=now,
    )
