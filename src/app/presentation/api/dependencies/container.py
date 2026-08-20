"""Thin FastAPI glue for pulling composition-root objects into route handlers.

This is the *only* place presentation code is allowed to reach into the
:class:`Container` — routes themselves depend on ``get_mediator``/
``get_current_auth_context`` below, never on the container directly.
"""

from __future__ import annotations

from fastapi import Request

from app.composition.container import Container


def get_container(request: Request) -> Container:
    return request.app.state.container  # type: ignore[no-any-return]
