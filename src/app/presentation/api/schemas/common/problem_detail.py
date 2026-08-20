"""RFC 7807 ``application/problem+json`` error contract (PRD §32)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProblemDetail(BaseModel):
    type: str = Field(examples=["https://fastarch.dev/errors/not-found"])
    title: str = Field(examples=["Not Found"])
    status: int = Field(examples=[404])
    detail: str = Field(examples=["The requested user does not exist"])
    instance: str = Field(examples=["/api/v1/users/123"])
    trace_id: str | None = None
    errors: dict[str, list[str]] | None = None
