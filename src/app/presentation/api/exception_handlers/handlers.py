"""Centralized exception -> HTTP mapping (PRD §32).

Every exception type the domain/application layers are allowed to raise is
mapped here to a status code and an RFC 7807 problem-detail body. Nothing
below this module ever constructs an HTTP response or raises
``fastapi.HTTPException`` — that would be HTTP leakage into layers that must
stay transport-agnostic (PRD §61).
"""

from __future__ import annotations

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.application.common.exceptions import (
    ApplicationException,
    AuthenticationException,
    AuthorizationException,
    ConflictException,
    InfrastructureException,
    NotFoundException,
    ValidationException,
)
from app.domain.shared.exceptions import (
    BusinessRuleViolation,
    ConcurrencyConflict,
    DomainException,
    EntityNotFound,
    InvalidState,
    InvalidValueObject,
)
from app.infrastructure.configuration.settings import Environment, Settings
from app.presentation.api.schemas.common.problem_detail import ProblemDetail

logger = structlog.get_logger(__name__)

_ERRORS_BASE_URL = "https://fastarch.dev/errors"


def _problem_response(
    request: Request,
    *,
    status_code: int,
    title: str,
    detail: str,
    errors: dict[str, list[str]] | None = None,
) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", None)
    problem = ProblemDetail(
        type=f"{_ERRORS_BASE_URL}/{title.lower().replace(' ', '-')}",
        title=title,
        status=status_code,
        detail=detail,
        instance=str(request.url.path),
        trace_id=correlation_id,
        errors=errors,
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json",
    )


def register_exception_handlers(app: FastAPI, settings: Settings) -> None:
    # -- domain exceptions, most specific first ----------------------------

    @app.exception_handler(EntityNotFound)
    async def handle_not_found(request: Request, exc: EntityNotFound) -> JSONResponse:
        return _problem_response(
            request, status_code=status.HTTP_404_NOT_FOUND, title="Not Found", detail=str(exc)
        )

    @app.exception_handler(ConcurrencyConflict)
    async def handle_concurrency_conflict(
        request: Request, exc: ConcurrencyConflict
    ) -> JSONResponse:
        return _problem_response(
            request, status_code=status.HTTP_409_CONFLICT, title="Conflict", detail=str(exc)
        )

    @app.exception_handler(BusinessRuleViolation)
    async def handle_business_rule_violation(
        request: Request, exc: BusinessRuleViolation
    ) -> JSONResponse:
        return _problem_response(
            request,
            status_code=status.HTTP_409_CONFLICT,
            title="Business Rule Violation",
            detail=str(exc),
        )

    @app.exception_handler(InvalidValueObject)
    @app.exception_handler(InvalidState)
    async def handle_invalid_input(request: Request, exc: DomainException) -> JSONResponse:
        return _problem_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Invalid Input",
            detail=str(exc),
        )

    @app.exception_handler(DomainException)
    async def handle_domain_exception(request: Request, exc: DomainException) -> JSONResponse:
        return _problem_response(
            request, status_code=status.HTTP_400_BAD_REQUEST, title="Domain Error", detail=str(exc)
        )

    # -- application exceptions ---------------------------------------------

    @app.exception_handler(ValidationException)
    async def handle_validation_exception(
        request: Request, exc: ValidationException
    ) -> JSONResponse:
        return _problem_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation Failed",
            detail="One or more fields failed validation",
            errors=exc.errors,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors: dict[str, list[str]] = {}
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"])
            errors.setdefault(field, []).append(error["msg"])
        return _problem_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation Failed",
            detail="One or more fields failed validation",
            errors=errors,
        )

    @app.exception_handler(AuthenticationException)
    async def handle_authentication_exception(
        request: Request, exc: AuthenticationException
    ) -> JSONResponse:
        return _problem_response(
            request, status_code=status.HTTP_401_UNAUTHORIZED, title="Unauthorized", detail=str(exc)
        )

    @app.exception_handler(AuthorizationException)
    async def handle_authorization_exception(
        request: Request, exc: AuthorizationException
    ) -> JSONResponse:
        return _problem_response(
            request, status_code=status.HTTP_403_FORBIDDEN, title="Forbidden", detail=str(exc)
        )

    @app.exception_handler(NotFoundException)
    async def handle_application_not_found(
        request: Request, exc: NotFoundException
    ) -> JSONResponse:
        return _problem_response(
            request, status_code=status.HTTP_404_NOT_FOUND, title="Not Found", detail=str(exc)
        )

    @app.exception_handler(ConflictException)
    async def handle_conflict_exception(request: Request, exc: ConflictException) -> JSONResponse:
        return _problem_response(
            request, status_code=status.HTTP_409_CONFLICT, title="Conflict", detail=str(exc)
        )

    @app.exception_handler(InfrastructureException)
    async def handle_infrastructure_exception(
        request: Request, exc: InfrastructureException
    ) -> JSONResponse:
        logger.exception("infrastructure.error", error=str(exc))
        return _problem_response(
            request,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            title="Service Unavailable",
            detail="A downstream dependency is currently unavailable",
        )

    @app.exception_handler(ApplicationException)
    async def handle_application_exception(
        request: Request, exc: ApplicationException
    ) -> JSONResponse:
        return _problem_response(
            request,
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Application Error",
            detail=str(exc),
        )

    # -- last resort: never leak internals in production ---------------------

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled.exception")
        detail = (
            str(exc)
            if settings.environment is Environment.DEVELOPMENT
            else "An unexpected error occurred"
        )
        return _problem_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Internal Server Error",
            detail=detail,
        )
