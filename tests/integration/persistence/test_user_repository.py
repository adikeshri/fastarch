from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.shared.domain_event import DomainEvent
from app.domain.users.exceptions import UserConcurrencyConflict
from app.domain.users.value_objects.display_name import DisplayName
from app.domain.users.value_objects.email import Email
from app.domain.users.value_objects.user_id import UserId
from app.infrastructure.persistence.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from tests.factories.user_factory import make_user


@pytest.fixture
def event_sink() -> list[DomainEvent]:
    return []


async def test_add_then_get_by_id_round_trips(
    session_factory: async_sessionmaker[AsyncSession], event_sink: list[DomainEvent]
) -> None:
    user = make_user()

    async with session_factory() as session:
        repo = SqlAlchemyUserRepository(session, event_sink)
        repo.add(user)
        await session.commit()

    async with session_factory() as session:
        repo = SqlAlchemyUserRepository(session, [])
        loaded = await repo.get_by_id(user.id)

    assert loaded is not None
    assert loaded.email == user.email
    assert loaded.display_name == user.display_name
    assert loaded.version == 0


async def test_add_collects_the_aggregates_domain_events(
    session_factory: async_sessionmaker[AsyncSession], event_sink: list[DomainEvent]
) -> None:
    user = make_user()
    assert len(user.domain_events) == 1

    async with session_factory() as session:
        repo = SqlAlchemyUserRepository(session, event_sink)
        repo.add(user)
        await session.commit()

    assert len(event_sink) == 1
    assert user.domain_events == ()


async def test_get_by_email_finds_a_normalized_match(
    session_factory: async_sessionmaker[AsyncSession], event_sink: list[DomainEvent]
) -> None:
    user = make_user(email=Email("ADA@example.com"))

    async with session_factory() as session:
        SqlAlchemyUserRepository(session, event_sink).add(user)
        await session.commit()

    async with session_factory() as session:
        found = await SqlAlchemyUserRepository(session, []).get_by_email(Email("ada@example.com"))

    assert found is not None
    assert found.id == user.id


async def test_get_by_id_returns_none_for_unknown_id(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        result = await SqlAlchemyUserRepository(session, []).get_by_id(UserId.new())

    assert result is None


async def test_save_persists_changes_and_bumps_version(
    session_factory: async_sessionmaker[AsyncSession], event_sink: list[DomainEvent]
) -> None:
    user = make_user()
    async with session_factory() as session:
        SqlAlchemyUserRepository(session, event_sink).add(user)
        await session.commit()

    user.rename(DisplayName("Renamed"))
    async with session_factory() as session:
        await SqlAlchemyUserRepository(session, []).save(user)
        await session.commit()

    assert user.version == 1

    async with session_factory() as session:
        reloaded = await SqlAlchemyUserRepository(session, []).get_by_id(user.id)
    assert reloaded is not None
    assert str(reloaded.display_name) == "Renamed"
    assert reloaded.version == 1


async def test_save_with_a_stale_version_raises_concurrency_conflict(
    session_factory: async_sessionmaker[AsyncSession], event_sink: list[DomainEvent]
) -> None:
    user = make_user()
    async with session_factory() as session:
        SqlAlchemyUserRepository(session, event_sink).add(user)
        await session.commit()

    # Simulate two concurrent readers of the same version.
    async with session_factory() as session:
        first_reader = await SqlAlchemyUserRepository(session, []).get_by_id(user.id)
    async with session_factory() as session:
        second_reader = await SqlAlchemyUserRepository(session, []).get_by_id(user.id)
    assert first_reader is not None
    assert second_reader is not None

    first_reader.deactivate()
    async with session_factory() as session:
        await SqlAlchemyUserRepository(session, []).save(first_reader)
        await session.commit()

    second_reader.deactivate()
    async with session_factory() as session:
        with pytest.raises(UserConcurrencyConflict):
            await SqlAlchemyUserRepository(session, []).save(second_reader)
            await session.commit()


async def test_list_page_paginates_and_reports_total(
    session_factory: async_sessionmaker[AsyncSession], event_sink: list[DomainEvent]
) -> None:
    async with session_factory() as session:
        repo = SqlAlchemyUserRepository(session, event_sink)
        for _ in range(3):
            repo.add(make_user())
        await session.commit()

    async with session_factory() as session:
        page_1, total = await SqlAlchemyUserRepository(session, []).list_page(offset=0, limit=2)
        page_2, _ = await SqlAlchemyUserRepository(session, []).list_page(offset=2, limit=2)

    assert total == 3
    assert len(page_1) == 2
    assert len(page_2) == 1
