from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.infrastructure.configuration.settings import Settings
from app.infrastructure.persistence.outbox.model import OutboxModel, OutboxStatus
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from tests.factories.user_factory import make_display_name, make_email


async def test_commit_persists_the_user_and_an_outbox_row_atomically(
    session_factory: async_sessionmaker, engine: AsyncEngine
) -> None:
    uow = SqlAlchemyUnitOfWork(session_factory, Settings())

    async with uow:
        from app.domain.users.entities.user import User

        user = User.register(email=make_email(), display_name=make_display_name())
        uow.users.add(user)
        await uow.commit()

    async with session_factory() as session:
        outbox_rows = (
            (
                await session.execute(
                    select(OutboxModel).where(OutboxModel.aggregate_id == user.id.value)
                )
            )
            .scalars()
            .all()
        )

    assert len(outbox_rows) == 1
    row = outbox_rows[0]
    assert row.event_type == "UserRegistered"
    assert row.status == OutboxStatus.PENDING.value
    assert row.payload["email"] == str(user.email)
    assert row.aggregate_type == "users"


async def test_rollback_on_exception_persists_nothing(
    session_factory: async_sessionmaker, engine: AsyncEngine
) -> None:
    from app.domain.users.entities.user import User

    user = User.register(email=make_email(), display_name=make_display_name())

    try:
        async with SqlAlchemyUnitOfWork(session_factory, Settings()) as uow:
            uow.users.add(user)
            raise RuntimeError("simulated failure before commit")
    except RuntimeError:
        pass

    async with session_factory() as session:
        outbox_rows = (
            (
                await session.execute(
                    select(OutboxModel).where(OutboxModel.aggregate_id == user.id.value)
                )
            )
            .scalars()
            .all()
        )
    assert outbox_rows == []
