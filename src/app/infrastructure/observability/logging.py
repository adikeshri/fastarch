"""Structured logging configuration (PRD §37).

Configures ``structlog`` to emit JSON in production-like environments and
a readable console format in development, with a processor that pulls the
current correlation/trace id out of contextvars
(``app.presentation.api.middleware.correlation``) into every log line, and
one that redacts a fixed set of sensitive keys so secrets can never leak
into logs even if a developer accidentally binds them.
"""

from __future__ import annotations

import logging
from typing import Any

import structlog

from app.infrastructure.configuration.settings import ObservabilitySettings

_SENSITIVE_KEYS = {"password", "token", "authorization", "secret", "access_token", "refresh_token"}


def _redact_sensitive(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    for key in list(event_dict):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "***REDACTED***"
    return event_dict


def configure_logging(settings: ObservabilitySettings) -> None:
    logging.basicConfig(level=settings.log_level, format="%(message)s")

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _redact_sensitive,
    ]

    renderer = (
        structlog.processors.JSONRenderer()
        if settings.json_logs
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping().get(settings.log_level, logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
