from __future__ import annotations

from app.application.common.interfaces.unit_of_work import UnitOfWorkFactory
from app.application.common.messages import Request, RequestHandler
from app.application.users.commands.rename_user import RenameUserCommand
from app.application.users.dto.user_dto import UserDTO
from app.domain.users.exceptions import UserNotFound
from app.domain.users.services.reserved_name_policy import ReservedDisplayNamePolicy
from app.domain.users.value_objects.display_name import DisplayName
from app.domain.users.value_objects.user_id import UserId


class RenameUserHandler(RequestHandler[UserDTO]):
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        reserved_name_policy: ReservedDisplayNamePolicy,
    ) -> None:
        self._uow_factory = uow_factory
        self._reserved_name_policy = reserved_name_policy

    async def handle(self, request: Request[UserDTO]) -> UserDTO:
        assert isinstance(request, RenameUserCommand)
        user_id = UserId.from_string(request.user_id)
        new_display_name = DisplayName(request.new_display_name)
        self._reserved_name_policy.ensure_allowed(new_display_name)

        async with self._uow_factory() as uow:
            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise UserNotFound(user_id)

            user.rename(new_display_name)
            await uow.users.save(user)
            await uow.commit()

            return UserDTO.from_domain(user)
