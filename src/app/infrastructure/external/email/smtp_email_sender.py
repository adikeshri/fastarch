"""Production-shaped adapter using stdlib ``smtplib``.

The only file in the template allowed to import ``smtplib`` — this is the
isolation boundary PRD §26 asks for. Runs the blocking client in a thread so
it doesn't stall the event loop.
"""

from __future__ import annotations

import asyncio
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.application.common.interfaces.notification_sender import NotificationSender


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int
    from_address: str
    use_tls: bool = True


class SmtpEmailSender(NotificationSender):
    def __init__(self, settings: SmtpSettings) -> None:
        self._settings = settings

    async def send_welcome_email(self, *, to_email: str, display_name: str) -> None:
        message = EmailMessage()
        message["From"] = self._settings.from_address
        message["To"] = to_email
        message["Subject"] = "Welcome!"
        message.set_content(f"Hi {display_name}, welcome aboard.")
        await asyncio.to_thread(self._send_sync, message)

    def _send_sync(self, message: EmailMessage) -> None:
        with smtplib.SMTP(self._settings.host, self._settings.port) as client:
            if self._settings.use_tls:
                client.starttls()
            client.send_message(message)
