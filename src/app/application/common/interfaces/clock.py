"""Clock port — allows deterministic testing of time-dependent application logic.

Domain entities use ``datetime.now(UTC)`` directly for their own creation
timestamps (a pure, referentially-simple call), but application-layer code
that needs to *reason* about "now" (e.g. idempotency-key expiry) should go
through this port so tests can inject a fixed/fake clock.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime:
        """Return the current UTC, timezone-aware time."""
