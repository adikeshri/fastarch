"""Command/Query base types and the handler contract they're dispatched to.

Every use case is modeled as a small, immutable ``Command`` (state-changing)
or ``Query`` (read-only) dataclass carrying exactly the input it needs, plus
one dedicated handler. This is the CQRS backbone (PRD §13): read and write
paths never share a handler, so they can evolve independently (different
persistence strategy, different caching, different scaling).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Generic, TypeVar

TResult = TypeVar("TResult")


class Request(ABC, Generic[TResult]):
    """Marker base for anything dispatchable through the ``Mediator``.

    Subclasses may set ``required_permission`` to have the
    ``AuthorizationBehavior`` enforce it automatically, and may override
    :meth:`validate` to have the ``ValidationBehavior`` enforce
    application-level input rules before the handler ever runs.
    """

    required_permission: ClassVar[str | None] = None

    def validate(self) -> dict[str, list[str]]:
        """Return a mapping of field -> error messages. Empty mapping means valid."""
        return {}


class Command(Request[TResult], ABC):
    """A state-changing use case."""


class Query(Request[TResult], ABC):
    """A read-only use case."""


class RequestHandler(ABC, Generic[TResult]):
    """Base class for a handler of exactly one ``Command``/``Query`` type."""

    @abstractmethod
    async def handle(self, request: Request[TResult]) -> TResult: ...
