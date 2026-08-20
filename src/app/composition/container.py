"""The composition root.

This is the *only* place in the whole codebase allowed to import concrete
infrastructure classes and wire them to application interfaces. FastAPI
dependencies (``app.presentation.api.dependencies``) pull already-built
objects from the :class:`Container`; they never construct infrastructure
themselves (PRD §28).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings as ArqRedisSettings
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.application.common.behaviors import (
    AuthorizationBehavior,
    IdempotencyBehavior,
    LoggingBehavior,
    PerformanceBehavior,
    ValidationBehavior,
)
from app.application.common.interfaces.unit_of_work import UnitOfWorkFactory
from app.application.common.mediator import Mediator
from app.application.common.messages import Request
from app.application.users.commands.deactivate_user import DeactivateUserCommand
from app.application.users.commands.register_user import RegisterUserCommand
from app.application.users.commands.rename_user import RenameUserCommand
from app.application.users.handlers import (
    DeactivateUserHandler,
    GetUserHandler,
    ListUsersHandler,
    RegisterUserHandler,
    RenameUserHandler,
)
from app.application.users.queries.get_user import GetUserQuery
from app.application.users.queries.list_users import ListUsersQuery
from app.domain.users.services.reserved_name_policy import ReservedDisplayNamePolicy
from app.infrastructure.authentication.jwt import JwtTokenService
from app.infrastructure.authentication.password_hasher import Argon2PasswordHasher
from app.infrastructure.caching.redis_idempotency_store import RedisIdempotencyStore
from app.infrastructure.configuration.settings import Settings
from app.infrastructure.persistence.database import create_engine, create_session_factory
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


@dataclass
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    redis_client: Redis
    arq_pool: ArqRedis
    mediator: Mediator
    jwt_service: JwtTokenService
    password_hasher: Argon2PasswordHasher

    def uow_factory(self) -> UnitOfWorkFactory:
        def _make() -> SqlAlchemyUnitOfWork:
            return SqlAlchemyUnitOfWork(self.session_factory, self.settings)

        return _make


async def build_container(settings: Settings) -> Container:
    engine = create_engine(settings.database)
    session_factory = create_session_factory(engine)
    redis_client: Redis = Redis.from_url(str(settings.redis.url), decode_responses=True)
    arq_pool = await create_pool(ArqRedisSettings.from_dsn(str(settings.redis.url)))

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, settings)

    reserved_name_policy = ReservedDisplayNamePolicy()

    handlers: dict[type[Request[Any]], object] = {
        RegisterUserCommand: RegisterUserHandler(uow_factory, reserved_name_policy),
        RenameUserCommand: RenameUserHandler(uow_factory, reserved_name_policy),
        DeactivateUserCommand: DeactivateUserHandler(uow_factory),
        GetUserQuery: GetUserHandler(uow_factory),
        ListUsersQuery: ListUsersHandler(uow_factory),
    }

    idempotency_store = RedisIdempotencyStore(redis_client)
    mediator = Mediator(
        handlers,  # type: ignore[arg-type]
        behaviors=[
            LoggingBehavior(),
            PerformanceBehavior(),
            ValidationBehavior(),
            AuthorizationBehavior(),
            IdempotencyBehavior(idempotency_store),
        ],
    )

    return Container(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        redis_client=redis_client,
        arq_pool=arq_pool,
        mediator=mediator,
        jwt_service=JwtTokenService(settings.auth),
        password_hasher=Argon2PasswordHasher(),
    )


async def shutdown_container(container: Container) -> None:
    """Release every resource opened by :func:`build_container` (PRD §64)."""
    await container.arq_pool.aclose()
    await container.redis_client.aclose()
    await container.engine.dispose()


__all__ = ["Container", "build_container", "shutdown_container"]
