"""SQLAlchemy model for the transactional outbox (PRD §22).

A row is written in the *same* transaction as the aggregate change that
raised the domain event (see
``app.infrastructure.persistence.unit_of_work.SqlAlchemyUnitOfWork.commit``),
so an event can never be observed as "published" without its originating
change having actually committed, and never lost if the process crashes
between commit and publish — the relay (``outbox/relay.py``) will pick it up
on the next poll.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"


class OutboxModel(Base):
    __tablename__ = "outbox_messages"
    __table_args__ = (
        Index("ix_outbox_status_created_at", "status", "created_at"),
        Index("ix_outbox_aggregate_id", "aggregate_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(200), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=OutboxStatus.PENDING.value
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
