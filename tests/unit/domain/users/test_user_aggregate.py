from __future__ import annotations

import pytest

from app.domain.users.entities.user import User, UserStatus
from app.domain.users.events.user_events import UserDeactivated, UserRegistered, UserRenamed
from app.domain.users.exceptions import UserAlreadyDeactivated
from tests.factories.user_factory import make_display_name, make_email, make_user


def test_register_creates_active_user_with_registered_event() -> None:
    email = make_email("ada")
    display_name = make_display_name("Ada Lovelace")

    user = User.register(email=email, display_name=display_name)

    assert user.email == email
    assert user.display_name == display_name
    assert user.status is UserStatus.ACTIVE
    assert user.is_active is True
    assert user.version == 0

    events = user.domain_events
    assert len(events) == 1
    assert isinstance(events[0], UserRegistered)
    assert events[0].email == str(email)
    assert events[0].display_name == str(display_name)
    assert events[0].aggregate_id == user.id.value


def test_collect_events_drains_and_clears_the_buffer() -> None:
    user = make_user()

    first_collection = user.collect_events()
    second_collection = user.collect_events()

    assert len(first_collection) == 1
    assert second_collection == []
    assert user.domain_events == ()


def test_rename_raises_user_renamed_event() -> None:
    user = make_user()
    user.collect_events()
    new_name = make_display_name("New Name")

    user.rename(new_name)

    assert user.display_name == new_name
    events = user.domain_events
    assert len(events) == 1
    assert isinstance(events[0], UserRenamed)
    assert events[0].new_display_name == str(new_name)


def test_rename_to_the_same_name_is_a_noop_and_raises_no_event() -> None:
    user = make_user(display_name=make_display_name("Same Name"))
    user.collect_events()

    user.rename(make_display_name("Same Name"))

    assert user.domain_events == ()


def test_deactivate_raises_user_deactivated_event() -> None:
    user = make_user()
    user.collect_events()

    user.deactivate(reason="requested")

    assert user.status is UserStatus.DEACTIVATED
    assert user.is_active is False
    events = user.domain_events
    assert len(events) == 1
    assert isinstance(events[0], UserDeactivated)
    assert events[0].reason == "requested"


def test_deactivate_twice_raises_user_already_deactivated() -> None:
    user = make_user()
    user.deactivate()

    with pytest.raises(UserAlreadyDeactivated):
        user.deactivate()


def test_rename_after_deactivation_raises_user_already_deactivated() -> None:
    user = make_user()
    user.deactivate()

    with pytest.raises(UserAlreadyDeactivated):
        user.rename(make_display_name("New Name"))


def test_mark_persisted_updates_the_in_memory_version() -> None:
    user = make_user()

    user.mark_persisted(5)

    assert user.version == 5
