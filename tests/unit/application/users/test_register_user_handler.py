from __future__ import annotations

import pytest

from app.application.users.commands.register_user import RegisterUserCommand
from app.application.users.handlers.register_user_handler import RegisterUserHandler
from app.domain.shared.exceptions import BusinessRuleViolation
from app.domain.users.exceptions import EmailAlreadyRegistered
from app.domain.users.services.reserved_name_policy import ReservedDisplayNamePolicy
from tests.unit.application.users.fakes import FakeUnitOfWork


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def handler(uow: FakeUnitOfWork) -> RegisterUserHandler:
    return RegisterUserHandler(lambda: uow, ReservedDisplayNamePolicy())


async def test_registers_a_new_user_and_commits(
    handler: RegisterUserHandler, uow: FakeUnitOfWork
) -> None:
    command = RegisterUserCommand(email="ada@example.com", display_name="Ada Lovelace")

    result = await handler.handle(command)

    assert result.email == "ada@example.com"
    assert result.display_name == "Ada Lovelace"
    assert result.status == "active"
    assert uow.committed is True
    assert len(uow.users.published_events) == 1


async def test_rejects_a_duplicate_email(handler: RegisterUserHandler) -> None:
    command = RegisterUserCommand(email="ada@example.com", display_name="Ada")
    await handler.handle(command)

    with pytest.raises(EmailAlreadyRegistered):
        await handler.handle(RegisterUserCommand(email="ADA@example.com", display_name="Ada 2"))


async def test_rejects_a_reserved_display_name(handler: RegisterUserHandler) -> None:
    command = RegisterUserCommand(email="admin@example.com", display_name="admin")

    with pytest.raises(BusinessRuleViolation):
        await handler.handle(command)
