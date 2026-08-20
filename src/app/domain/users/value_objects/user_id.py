from __future__ import annotations

import dataclasses
import uuid

from app.domain.shared.identifiers import new_id
from app.domain.shared.value_object import ValueObject


@dataclasses.dataclass(frozen=True)
class UserId(ValueObject):
    """Strongly-typed identifier for a :class:`~app.domain.users.entities.user.User`.

    Wrapping the raw ``uuid.UUID`` prevents a ``UserId`` from being confused
    with any other aggregate's identifier at the type-checker level.
    """

    value: uuid.UUID

    @classmethod
    def new(cls) -> UserId:
        return cls(new_id())

    @classmethod
    def from_string(cls, raw: str) -> UserId:
        try:
            return cls(uuid.UUID(raw))
        except ValueError as exc:
            from app.domain.shared.exceptions import InvalidValueObject

            raise InvalidValueObject(f"'{raw}' is not a valid UserId") from exc

    def __str__(self) -> str:
        return str(self.value)
