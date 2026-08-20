"""arq implementation of the :class:`JobQueue` port.

arq was chosen (over Celery) because it's async-native and Redis-based,
reusing the Redis dependency already required for caching/idempotency
without adding a second broker to operate. See ``docs/background-jobs.md``
for the adapter strategy if a different durable worker system is needed.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from arq import ArqRedis

from app.application.common.interfaces.job_queue import JobQueue


class ArqJobQueue(JobQueue):
    def __init__(self, redis: ArqRedis) -> None:
        self._redis = redis

    async def enqueue(
        self,
        job_name: str,
        *args: Any,
        job_id: str | None = None,
        defer_by: timedelta | None = None,
        **kwargs: Any,
    ) -> str:
        job = await self._redis.enqueue_job(
            job_name, *args, _job_id=job_id, _defer_by=defer_by, **kwargs
        )
        # `job` is None when `job_id` collided with a still-pending job — that's the
        # intended idempotent-enqueue behavior, so surface the id the caller asked for.
        return job.job_id if job is not None else (job_id or job_name)
