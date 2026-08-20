from __future__ import annotations

from app.application.common.interfaces.unit_of_work import UnitOfWorkFactory
from app.application.common.messages import Request, RequestHandler
from app.application.users.commands.register_user import RegisterUserCommand
from app.application.users.dto.user_dto import UserDTO
from app.domain.users.entities.user import User
from app.domain.users.exceptions import EmailAlreadyRegistered
from app.domain.users.services.reserved_name_policy import ReservedDisplayNamePolicy
from app.domain.users.value_objects.display_name import DisplayName
from app.domain.users.value_objects.email import Email


class RegisterUserHandler(RequestHandler[UserDTO]):
    """Handles :class:`RegisterUserCommand`.

    Owns the transaction boundary via the injected :class:`UnitOfWork`
    factory — this is the standard shape every command handler in this
    template follows (see ``docs/application-layer.md``).
    """

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        reserved_name_policy: ReservedDisplayNamePolicy,
    ) -> None:
        self._uow_factory = uow_factory
        self._reserved_name_policy = reserved_name_policy

    async def handle(self, request: Request[UserDTO]) -> UserDTO:
        assert isinstance(request, RegisterUserCommand)
        email = Email(request.email)
        display_name = DisplayName(request.display_name)
        self._reserved_name_policy.ensure_allowed(display_name)

        async with self._uow_factory() as uow:
            existing = await uow.users.get_by_email(email)
            if existing is not None:
                raise EmailAlreadyRegistered(str(email))

            user = User.register(email=email, display_name=display_name)
            uow.users.add(user)
            await uow.commit()

            return UserDTO.from_domain(user)
