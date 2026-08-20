from __future__ import annotations

from dataclasses import dataclass

from app.application.common.messages import Command
from app.application.users.dto.user_dto import UserDTO


@dataclass(frozen=True)
class RegisterUserCommand(Command[UserDTO]):
    email: str
    display_name: str

    def validate(self) -> dict[str, list[str]]:
        errors: dict[str, list[str]] = {}
        if not self.email or "@" not in self.email:
            errors.setdefault("email", []).append("email must be a non-empty address")
        if not self.display_name or not self.display_name.strip():
            errors.setdefault("display_name", []).append("display_name must not be empty")
        return errors
