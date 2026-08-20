from __future__ import annotations

import dataclasses

from app.domain.shared.exceptions import InvalidValueObject
from app.domain.shared.value_object import ValueObject

_MAX_LENGTH = 120


@dataclasses.dataclass(frozen=True)
class DisplayName(ValueObject):
    """A user's human-readable display name."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", self.value.strip())
        self._validate()

    def _validate(self) -> None:
        if not self.value:
            raise InvalidValueObject("Display name must not be empty")
        if len(self.value) > _MAX_LENGTH:
            raise InvalidValueObject(f"Display name must not exceed {_MAX_LENGTH} characters")

    def __str__(self) -> str:
        return self.value
