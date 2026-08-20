"""Authentication/authorization context passed into every command/query.

``AuthContext`` is constructed once per request by the presentation layer
(from the verified JWT — see ``app.infrastructure.authentication.jwt``) and
threaded through to handlers via the pipeline's ``AuthorizationBehavior``.
Nothing below the presentation layer ever touches a raw token.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class AuthContext:
    """Identity + permissions of the caller executing the current use case."""

    user_id: UUID | None
    roles: frozenset[str] = field(default_factory=frozenset)
    permissions: frozenset[str] = field(default_factory=frozenset)
    is_authenticated: bool = False

    @classmethod
    def anonymous(cls) -> AuthContext:
        return cls(user_id=None, is_authenticated=False)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        return role in self.roles
