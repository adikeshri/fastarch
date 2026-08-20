from __future__ import annotations

import pytest

from app.application.users.commands.deactivate_user import DeactivateUserCommand
from app.application.users.commands.rename_user import RenameUserCommand
from app.application.users.handlers.deactivate_user_handler import DeactivateUserHandler
from app.application.users.handlers.rename_user_handler import RenameUserHandler
from app.domain.users.exceptions import UserAlreadyDeactivated, UserNotFound
from app.domain.users.services.reserved_name_policy import ReservedDisplayNamePolicy
from tests.factories.user_factory import make_user
from tests.unit.application.users.fakes import FakeUnitOfWork


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


async def test_rename_updates_display_name_and_bumps_version(uow: FakeUnitOfWork) -> None:
    user = make_user()
    uow.users.add(user)
    handler = RenameUserHandler(lambda: uow, ReservedDisplayNamePolicy())

    result = await handler.handle(RenameUserCommand(user_id=str(user.id), new_display_name="New"))

    assert result.display_name == "New"
    assert result.version == 1
    assert uow.committed is True


async def test_rename_unknown_user_raises_not_found(uow: FakeUnitOfWork) -> None:
    handler = RenameUserHandler(lambda: uow, ReservedDisplayNamePolicy())

    with pytest.raises(UserNotFound):
        await handler.handle(RenameUserCommand(user_id=str(make_user().id), new_display_name="X"))


async def test_deactivate_marks_user_inactive(uow: FakeUnitOfWork) -> None:
    user = make_user()
    uow.users.add(user)
    handler = DeactivateUserHandler(lambda: uow)

    result = await handler.handle(DeactivateUserCommand(user_id=str(user.id), reason="bye"))

    assert result.status == "deactivated"


async def test_deactivate_twice_raises_already_deactivated(uow: FakeUnitOfWork) -> None:
    user = make_user()
    uow.users.add(user)
    handler = DeactivateUserHandler(lambda: uow)
    await handler.handle(DeactivateUserCommand(user_id=str(user.id)))

    with pytest.raises(UserAlreadyDeactivated):
        await handler.handle(DeactivateUserCommand(user_id=str(user.id)))
