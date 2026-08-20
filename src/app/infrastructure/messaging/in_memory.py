"""In-memory ``Publisher`` for unit/e2e tests and local dev without Redis.

Captures every published message so tests can assert on it directly instead
of needing a real broker.
"""

from __future__ import annotations

from app.application.common.interfaces.publisher import OutboundMessage, Publisher


class InMemoryPublisher(Publisher):
    def __init__(self) -> None:
        self.published: list[OutboundMessage] = []

    async def publish(self, message: OutboundMessage) -> None:
        self.published.append(message)
