"""Development/test adapter: logs the email instead of sending it.

Swap for ``SmtpEmailSender`` or a provider-SDK-backed adapter in production
via the composition root — application code never notices the difference,
it only depends on ``NotificationSender``.
"""

from __future__ import annotations

import structlog

from app.application.common.interfaces.notification_sender import NotificationSender

logger = structlog.get_logger(__name__)


class ConsoleEmailSender(NotificationSender):
    async def send_welcome_email(self, *, to_email: str, display_name: str) -> None:
        logger.info("email.welcome_sent", to_email=to_email, display_name=display_name)
