from __future__ import annotations

import pytest

from app.application.users.handlers.get_user_handler import GetUserHandler
from app.application.users.handlers.list_users_handler import ListUsersHandler
from app.application.users.queries.get_user import GetUserQuery
from app.application.users.queries.list_users import ListUsersQuery
from app.domain.users.exceptions import UserNotFound
from tests.factories.user_factory import make_user
from tests.unit.application.users.fakes import FakeUnitOfWork


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


async def test_get_user_returns_the_dto(uow: FakeUnitOfWork) -> None:
    user = make_user()
    uow.users.add(user)
    handler = GetUserHandler(lambda: uow)

    result = await handler.handle(GetUserQuery(user_id=str(user.id)))

    assert result.id == str(user.id)


async def test_get_user_raises_not_found_for_unknown_id(uow: FakeUnitOfWork) -> None:
    handler = GetUserHandler(lambda: uow)

    with pytest.raises(UserNotFound):
        await handler.handle(GetUserQuery(user_id=str(make_user().id)))


async def test_list_users_paginates(uow: FakeUnitOfWork) -> None:
    for _ in range(5):
        uow.users.add(make_user())
    handler = ListUsersHandler(lambda: uow)

    page = await handler.handle(ListUsersQuery(offset=0, limit=2))

    assert len(page.items) == 2
    assert page.total == 5
    assert page.has_next is True
    assert page.has_previous is False
