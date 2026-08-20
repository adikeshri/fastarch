from __future__ import annotations

from app.infrastructure.authorization.policies import (
    ROLE_PERMISSIONS,
    can_act_on_own_resource,
    permissions_for_roles,
)

__all__ = ["ROLE_PERMISSIONS", "can_act_on_own_resource", "permissions_for_roles"]
