from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class CommandResult(Generic[T]):
    """Uniform envelope returned by command handlers.

    Kept separate from query DTOs so presentation code can distinguish
    "the result of a write" (often just an id + a few echoed fields) from
    "the result of a read" without guessing from shape alone.
    """

    data: T
