from __future__ import annotations

from typing import TypeVar

import structlog

from app.application.common.behaviors.base import NextStep, PipelineBehavior
from app.application.common.messages import Request
from app.application.common.request_context import RequestContext

TResult = TypeVar("TResult")

logger = structlog.get_logger(__name__)


class LoggingBehavior(PipelineBehavior):
    """Logs the start/end (or failure) of every command/query dispatch."""

    async def handle(
        self,
        request: Request[TResult],
        context: RequestContext,
        call_next: NextStep[TResult],
    ) -> TResult:
        request_name = type(request).__name__
        log = logger.bind(
            request=request_name,
            correlation_id=str(context.correlation_id),
            user_id=str(context.auth.user_id) if context.auth.user_id else None,
        )
        log.info("request.started")
        try:
            result = await call_next(request, context)
        except Exception:
            log.exception("request.failed")
            raise
        log.info("request.completed")
        return result
