from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.application.common.interfaces.publisher import OutboundMessage, Publisher
from app.infrastructure.configuration.settings import Settings
from app.infrastructure.persistence.outbox.model import OutboxModel, OutboxStatus
from app.infrastructure.persistence.outbox.relay import OutboxRelay
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from tests.factories.user_factory import make_display_name, make_email


class RecordingPublisher(Publisher):
    def __init__(self, *, fail: bool = False) -> None:
        self.published: list[OutboundMessage] = []
        self._fail = fail

    async def publish(self, message: OutboundMessage) -> None:
        if self._fail:
            raise RuntimeError("simulated broker failure")
        self.published.append(message)


@pytest.fixture
async def _pending_outbox_row(session_factory: async_sessionmaker, engine: AsyncEngine) -> None:
    from app.domain.users.entities.user import User

    async with SqlAlchemyUnitOfWork(session_factory, Settings()) as uow:
        user = User.register(email=make_email(), display_name=make_display_name())
        uow.users.add(user)
        await uow.commit()


async def test_relay_once_publishes_pending_rows_and_marks_them_published(
    session_factory: async_sessionmaker, _pending_outbox_row: None
) -> None:
    publisher = RecordingPublisher()
    relay = OutboxRelay(publisher, batch_size=10, max_attempts=10)

    async with session_factory() as session:
        processed = await relay.relay_once(session)

    assert processed == 1
    assert len(publisher.published) == 1
    assert publisher.published[0].event_type == "UserRegistered"

    async with session_factory() as session:
        rows = (await session.execute(select(OutboxModel))).scalars().all()
    assert rows[0].status == OutboxStatus.PUBLISHED.value
    assert rows[0].processed_at is not None


async def test_relay_once_marks_failures_and_schedules_a_retry(
    session_factory: async_sessionmaker, _pending_outbox_row: None
) -> None:
    relay = OutboxRelay(RecordingPublisher(fail=True), batch_size=10, max_attempts=10)

    async with session_factory() as session:
        await relay.relay_once(session)

    async with session_factory() as session:
        rows = (await session.execute(select(OutboxModel))).scalars().all()

    assert rows[0].status == OutboxStatus.FAILED.value
    assert rows[0].attempt_count == 1
    assert rows[0].last_error is not None
    assert rows[0].available_at > rows[0].created_at


async def test_relay_once_ignores_rows_past_max_attempts(
    session_factory: async_sessionmaker, _pending_outbox_row: None
) -> None:
    relay = OutboxRelay(RecordingPublisher(), batch_size=10, max_attempts=0)

    async with session_factory() as session:
        processed = await relay.relay_once(session)

    assert processed == 0
