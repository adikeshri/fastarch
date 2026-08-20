from __future__ import annotations

from dataclasses import dataclass

from app.application.common.messages import Command
from app.application.users.dto.user_dto import UserDTO


@dataclass(frozen=True)
class DeactivateUserCommand(Command[UserDTO]):
    required_permission = "users:write"

    user_id: str
    reason: str | None = None
