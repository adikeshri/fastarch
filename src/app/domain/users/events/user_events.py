from __future__ import annotations

import dataclasses

from app.domain.shared.domain_event import DomainEvent


@dataclasses.dataclass(frozen=True, kw_only=True)
class UserRegistered(DomainEvent):
    email: str
    display_name: str


@dataclasses.dataclass(frozen=True, kw_only=True)
class UserRenamed(DomainEvent):
    old_display_name: str
    new_display_name: str


@dataclasses.dataclass(frozen=True, kw_only=True)
class UserDeactivated(DomainEvent):
    reason: str | None = None
