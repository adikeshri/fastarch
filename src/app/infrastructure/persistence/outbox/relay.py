"""The outbox relay: moves committed outbox rows to the message broker.

Runs as a periodic ``arq`` job (registered in
``app.infrastructure.background_jobs.arq_job_queue``). Uses
``SELECT ... FOR UPDATE SKIP LOCKED`` so multiple relay workers can run
concurrently without double-publishing, and tracks attempt/failure metadata
so permanently-failing rows stop being retried and are visible for
operator triage instead of looping forever.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.common.interfaces.publisher import OutboundMessage, Publisher
from app.infrastructure.persistence.outbox.model import OutboxModel, OutboxStatus

logger = structlog.get_logger(__name__)

_BACKOFF_BASE_SECONDS = 5


class OutboxRelay:
    def __init__(self, publisher: Publisher, *, batch_size: int, max_attempts: int) -> None:
        self._publisher = publisher
        self._batch_size = batch_size
        self._max_attempts = max_attempts

    async def relay_once(self, session: AsyncSession) -> int:
        """Publish one batch of due outbox rows. Returns the number of rows processed."""
        now = datetime.now(UTC)
        stmt = (
            select(OutboxModel)
            .where(
                OutboxModel.status.in_([OutboxStatus.PENDING.value, OutboxStatus.FAILED.value]),
                OutboxModel.available_at <= now,
                OutboxModel.attempt_count < self._max_attempts,
            )
            .order_by(OutboxModel.created_at)
            .limit(self._batch_size)
            .with_for_update(skip_locked=True)
        )
        rows = (await session.execute(stmt)).scalars().all()

        for row in rows:
            await self._process_row(session, row)

        await session.commit()
        return len(rows)

    async def _process_row(self, session: AsyncSession, row: OutboxModel) -> None:
        row.status = OutboxStatus.PROCESSING.value
        row.attempt_count += 1
        try:
            await self._publisher.publish(
                OutboundMessage(
                    topic=row.aggregate_type,
                    key=str(row.aggregate_id),
                    event_type=row.event_type,
                    payload=row.payload,
                    headers={"outbox-id": str(row.id)},
                )
            )
        except Exception as exc:
            row.status = OutboxStatus.FAILED.value
            row.last_error = str(exc)[:2000]
            row.available_at = datetime.now(UTC) + timedelta(
                seconds=_BACKOFF_BASE_SECONDS * (2 ** min(row.attempt_count, 8))
            )
            logger.warning(
                "outbox.publish_failed",
                outbox_id=str(row.id),
                event_type=row.event_type,
                attempt=row.attempt_count,
                error=str(exc),
            )
        else:
            row.status = OutboxStatus.PUBLISHED.value
            row.processed_at = datetime.now(UTC)
