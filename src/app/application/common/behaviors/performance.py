from __future__ import annotations

import time
from typing import TypeVar

import structlog

from app.application.common.behaviors.base import NextStep, PipelineBehavior
from app.application.common.messages import Request
from app.application.common.request_context import RequestContext

TResult = TypeVar("TResult")

logger = structlog.get_logger(__name__)

_SLOW_REQUEST_THRESHOLD_MS = 500


class PerformanceBehavior(PipelineBehavior):
    """Warns when a use case takes longer than a threshold to execute."""

    def __init__(self, *, slow_threshold_ms: int = _SLOW_REQUEST_THRESHOLD_MS) -> None:
        self._slow_threshold_ms = slow_threshold_ms

    async def handle(
        self,
        request: Request[TResult],
        context: RequestContext,
        call_next: NextStep[TResult],
    ) -> TResult:
        start = time.perf_counter()
        try:
            return await call_next(request, context)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            if elapsed_ms > self._slow_threshold_ms:
                logger.warning(
                    "request.slow",
                    request=type(request).__name__,
                    elapsed_ms=round(elapsed_ms, 2),
                    correlation_id=str(context.correlation_id),
                )
