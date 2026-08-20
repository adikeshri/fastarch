"""In-memory fakes for the Users ports, used by handler unit tests.

Real fakes (not mocks) — they implement the actual port contracts,
including optimistic-concurrency and event-collection semantics, so handler
tests exercise real collaboration behavior without touching a database.
"""

from __future__ import annotations

from types import TracebackType
from typing import Self

from app.application.common.interfaces.unit_of_work import UnitOfWork
from app.domain.shared.domain_event import DomainEvent
from app.domain.users.entities.user import User
from app.domain.users.exceptions import UserConcurrencyConflict
from app.domain.users.repositories.user_repository import UserRepository
from app.domain.users.value_objects.email import Email
from app.domain.users.value_objects.user_id import UserId


class FakeUserRepository(UserRepository):
    def __init__(self) -> None:
        self._by_id: dict[UserId, User] = {}
        self.published_events: list[DomainEvent] = []

    async def get_by_id(self, user_id: UserId) -> User | None:
        return self._by_id.get(user_id)

    async def get_by_email(self, email: Email) -> User | None:
        return next((u for u in self._by_id.values() if u.email == email), None)

    async def list_page(self, *, offset: int, limit: int) -> tuple[list[User], int]:
        users = sorted(self._by_id.values(), key=lambda u: u.registered_at, reverse=True)
        return users[offset : offset + limit], len(users)

    def add(self, user: User) -> None:
        self._by_id[user.id] = user
        self.published_events.extend(user.collect_events())

    async def save(self, user: User) -> None:
        existing = self._by_id.get(user.id)
        if existing is None or existing.version != user.version:
            raise UserConcurrencyConflict("User", user.id, user.version)
        user.mark_persisted(user.version + 1)
        self._by_id[user.id] = user
        self.published_events.extend(user.collect_events())


class FakeUnitOfWork(UnitOfWork):
    """A single shared repository across every ``async with`` block, mimicking
    committed state persisting across handler invocations in a test.
    """

    def __init__(self, users: FakeUserRepository | None = None) -> None:
        self.users = users or FakeUserRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True
