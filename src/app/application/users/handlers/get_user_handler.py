from __future__ import annotations

from app.application.common.interfaces.unit_of_work import UnitOfWorkFactory
from app.application.common.messages import Request, RequestHandler
from app.application.users.dto.user_dto import UserDTO
from app.application.users.queries.get_user import GetUserQuery
from app.domain.users.exceptions import UserNotFound
from app.domain.users.value_objects.user_id import UserId


class GetUserHandler(RequestHandler[UserDTO]):
    """Query handlers use the same ``UnitOfWork`` port as commands but never call ``commit()``.

    Nothing here prevents swapping this for a dedicated read-optimized data
    access path later (a raw SQL projection, a read replica, a cache-first
    lookup) — that's the point of keeping reads and writes on separate
    handlers (PRD §13).
    """

    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def handle(self, request: Request[UserDTO]) -> UserDTO:
        assert isinstance(request, GetUserQuery)
        user_id = UserId.from_string(request.user_id)

        async with self._uow_factory() as uow:
            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise UserNotFound(user_id)
            return UserDTO.from_domain(user)
