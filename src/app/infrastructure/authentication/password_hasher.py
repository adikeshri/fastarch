from __future__ import annotations

from passlib.context import CryptContext

from app.application.common.interfaces.password_hasher import PasswordHasher

_context = CryptContext(schemes=["argon2"], deprecated="auto")


class Argon2PasswordHasher(PasswordHasher):
    def hash(self, plain_password: str) -> str:
        return _context.hash(plain_password)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return _context.verify(plain_password, hashed_password)
