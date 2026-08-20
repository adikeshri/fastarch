"""Domain-level exceptions.

These are the only exception types the domain layer may raise. They carry no
knowledge of HTTP, FastAPI, or any transport concern — mapping them to HTTP
responses is a Presentation-layer responsibility
(see ``app.presentation.api.exception_handlers``).
"""

from __future__ import annotations


class DomainException(Exception):
    """Base type for every exception raised from within the domain layer."""


class InvalidValueObject(DomainException):
    """A value object failed to satisfy its own invariants."""


class InvalidState(DomainException):
    """An entity/aggregate was asked to perform an operation invalid for its current state."""


class BusinessRuleViolation(DomainException):
    """A named business rule was violated."""


class EntityNotFound(DomainException):
    """A referenced entity/aggregate does not exist."""

    def __init__(self, entity_name: str, entity_id: object) -> None:
        self.entity_name = entity_name
        self.entity_id = entity_id
        super().__init__(f"{entity_name} with id={entity_id!r} was not found")


class ConcurrencyConflict(DomainException):
    """An aggregate was modified concurrently (optimistic-concurrency version mismatch)."""

    def __init__(self, entity_name: str, entity_id: object, expected_version: int) -> None:
        self.entity_name = entity_name
        self.entity_id = entity_id
        self.expected_version = expected_version
        super().__init__(
            f"{entity_name} with id={entity_id!r} was modified concurrently "
            f"(expected version={expected_version})"
        )
