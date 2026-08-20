"""Import every ORM model so ``Base.metadata`` is fully populated.

Alembic's ``env.py`` and test fixtures that call
``Base.metadata.create_all`` import this module (not the individual model
modules) precisely so a newly added bounded context can't be forgotten —
add its model import here once and both migrations and tests pick it up.
"""

from __future__ import annotations

from app.infrastructure.persistence.models.base import Base
from app.infrastructure.persistence.models.user_model import UserModel
from app.infrastructure.persistence.outbox.model import OutboxModel

__all__ = ["Base", "OutboxModel", "UserModel"]
