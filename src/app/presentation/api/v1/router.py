"""Aggregates every v1 resource router under a single ``/v1`` prefix.

Adding a new bounded context's API means adding one ``include_router`` call
here — see the root README's "Adding a new bounded context" section for the
full checklist.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.presentation.api.v1.users.router import router as users_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(users_router)
