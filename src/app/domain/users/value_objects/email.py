from __future__ import annotations

import dataclasses
import re

from app.domain.shared.exceptions import InvalidValueObject
from app.domain.shared.value_object import ValueObject

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MAX_LENGTH = 254


@dataclasses.dataclass(frozen=True)
class Email(ValueObject):
    """An RFC-5321-ish-valid, normalized email address."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", self.value.strip().lower())
        self._validate()

    def _validate(self) -> None:
        if not self.value:
            raise InvalidValueObject("Email must not be empty")
        if len(self.value) > _MAX_LENGTH:
            raise InvalidValueObject(f"Email must not exceed {_MAX_LENGTH} characters")
        if not _EMAIL_PATTERN.match(self.value):
            raise InvalidValueObject(f"'{self.value}' is not a valid email address")

    @property
    def domain(self) -> str:
        return self.value.rsplit("@", 1)[-1]

    def __str__(self) -> str:
        return self.value
