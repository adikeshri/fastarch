"""Explicit, bidirectional mapping between the ``User`` aggregate and ``UserModel``.

Kept as free functions (not methods on either class) so neither the domain
aggregate nor the ORM model needs to know the other exists — this module is
the only place that does.
"""

from __future__ import annotations

from app.domain.users.entities.user import User, UserStatus
from app.domain.users.value_objects.display_name import DisplayName
from app.domain.users.value_objects.email import Email
from app.domain.users.value_objects.user_id import UserId
from app.infrastructure.persistence.models.user_model import UserModel


def to_domain(model: UserModel) -> User:
    return User(
        user_id=UserId(model.id),
        email=Email(model.email),
        display_name=DisplayName(model.display_name),
        status=UserStatus(model.status),
        registered_at=model.registered_at,
        version=model.version,
    )


def to_model(user: User) -> UserModel:
    return UserModel(
        id=user.id.value,
        email=str(user.email),
        display_name=str(user.display_name),
        status=user.status.value,
        registered_at=user.registered_at,
        version=user.version,
    )
