"""Port for outbound notifications (email today; same shape would cover SMS/push).

Concrete adapters live in ``app.infrastructure.external.email`` and hide
whatever client library they use (``smtplib``, an HTTP-based provider SDK,
...) — nothing outside that package imports the client library directly
(PRD §26).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class NotificationSender(ABC):
    @abstractmethod
    async def send_welcome_email(self, *, to_email: str, display_name: str) -> None: ...
