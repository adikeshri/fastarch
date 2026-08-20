from __future__ import annotations

from dataclasses import dataclass

from app.application.common.messages import Command
from app.application.users.dto.user_dto import UserDTO


@dataclass(frozen=True)
class RenameUserCommand(Command[UserDTO]):
    required_permission = "users:write"

    user_id: str
    new_display_name: str

    def validate(self) -> dict[str, list[str]]:
        errors: dict[str, list[str]] = {}
        if not self.new_display_name or not self.new_display_name.strip():
            errors.setdefault("new_display_name", []).append("new_display_name must not be empty")
        return errors
