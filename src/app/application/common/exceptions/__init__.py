"""Application-layer exceptions.

Handlers raise these for failures that are about *use-case orchestration*
rather than domain invariants (e.g. "you're not allowed to do this", "this
input failed validation", "an idempotent replay was detected"). Like domain
exceptions, they carry no HTTP knowledge — mapping happens in
``app.presentation.api.exception_handlers``.
"""

from __future__ import annotations


class ApplicationException(Exception):
    """Base type for every exception raised from within the application layer."""


class ValidationException(ApplicationException):
    """Input failed application-level validation (as opposed to a domain invariant)."""

    def __init__(self, errors: dict[str, list[str]]) -> None:
        self.errors = errors
        super().__init__(f"Validation failed: {errors}")


class AuthenticationException(ApplicationException):
    """The caller could not be authenticated."""


class AuthorizationException(ApplicationException):
    """The (authenticated) caller is not permitted to perform this use case."""

    def __init__(self, message: str = "You are not authorized to perform this action") -> None:
        super().__init__(message)


class NotFoundException(ApplicationException):
    """A referenced resource does not exist, from the application's point of view."""


class ConflictException(ApplicationException):
    """The requested operation conflicts with the current state of the resource."""


class InfrastructureException(ApplicationException):
    """An infrastructure dependency (DB, cache, broker, external API) failed unexpectedly."""

    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.__cause__ = cause


__all__ = [
    "ApplicationException",
    "AuthenticationException",
    "AuthorizationException",
    "ConflictException",
    "InfrastructureException",
    "NotFoundException",
    "ValidationException",
]
