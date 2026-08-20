"""Reusable pagination conventions for the application layer.

These are plain, framework-free dataclasses. Presentation schemas
(``app.presentation.api.schemas``) wrap them for HTTP; the application and
domain layers never depend on FastAPI/Pydantic pagination helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class PageRequest:
    """Offset-based pagination request, validated/clamped once at construction."""

    offset: int = 0
    limit: int = DEFAULT_PAGE_SIZE

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError("offset must be >= 0")
        if not (1 <= self.limit <= MAX_PAGE_SIZE):
            raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}")


@dataclass(frozen=True)
class Page(Generic[T]):
    """A page of results plus enough metadata to compute total pages / has_next."""

    items: list[T]
    total: int
    offset: int
    limit: int

    @property
    def has_next(self) -> bool:
        return self.offset + len(self.items) < self.total

    @property
    def has_previous(self) -> bool:
        return self.offset > 0
