from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from app.application.common.dto.pagination import Page

T = TypeVar("T", bound=BaseModel)


class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int
    has_next: bool
    has_previous: bool

    @classmethod
    def from_page(cls, page: Page[Any], item_schema: type[T]) -> PageResponse[T]:
        return cls(
            items=[item_schema.model_validate(item, from_attributes=True) for item in page.items],
            total=page.total,
            offset=page.offset,
            limit=page.limit,
            has_next=page.has_next,
            has_previous=page.has_previous,
        )
