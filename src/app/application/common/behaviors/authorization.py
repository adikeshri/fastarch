from __future__ import annotations

from typing import TypeVar

from app.application.common.behaviors.base import NextStep, PipelineBehavior
from app.application.common.exceptions import AuthenticationException, AuthorizationException
from app.application.common.messages import Request
from app.application.common.request_context import RequestContext

TResult = TypeVar("TResult")


class AuthorizationBehavior(PipelineBehavior):
    """Enforces ``request.required_permission`` against the caller's ``AuthContext``.

    Requests that leave ``required_permission`` as ``None`` (the default)
    are treated as public and skip this check entirely — authorization
    policy is declared on the use case itself, not scattered across FastAPI
    route decorators.
    """

    async def handle(
        self,
        request: Request[TResult],
        context: RequestContext,
        call_next: NextStep[TResult],
    ) -> TResult:
        required_permission = request.required_permission
        if required_permission is not None:
            if not context.auth.is_authenticated:
                raise AuthenticationException("Authentication is required for this operation")
            if not context.auth.has_permission(required_permission):
                raise AuthorizationException(
                    f"Missing required permission: '{required_permission}'"
                )
        return await call_next(request, context)
