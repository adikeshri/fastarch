"""Background-job port.

FastAPI ``BackgroundTasks`` is explicitly not a production job system (PRD
§24) — it runs in-process and is lost on crash/restart. This port is backed
in production by ``app.infrastructure.background_jobs.arq_job_queue``
(arq/Redis), which gives durable, retryable, observable jobs. Job functions
themselves are plain callables registered with the worker; this port is only
for *enqueuing*.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any


class JobQueue(ABC):
    @abstractmethod
    async def enqueue(
        self,
        job_name: str,
        *args: Any,
        job_id: str | None = None,
        defer_by: timedelta | None = None,
        **kwargs: Any,
    ) -> str:
        """Enqueue a job by its registered name.

        Args:
            job_id: When provided, enqueuing is idempotent — a second call
                with the same ``job_id`` while the first is still
                pending/running is a no-op.
            defer_by: Delay execution by this duration.

        Returns:
            The job id (generated if not provided).
        """
