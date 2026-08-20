from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, Header, Request

from app.application.common.interfaces.identity import AuthContext
from app.application.common.mediator import Mediator
from app.application.common.request_context import RequestContext
from app.composition.container import Container
from app.presentation.api.dependencies.auth import get_current_auth_context
from app.presentation.api.dependencies.container import get_container


def get_mediator(container: Annotated[Container, Depends(get_container)]) -> Mediator:
    return container.mediator


def get_request_context(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_current_auth_context)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> RequestContext:
    correlation_id_raw = getattr(request.state, "correlation_id", None)
    try:
        correlation_id = UUID(correlation_id_raw) if correlation_id_raw else uuid4()
    except ValueError:
        correlation_id = uuid4()
    return RequestContext(correlation_id=correlation_id, auth=auth, idempotency_key=idempotency_key)
