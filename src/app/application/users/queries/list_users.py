from __future__ import annotations

from dataclasses import dataclass

from app.application.common.dto.pagination import DEFAULT_PAGE_SIZE, Page
from app.application.common.messages import Query
from app.application.users.dto.user_dto import UserDTO


@dataclass(frozen=True)
class ListUsersQuery(Query[Page[UserDTO]]):
    offset: int = 0
    limit: int = DEFAULT_PAGE_SIZE

    def validate(self) -> dict[str, list[str]]:
        errors: dict[str, list[str]] = {}
        if self.offset < 0:
            errors.setdefault("offset", []).append("offset must be >= 0")
        if not (1 <= self.limit <= 100):
            errors.setdefault("limit", []).append("limit must be between 1 and 100")
        return errors
