"""Test data builders for the Users bounded context.

Plain builder functions rather than a heavier factory framework for the
domain/application layers — they take explicit keyword overrides so tests
stay readable about exactly what they're asserting on, without hardcoding
unrelated fields (PRD §49). API-payload factories use ``polyfactory`` since
that's plain-dict generation where field independence doesn't matter.
"""

from __future__ import annotations

from polyfactory.factories.pydantic_factory import ModelFactory

from app.domain.users.entities.user import User
from app.domain.users.value_objects.display_name import DisplayName
from app.domain.users.value_objects.email import Email
from app.presentation.api.schemas.users.requests import RegisterUserRequest

_counter = 0


def _next_n() -> int:
    global _counter
    _counter += 1
    return _counter


def make_email(local_part: str | None = None) -> Email:
    return Email(f"{local_part or f'user{_next_n()}'}@example.com")


def make_display_name(value: str | None = None) -> DisplayName:
    return DisplayName(value or f"Test User {_next_n()}")


def make_user(*, email: Email | None = None, display_name: DisplayName | None = None) -> User:
    return User.register(
        email=email or make_email(),
        display_name=display_name or make_display_name(),
    )


class RegisterUserRequestFactory(ModelFactory[RegisterUserRequest]):
    __model__ = RegisterUserRequest

    @classmethod
    def email(cls) -> str:
        return f"user{_next_n()}@example.com"
