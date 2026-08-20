"""A minimal ``Result`` type for domain services that need to communicate
expected business failures without raising exceptions for control flow.

Use exceptions (``app.domain.shared.exceptions``) for invariant violations —
programming errors that should never happen if callers respect the domain's
contracts. Use ``Result`` for expected, "may legitimately fail" outcomes a
caller is meant to branch on, e.g. a domain service that checks a business
rule spanning multiple aggregates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Result(Generic[T, E]):
    _value: T | None
    _error: E | None
    is_success: bool

    @classmethod
    def ok(cls, value: T) -> Result[T, E]:
        return cls(_value=value, _error=None, is_success=True)

    @classmethod
    def fail(cls, error: E) -> Result[T, E]:
        return cls(_value=None, _error=error, is_success=False)

    @property
    def is_failure(self) -> bool:
        return not self.is_success

    @property
    def value(self) -> T:
        if not self.is_success:
            raise ValueError("Cannot access .value on a failed Result")
        return self._value  # type: ignore[return-value]

    @property
    def error(self) -> E:
        if self.is_success:
            raise ValueError("Cannot access .error on a successful Result")
        return self._error  # type: ignore[return-value]
