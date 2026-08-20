from __future__ import annotations

from typing import TypeVar

from app.application.common.behaviors.base import NextStep, PipelineBehavior
from app.application.common.exceptions import ValidationException
from app.application.common.messages import Request
from app.application.common.request_context import RequestContext

TResult = TypeVar("TResult")


class ValidationBehavior(PipelineBehavior):
    """Runs ``request.validate()`` and raises :class:`ValidationException` on errors.

    Application-level validation (shape/range/required-field checks on the
    command/query itself) — distinct from domain invariants, which are
    enforced by value objects and aggregates regardless of this behavior.
    """

    async def handle(
        self,
        request: Request[TResult],
        context: RequestContext,
        call_next: NextStep[TResult],
    ) -> TResult:
        errors = request.validate()
        if errors:
            raise ValidationException(errors)
        return await call_next(request, context)
