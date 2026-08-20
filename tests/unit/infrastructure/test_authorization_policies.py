from __future__ import annotations

from uuid import uuid4

from app.application.common.interfaces.identity import AuthContext
from app.infrastructure.authorization.policies import (
    can_act_on_own_resource,
    permissions_for_roles,
)


def test_permissions_for_roles_unions_across_roles() -> None:
    permissions = permissions_for_roles(frozenset({"admin", "user"}))

    assert "users:write" in permissions
    assert "users:read" in permissions


def test_permissions_for_roles_ignores_unknown_roles() -> None:
    assert permissions_for_roles(frozenset({"nonexistent"})) == frozenset()


def test_can_act_on_own_resource_allows_the_owner() -> None:
    user_id = uuid4()
    context = AuthContext(user_id=user_id, is_authenticated=True)

    assert can_act_on_own_resource(context, user_id, or_permission="users:write") is True


def test_can_act_on_own_resource_allows_a_caller_with_the_override_permission() -> None:
    context = AuthContext(
        user_id=uuid4(), is_authenticated=True, permissions=frozenset({"users:write"})
    )

    assert can_act_on_own_resource(context, uuid4(), or_permission="users:write") is True


def test_can_act_on_own_resource_denies_an_unrelated_caller() -> None:
    context = AuthContext(user_id=uuid4(), is_authenticated=True)

    assert can_act_on_own_resource(context, uuid4(), or_permission="users:write") is False
