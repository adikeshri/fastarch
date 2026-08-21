# API

## Versioning

Every route lives under `/api/v1/...` (`presentation/api/v1/router.py`).
Adding `/api/v2` for a breaking change means adding a new
`presentation/api/v2/` package and mounting it alongside `v1` in
`main.py` — the application and domain layers never know a version number
exists, since versioning is purely a presentation/transport concern.

## Serialization boundary

```
Domain (User aggregate, value objects)
    ↓  UserDTO.from_domain(user)          [application]
Application DTO (UserDTO — a plain dataclass)
    ↓  UserResponse.model_validate(dto)   [presentation]
Presentation schema (UserResponse — a Pydantic model)
    ↓  FastAPI's JSON renderer
JSON
```

The domain is never responsible for JSON serialization (PRD §66) — it
doesn't even know Pydantic exists (see
[`dependency-rules.md`](dependency-rules.md)).

## Request/response schemas

`presentation/api/schemas/users/`:

- `requests.py` — `RegisterUserRequest`, `RenameUserRequest`,
  `DeactivateUserRequest`. Validated by Pydantic before the route body
  even runs.
- `responses.py` — `UserResponse`, built via
  `UserResponse.model_validate(dto, from_attributes=True)`.

`presentation/api/schemas/common/`:

- `pagination.py` — `PageResponse[T]`, wrapping the application layer's
  framework-free `Page[T]`.
- `problem_detail.py` — the RFC 7807 error contract, see below.

## Routes stay thin

Every route in `presentation/api/v1/users/router.py` follows the same
shape: parse → build a command/query → `mediator.send(...)` → map the DTO
to a response schema. No business logic, no SQLAlchemy import, no domain
rule — see PRD §61 ("fat controllers") and
[`application-layer.md`](application-layer.md) for where that logic
actually lives.

## Error contract

Centralized exception handling
(`presentation/api/exception_handlers/handlers.py`) maps every domain and
application exception to an `application/problem+json` response
(RFC 7807):

```json
{
  "type": "https://fastarch.dev/errors/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "User with id=... was not found",
  "instance": "/api/v1/users/123",
  "trace_id": "0f810f32-6e10-4c60-b3d8-76bb61511b24"
}
```

| Exception | HTTP status |
|---|---|
| `EntityNotFound`, `NotFoundException` | 404 |
| `ConcurrencyConflict`, `BusinessRuleViolation`, `ConflictException` | 409 |
| `InvalidValueObject`, `InvalidState`, `ValidationException`, request validation | 422 |
| `AuthenticationException` | 401 |
| `AuthorizationException` | 403 |
| `InfrastructureException` | 503 |
| Anything else (`DomainException`, `ApplicationException` catch-alls) | 400 |
| Unhandled `Exception` | 500 — detail hidden outside `development` |

No stack trace or internal detail is ever returned to the client in
`staging`/`production` (see `Environment.is_production_like` in
`infrastructure/configuration/settings.py`).

## Pagination

Offset pagination is the default (`Page`/`PageRequest` in
`application/common/dto/pagination.py`); `PaginationParams` in
`presentation/api/dependencies/pagination.py` is the only place FastAPI
`Query` parameters get parsed, clamped (`limit` 1–100), and turned into
plain ints before crossing into the application layer. Cursor pagination
follows the same shape — a `PageRequest`-like dataclass owned by
`application/common/dto` and parsed in a dedicated
`presentation/api/dependencies` function — for endpoints where offset
pagination doesn't scale (deep pages on a large, frequently-mutated table).

## Idempotency

Commands that carry an `Idempotency-Key` header (parsed in
`presentation/api/dependencies/mediator.get_request_context`) get
short-circuited by `IdempotencyBehavior` if the same key+payload was already
processed. See [`application-layer.md`](application-layer.md) and PRD §43.

## OpenAPI

`main.py`'s `create_app()` sets title/description/version/contact/license
on the `FastAPI` instance, and the `/api/docs` (Swagger UI) and
`/api/redoc` routes are enabled by default. Every route has a `summary`;
add `description` and `responses={...}` on routes where the default
"200 + your Pydantic model" isn't the whole story (e.g. documenting the 409
on `POST /users`).
