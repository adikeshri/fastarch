"""Persistence port for the ``User`` aggregate.

Defined in the domain layer because it expresses what the aggregate *needs*
from persistence in domain terms — never SQLAlchemy sessions, ORM models, or
SQL. The concrete implementation lives in
``app.infrastructure.persistence.repositories.sqlalchemy_user_repository``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.users.entities.user import User
from app.domain.users.value_objects.email import Email
from app.domain.users.value_objects.user_id import UserId


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: UserId) -> User | None:
        """Return the user with the given id, or ``None`` if it does not exist."""

    @abstractmethod
    async def get_by_email(self, email: Email) -> User | None:
        """Return the user with the given email, or ``None`` if it does not exist."""

    @abstractmethod
    async def list_page(self, *, offset: int, limit: int) -> tuple[list[User], int]:
        """Return a page of users ordered deterministically, plus the total count."""

    @abstractmethod
    def add(self, user: User) -> None:
        """Register a brand-new aggregate to be inserted on commit."""

    @abstractmethod
    async def save(self, user: User) -> None:
        """Persist changes to an existing aggregate, enforcing optimistic concurrency."""
