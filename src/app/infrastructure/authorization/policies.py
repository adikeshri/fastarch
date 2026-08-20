"""Role → permission mapping and resource-level authorization helpers.

Simple RBAC: a small, explicit table of role -> granted permissions, plus a
helper for "resource-level" checks (e.g. a user acting on their own
record) that ``required_permission`` alone can't express. Application
handlers call :func:`can_act_on_own_resource` explicitly when a use case
needs it (see ``docs/security.md`` for the full authorization story);
nothing here is invoked automatically like ``AuthorizationBehavior`` is.
"""

from __future__ import annotations

from uuid import UUID

from app.application.common.interfaces.identity import AuthContext

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": frozenset({"users:read", "users:write", "users:deactivate"}),
    "user": frozenset({"users:read"}),
}


def permissions_for_roles(roles: frozenset[str]) -> frozenset[str]:
    permissions: set[str] = set()
    for role in roles:
        permissions |= ROLE_PERMISSIONS.get(role, frozenset())
    return frozenset(permissions)


def can_act_on_own_resource(
    context: AuthContext, resource_owner_id: UUID, *, or_permission: str
) -> bool:
    """True if the caller owns the resource, or holds ``or_permission`` (e.g. an admin override)."""
    if context.user_id == resource_owner_id:
        return True
    return context.has_permission(or_permission)
