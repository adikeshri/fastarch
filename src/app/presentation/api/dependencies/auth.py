from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.common.interfaces.identity import AuthContext
from app.composition.container import Container
from app.presentation.api.dependencies.container import get_container

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    container: Annotated[Container, Depends(get_container)],
) -> AuthContext:
    """Resolve the caller's identity from the bearer token, or an anonymous context if absent.

    Missing/invalid credentials never raise here — a request with no
    identity is simply "anonymous" until a specific use case's
    ``required_permission`` rejects it via ``AuthorizationBehavior``. This
    keeps authentication-required-or-not a per-use-case decision instead of
    a per-route one.
    """
    if credentials is None:
        return AuthContext.anonymous()
    return container.jwt_service.verify(credentials.credentials)
