"""Messaging port for publishing already-persisted integration events.

Only the outbox relay (``app.infrastructure.persistence.outbox.relay``)
calls this — application handlers never publish directly, so an event is
never observable externally before its originating transaction has
committed (PRD §22/§23).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OutboundMessage:
    topic: str
    key: str
    event_type: str
    payload: dict[str, Any]
    headers: dict[str, str]


class Publisher(ABC):
    @abstractmethod
    async def publish(self, message: OutboundMessage) -> None:
        """Publish a single message. Must raise on failure so the outbox can retry."""


class MessageHandler(ABC):
    """A single message-type handler registered with a :class:`Consumer`."""

    @abstractmethod
    async def handle(self, message: OutboundMessage) -> None: ...


class Consumer(ABC):
    @abstractmethod
    def register(self, event_type: str, handler: MessageHandler) -> None:
        """Register a handler for a given event type."""

    @abstractmethod
    async def start(self) -> None:
        """Start consuming in the background until :meth:`stop` is called."""

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully stop consuming, allowing in-flight messages to finish."""
