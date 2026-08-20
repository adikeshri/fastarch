"""Central place for the identifier generation strategy.

Every aggregate obtains new identity through :func:`new_id` rather than
calling ``uuid4`` directly, so the identifier strategy (UUIDv4 today) can be
swapped project-wide — e.g. for UUIDv7 — without touching domain, application,
or persistence code.
"""

from __future__ import annotations

import uuid


def new_id() -> uuid.UUID:
    """Generate a new globally unique identifier for a new entity/aggregate."""
    return uuid.uuid4()
