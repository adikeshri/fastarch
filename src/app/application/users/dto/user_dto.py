from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.users.entities.user import User


@dataclass(frozen=True)
class UserDTO:
    """Application-layer representation of a user.

    Deliberately distinct from the domain ``User`` aggregate (no behavior,
    no value objects — just primitives) and from any Pydantic/HTTP schema:
    the presentation layer maps this DTO into its own response schema, it
    never serializes it directly.
    """

    id: str
    email: str
    display_name: str
    status: str
    registered_at: datetime
    version: int

    @classmethod
    def from_domain(cls, user: User) -> UserDTO:
        return cls(
            id=str(user.id),
            email=str(user.email),
            display_name=str(user.display_name),
            status=user.status.value,
            registered_at=user.registered_at,
            version=user.version,
        )
