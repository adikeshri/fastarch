"""JWT issuing/verification, isolated from domain and application code.

The presentation layer's ``current_user`` dependency
(``app.presentation.api.dependencies.auth``) is the only caller — nothing
below Presentation ever sees a raw token, only the resulting
:class:`AuthContext`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.application.common.exceptions import AuthenticationException
from app.application.common.interfaces.identity import AuthContext
from app.infrastructure.configuration.settings import AuthSettings


class JwtTokenService:
    def __init__(self, settings: AuthSettings) -> None:
        self._settings = settings

    def issue_access_token(
        self,
        *,
        user_id: UUID,
        roles: frozenset[str] = frozenset(),
        permissions: frozenset[str] = frozenset(),
    ) -> str:
        now = datetime.now(UTC)
        claims = {
            "sub": str(user_id),
            "iss": self._settings.jwt_issuer,
            "aud": self._settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=self._settings.access_token_ttl_minutes),
            "roles": sorted(roles),
            "permissions": sorted(permissions),
        }
        return jwt.encode(
            claims,
            self._settings.jwt_secret.get_secret_value(),
            algorithm=self._settings.jwt_algorithm,
        )

    def verify(self, token: str) -> AuthContext:
        try:
            claims = jwt.decode(
                token,
                self._settings.jwt_secret.get_secret_value(),
                algorithms=[self._settings.jwt_algorithm],
                issuer=self._settings.jwt_issuer,
                audience=self._settings.jwt_audience,
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationException("Invalid or expired access token") from exc

        return AuthContext(
            user_id=UUID(claims["sub"]),
            roles=frozenset(claims.get("roles", [])),
            permissions=frozenset(claims.get("permissions", [])),
            is_authenticated=True,
        )
