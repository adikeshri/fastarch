"""Base abstraction for Aggregate Roots.

An Aggregate Root is the single entry point through which a consistency
boundary (aggregate) is mutated. It owns:

- identity (inherited from :class:`Entity`)
- an optimistic-concurrency ``version`` counter
- a buffer of domain events raised by its own behavior, which is drained by
  the Unit of Work when the aggregate is persisted (see
  ``app.infrastructure.persistence.unit_of_work``) and turned into outbox
  records — the aggregate itself never knows events are eventually
  published anywhere.
"""

from __future__ import annotations

from app.domain.shared.domain_event import DomainEvent
from app.domain.shared.entity import Entity, IdType


class AggregateRoot(Entity[IdType]):
    """Base class for aggregate roots identified by ``IdType``."""

    def __init__(self, entity_id: IdType, *, version: int = 0) -> None:
        super().__init__(entity_id)
        self._version = version
        self._domain_events: list[DomainEvent] = []

    @property
    def version(self) -> int:
        """Optimistic-concurrency version, as of the last load/save."""
        return self._version

    def mark_persisted(self, version: int) -> None:
        """Sync the in-memory version counter after a successful save.

        Called only by the persistence layer (see
        ``app.infrastructure.persistence.repositories``) once the
        version-checked write has actually committed — never by domain or
        application code.
        """
        self._version = version

    @property
    def domain_events(self) -> tuple[DomainEvent, ...]:
        """Events raised so far and not yet collected."""
        return tuple(self._domain_events)

    def register_event(self, event: DomainEvent) -> None:
        """Record a domain event raised by this aggregate's behavior."""
        self._domain_events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        """Drain and return all pending domain events (called by the repository/UoW on save)."""
        events, self._domain_events = self._domain_events, []
        return events

    def clear_events(self) -> None:
        """Discard pending events without returning them (e.g. after a failed transaction)."""
        self._domain_events = []
