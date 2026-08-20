"""Pipeline behavior contract.

Modeled after the MediatR pipeline-behavior pattern, translated to Python
idioms (composition of async callables) rather than reproducing its .NET
API surface. Each behavior wraps the *next* step (either another behavior or
the terminal handler call) and decides whether/how to call it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.application.common.messages import Request
from app.application.common.request_context import RequestContext

TResult = TypeVar("TResult")

NextStep = Callable[[Request[TResult], RequestContext], Awaitable[TResult]]


class PipelineBehavior(ABC):
    """A cross-cutting concern applied around every command/query dispatch."""

    @abstractmethod
    async def handle(
        self,
        request: Request[TResult],
        context: RequestContext,
        call_next: NextStep[TResult],
    ) -> TResult: ...
