from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.application.common.interfaces.identity import AuthContext


@dataclass(frozen=True)
class RequestContext:
    """Ambient, per-request metadata threaded through the pipeline behaviors.

    Built once by the presentation layer per HTTP request (see
    ``app.presentation.api.dependencies.mediator``) from the correlation-id
    middleware and the verified auth token.
    """

    correlation_id: UUID = field(default_factory=uuid4)
    auth: AuthContext = field(default_factory=AuthContext.anonymous)
    idempotency_key: str | None = None
