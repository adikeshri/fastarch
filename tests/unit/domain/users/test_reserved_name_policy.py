from __future__ import annotations

import pytest

from app.domain.shared.exceptions import BusinessRuleViolation
from app.domain.users.services.reserved_name_policy import ReservedDisplayNamePolicy
from app.domain.users.value_objects.display_name import DisplayName


@pytest.mark.parametrize("reserved", ["admin", "Admin", "ROOT", "system", "support", "moderator"])
def test_rejects_reserved_names(reserved: str) -> None:
    policy = ReservedDisplayNamePolicy()

    with pytest.raises(BusinessRuleViolation):
        policy.ensure_allowed(DisplayName(reserved))


def test_allows_ordinary_names() -> None:
    policy = ReservedDisplayNamePolicy()

    policy.ensure_allowed(DisplayName("Ada Lovelace"))
