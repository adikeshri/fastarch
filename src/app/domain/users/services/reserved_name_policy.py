"""Example domain service: business logic that doesn't belong to a single
aggregate instance.

Unlike aggregate methods, a domain service takes its subject as an argument
rather than owning it, and it must not touch infrastructure (no database
calls, no HTTP) — cross-aggregate lookups belong in the application layer,
which fetches the data and passes it in.
"""

from __future__ import annotations

from app.domain.shared.exceptions import BusinessRuleViolation
from app.domain.users.value_objects.display_name import DisplayName

_RESERVED_NAMES = frozenset({"admin", "root", "system", "support", "moderator"})


class ReservedDisplayNamePolicy:
    """Rejects display names that collide with reserved system-level names."""

    def ensure_allowed(self, display_name: DisplayName) -> None:
        if display_name.value.strip().lower() in _RESERVED_NAMES:
            raise BusinessRuleViolation(
                f"'{display_name}' is a reserved name and cannot be used as a display name"
            )
