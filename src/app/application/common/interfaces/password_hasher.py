"""Password hashing port, isolating the choice of hashing algorithm
(argon2, via ``app.infrastructure.authentication``) from application code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, plain_password: str) -> str: ...

    @abstractmethod
    def verify(self, plain_password: str, hashed_password: str) -> bool: ...
