from __future__ import annotations

from dataclasses import dataclass

from app.application.common.messages import Query
from app.application.users.dto.user_dto import UserDTO


@dataclass(frozen=True)
class GetUserQuery(Query[UserDTO]):
    user_id: str
