"""SQLAlchemy implementation of the domain's ``UserRepository`` port.

Every pending domain event raised by an aggregate passed to :meth:`add` or
:meth:`save` is appended to the shared ``event_sink`` list injected by the
owning Unit of Work — the repository never talks to the outbox or the
message broker directly, it just hands events upward.
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.shared.domain_event import DomainEvent
from app.domain.users.entities.user import User
from app.domain.users.exceptions import UserConcurrencyConflict
from app.domain.users.repositories.user_repository import UserRepository
from app.domain.users.value_objects.email import Email
from app.domain.users.value_objects.user_id import UserId
from app.infrastructure.persistence.mappers.user_mapper import to_domain, to_model
from app.infrastructure.persistence.models.user_model import UserModel


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession, event_sink: list[DomainEvent]) -> None:
        self._session = session
        self._event_sink = event_sink

    async def get_by_id(self, user_id: UserId) -> User | None:
        model = await self._session.get(UserModel, user_id.value)
        return to_domain(model) if model is not None else None

    async def get_by_email(self, email: Email) -> User | None:
        stmt = select(UserModel).where(UserModel.email == str(email))
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_domain(model) if model is not None else None

    async def list_page(self, *, offset: int, limit: int) -> tuple[list[User], int]:
        items_stmt = (
            select(UserModel)
            .order_by(UserModel.registered_at.desc(), UserModel.id)
            .offset(offset)
            .limit(limit)
        )
        count_stmt = select(func.count()).select_from(UserModel)

        models = (await self._session.execute(items_stmt)).scalars().all()
        total = (await self._session.execute(count_stmt)).scalar_one()

        return [to_domain(model) for model in models], total

    def add(self, user: User) -> None:
        self._session.add(to_model(user))
        self._event_sink.extend(user.collect_events())

    async def save(self, user: User) -> None:
        new_version = user.version + 1
        stmt = (
            update(UserModel)
            .where(UserModel.id == user.id.value, UserModel.version == user.version)
            .values(
                email=str(user.email),
                display_name=str(user.display_name),
                status=user.status.value,
                registered_at=user.registered_at,
                version=new_version,
            )
        )
        result = cast(CursorResult[Any], await self._session.execute(stmt))
        if result.rowcount == 0:
            raise UserConcurrencyConflict("User", user.id, user.version)

        user.mark_persisted(new_version)
        self._event_sink.extend(user.collect_events())
