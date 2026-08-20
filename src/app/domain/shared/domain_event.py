"""Base abstraction for Domain Events.

Domain events are immutable facts about something that happened to an
aggregate. Aggregates register events on themselves (see
``AggregateRoot.register_event``) without any knowledge of how those events
will eventually be dispatched — that is an infrastructure concern (the
outbox, see ``app.infrastructure.persistence.outbox``).
"""

from __future__ import annotations

import dataclasses
import uuid
from datetime import UTC, datetime

from app.domain.shared.identifiers import new_id


@dataclasses.dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base class for all domain events.

    Attributes:
        event_id: Unique identifier of this event occurrence.
        occurred_at: UTC timestamp of when the event was registered.
        aggregate_id: Identity of the aggregate that raised the event.
        event_version: Schema version of this event type, for consumers that
            need to evolve payloads over time without breaking old handlers.
    """

    aggregate_id: uuid.UUID
    event_id: uuid.UUID = dataclasses.field(default_factory=new_id)
    occurred_at: datetime = dataclasses.field(default_factory=lambda: datetime.now(UTC))
    event_version: int = 1

    @property
    def event_type(self) -> str:
        """Stable, dotted type name used as the outbox/message envelope ``type``."""
        return type(self).__name__
