from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterUserRequest(BaseModel):
    email: EmailStr = Field(examples=["ada@example.com"])
    display_name: str = Field(min_length=1, max_length=120, examples=["Ada Lovelace"])


class RenameUserRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=120, examples=["Ada, Countess of Lovelace"])


class DeactivateUserRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500, examples=["Requested account closure"])
