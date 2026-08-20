"""Base abstraction for Entities.

An Entity has a persistent identity that survives attribute changes.
Equality and hashing are based purely on identity + type, never on
attribute values.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

IdType = TypeVar("IdType")


class Entity(Generic[IdType]):
    """Base class for domain entities identified by ``IdType``."""

    def __init__(self, entity_id: IdType) -> None:
        self._id = entity_id

    @property
    def id(self) -> IdType:
        return self._id

    def __eq__(self, other: Any) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash((type(self), self._id))

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self._id!r})"
