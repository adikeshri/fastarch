"""Base abstraction for Value Objects.

A Value Object is immutable and compared by the value of its attributes
rather than by identity. Concrete value objects should subclass
``ValueObject`` as a frozen ``@dataclass`` and validate their invariants in
``__post_init__`` by calling ``self._validate()``.
"""

from __future__ import annotations

import dataclasses
from typing import Any


@dataclasses.dataclass(frozen=True)
class ValueObject:
    """Marker base class for immutable, value-equal domain value objects.

    Subclasses must be declared as ``@dataclass(frozen=True)`` so equality,
    hashing, and immutability come from the dataclass machinery itself —
    this base class exists only to give value objects a common type and a
    validation hook.
    """

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        """Override to raise ``InvalidValueObject`` when invariants are violated."""

    def _replace(self, **changes: Any) -> ValueObject:
        """Return a new instance with the given fields replaced (value objects are immutable)."""
        return dataclasses.replace(self, **changes)
