from __future__ import annotations

from app.application.common.interfaces.unit_of_work import UnitOfWorkFactory
from app.application.common.messages import Request, RequestHandler
from app.application.users.commands.deactivate_user import DeactivateUserCommand
from app.application.users.dto.user_dto import UserDTO
from app.domain.users.exceptions import UserNotFound
from app.domain.users.value_objects.user_id import UserId


class DeactivateUserHandler(RequestHandler[UserDTO]):
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def handle(self, request: Request[UserDTO]) -> UserDTO:
        assert isinstance(request, DeactivateUserCommand)
        user_id = UserId.from_string(request.user_id)

        async with self._uow_factory() as uow:
            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise UserNotFound(user_id)

            user.deactivate(reason=request.reason)
            await uow.users.save(user)
            await uow.commit()

            return UserDTO.from_domain(user)
