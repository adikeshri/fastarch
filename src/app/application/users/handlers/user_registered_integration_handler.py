"""Consumes ``UserRegistered`` off the message broker and sends a welcome email.

This is the consumption side of the outbox/messaging story: the aggregate
raised the event, the outbox relay published it, and this handler — running
in the arq worker process, wired to a :class:`Consumer` at startup — reacts
to it asynchronously and independently of the original HTTP request.
"""

from __future__ import annotations

from app.application.common.interfaces.notification_sender import NotificationSender
from app.application.common.interfaces.publisher import MessageHandler, OutboundMessage


class UserRegisteredIntegrationHandler(MessageHandler):
    def __init__(self, notification_sender: NotificationSender) -> None:
        self._notification_sender = notification_sender

    async def handle(self, message: OutboundMessage) -> None:
        await self._notification_sender.send_welcome_email(
            to_email=message.payload["email"],
            display_name=message.payload["display_name"],
        )
