from __future__ import annotations

from app.domain.shared.exceptions import (
    BusinessRuleViolation,
    ConcurrencyConflict,
    EntityNotFound,
    InvalidState,
)


class UserNotFound(EntityNotFound):
    def __init__(self, user_id: object) -> None:
        super().__init__("User", user_id)


class EmailAlreadyRegistered(BusinessRuleViolation):
    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"Email '{email}' is already registered to another user")


class UserAlreadyDeactivated(InvalidState):
    def __init__(self, user_id: object) -> None:
        super().__init__(f"User {user_id!r} is already deactivated")


class UserConcurrencyConflict(ConcurrencyConflict):
    pass


__all__ = [
    "EmailAlreadyRegistered",
    "UserAlreadyDeactivated",
    "UserConcurrencyConflict",
    "UserNotFound",
]
