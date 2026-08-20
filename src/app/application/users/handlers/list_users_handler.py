from __future__ import annotations

from app.application.common.dto.pagination import Page
from app.application.common.interfaces.unit_of_work import UnitOfWorkFactory
from app.application.common.messages import Request, RequestHandler
from app.application.users.dto.user_dto import UserDTO
from app.application.users.queries.list_users import ListUsersQuery


class ListUsersHandler(RequestHandler[Page[UserDTO]]):
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def handle(self, request: Request[Page[UserDTO]]) -> Page[UserDTO]:
        assert isinstance(request, ListUsersQuery)

        async with self._uow_factory() as uow:
            users, total = await uow.users.list_page(offset=request.offset, limit=request.limit)
            return Page(
                items=[UserDTO.from_domain(user) for user in users],
                total=total,
                offset=request.offset,
                limit=request.limit,
            )
