"""Composes registered handlers with the pipeline behaviors and dispatches requests.

Built once in the composition root (``app.composition.container``) with the
full handler map and the ordered behavior chain, then handed to the
presentation layer as a single dependency — routes never import individual
handlers directly (PRD §13/§15).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from app.application.common.behaviors.base import PipelineBehavior
from app.application.common.messages import Request, RequestHandler
from app.application.common.request_context import RequestContext

TResult = TypeVar("TResult")


class HandlerNotRegistered(RuntimeError):
    def __init__(self, request_type: type) -> None:
        super().__init__(f"No handler registered for {request_type.__name__}")


class Mediator:
    def __init__(
        self,
        handlers: dict[type[Request[Any]], RequestHandler[Any]],
        behaviors: list[PipelineBehavior] | None = None,
    ) -> None:
        self._handlers = handlers
        self._behaviors = behaviors or []

    async def send(self, request: Request[TResult], context: RequestContext) -> TResult:
        handler = self._handlers.get(type(request))
        if handler is None:
            raise HandlerNotRegistered(type(request))

        async def terminal(req: Request[TResult], _ctx: RequestContext) -> TResult:
            return await handler.handle(req)  # type: ignore[no-any-return]

        pipeline: Callable[[Request[TResult], RequestContext], Awaitable[TResult]] = terminal
        for behavior in reversed(self._behaviors):
            pipeline = _bind(behavior, pipeline)

        return await pipeline(request, context)


def _bind(
    behavior: PipelineBehavior,
    call_next: Callable[[Request[TResult], RequestContext], Awaitable[TResult]],
) -> Callable[[Request[TResult], RequestContext], Awaitable[TResult]]:
    async def step(request: Request[TResult], context: RequestContext) -> TResult:
        return await behavior.handle(request, context, call_next)

    return step
