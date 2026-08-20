"""The ``User`` aggregate root.

This is the only place business rules about a user's lifecycle live. The
application layer orchestrates *when* these methods are called (inside a
transaction, after authorization); it never re-implements the rules
themselves.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.users.events.user_events import UserDeactivated, UserRegistered, UserRenamed
from app.domain.users.exceptions import UserAlreadyDeactivated
from app.domain.users.value_objects.display_name import DisplayName
from app.domain.users.value_objects.email import Email
from app.domain.users.value_objects.user_id import UserId


class UserStatus(StrEnum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"


class User(AggregateRoot[UserId]):
    """A registered user of the system."""

    def __init__(
        self,
        *,
        user_id: UserId,
        email: Email,
        display_name: DisplayName,
        status: UserStatus,
        registered_at: datetime,
        version: int = 0,
    ) -> None:
        super().__init__(user_id, version=version)
        self._email = email
        self._display_name = display_name
        self._status = status
        self._registered_at = registered_at

    # -- factory -----------------------------------------------------------

    @classmethod
    def register(cls, *, email: Email, display_name: DisplayName) -> User:
        """Create a brand-new user and raise :class:`UserRegistered`.

        Uniqueness of ``email`` is a cross-aggregate invariant and is
        enforced by the application layer via the repository
        (``UserRepository.get_by_email``), not here — a single aggregate
        cannot know about other aggregates' state.
        """
        user_id = UserId.new()
        user = cls(
            user_id=user_id,
            email=email,
            display_name=display_name,
            status=UserStatus.ACTIVE,
            registered_at=datetime.now(UTC),
        )
        user.register_event(
            UserRegistered(
                aggregate_id=user_id.value,
                email=str(email),
                display_name=str(display_name),
            )
        )
        return user

    # -- behavior ------------------------------------------------------

    def rename(self, new_display_name: DisplayName) -> None:
        self._ensure_active()
        if new_display_name == self._display_name:
            return
        old_name = self._display_name
        self._display_name = new_display_name
        self.register_event(
            UserRenamed(
                aggregate_id=self.id.value,
                old_display_name=str(old_name),
                new_display_name=str(new_display_name),
            )
        )

    def deactivate(self, *, reason: str | None = None) -> None:
        self._ensure_active()
        self._status = UserStatus.DEACTIVATED
        self.register_event(UserDeactivated(aggregate_id=self.id.value, reason=reason))

    def _ensure_active(self) -> None:
        if self._status is not UserStatus.ACTIVE:
            raise UserAlreadyDeactivated(self.id)

    # -- read-only projections ------------------------------------------

    @property
    def email(self) -> Email:
        return self._email

    @property
    def display_name(self) -> DisplayName:
        return self._display_name

    @property
    def status(self) -> UserStatus:
        return self._status

    @property
    def is_active(self) -> bool:
        return self._status is UserStatus.ACTIVE

    @property
    def registered_at(self) -> datetime:
        return self._registered_at
