from __future__ import annotations

import uuid

import pytest

from app.domain.shared.exceptions import InvalidValueObject
from app.domain.users.value_objects.display_name import DisplayName
from app.domain.users.value_objects.email import Email
from app.domain.users.value_objects.user_id import UserId


class TestEmail:
    def test_normalizes_case_and_whitespace(self) -> None:
        assert Email("  ADA@Example.COM  ").value == "ada@example.com"

    def test_equality_is_by_value(self) -> None:
        assert Email("a@example.com") == Email("a@example.com")

    def test_domain_property(self) -> None:
        assert Email("a@example.com").domain == "example.com"

    @pytest.mark.parametrize("invalid", ["", "not-an-email", "a@", "@b.com", "a@b"])
    def test_rejects_invalid_addresses(self, invalid: str) -> None:
        with pytest.raises(InvalidValueObject):
            Email(invalid)

    def test_rejects_addresses_over_the_length_limit(self) -> None:
        too_long = "a" * 250 + "@b.com"
        with pytest.raises(InvalidValueObject):
            Email(too_long)


class TestDisplayName:
    def test_strips_whitespace(self) -> None:
        assert DisplayName("  Ada  ").value == "Ada"

    def test_rejects_empty(self) -> None:
        with pytest.raises(InvalidValueObject):
            DisplayName("   ")

    def test_rejects_names_over_the_length_limit(self) -> None:
        with pytest.raises(InvalidValueObject):
            DisplayName("x" * 121)


class TestUserId:
    def test_new_generates_a_unique_id(self) -> None:
        assert UserId.new() != UserId.new()

    def test_from_string_round_trips(self) -> None:
        raw = str(uuid.uuid4())
        assert str(UserId.from_string(raw)) == raw

    def test_from_string_rejects_invalid_uuid(self) -> None:
        with pytest.raises(InvalidValueObject):
            UserId.from_string("not-a-uuid")
