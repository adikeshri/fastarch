"""Transport-specific parsing of pagination query params (PRD §41/§42).

Only this module knows about FastAPI ``Query`` — it produces plain
``(offset, limit)`` primitives that flow into an application-layer
``Query`` dataclass, never a FastAPI-specific pagination object.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Query

from app.application.common.dto.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


@dataclass(frozen=True)
class PaginationParams:
    offset: int
    limit: int


def pagination_params(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> PaginationParams:
    return PaginationParams(offset=offset, limit=limit)
