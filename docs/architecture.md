# Architecture

fastarch implements Clean Architecture (Robert C. Martin) combined with tactical
Domain-Driven Design and CQRS, adapted to modern async Python/FastAPI. The
goal is a codebase where the correct design is the easiest design — a
developer adding a feature has one obvious path to follow.

## The four layers

```
                    ┌─────────────────────┐
                    │    Presentation      │  FastAPI routes, Pydantic
                    │                      │  schemas, middleware, DI glue
                    └──────────┬───────────┘
                               │ depends on
                               ▼
                    ┌─────────────────────┐
                    │     Application      │  Commands/Queries, handlers,
                    │                      │  the Mediator pipeline, DTOs
                    └──────────┬───────────┘
                               │ depends on
                               ▼
                    ┌─────────────────────┐
                    │        Domain        │  Entities, aggregates, value
                    │                      │  objects, domain events, rules
                    └─────────────────────┘
                               ▲
                               │ implements domain-defined ports
                    ┌──────────┴───────────┐
                    │    Infrastructure     │  Postgres/SQLAlchemy, Redis,
                    │                      │  JWT, OpenTelemetry, arq
                    └─────────────────────┘
```

**The dependency rule**: source-code dependencies point inward, toward the
domain. The domain has zero dependencies on anything outside itself. This
is not a convention here — it's enforced by an import-linter contract
(`pyproject.toml [tool.importlinter]`) that runs as a pytest test
(`tests/architecture/test_layers.py`) and a dedicated CI job. See
[`dependency-rules.md`](dependency-rules.md) for the exact rules.

## Where each concern lives

| Concern | Layer | Example |
|---|---|---|
| Business invariants | Domain | `User.deactivate()` refuses to deactivate twice |
| Cross-aggregate business rules | Domain (service) | `ReservedDisplayNamePolicy` |
| Use-case orchestration, transactions | Application | `RegisterUserHandler` |
| Cross-cutting concerns (logging, auth, validation) | Application (pipeline) | `AuthorizationBehavior` |
| Persistence, caching, messaging, auth mechanics | Infrastructure | `SqlAlchemyUserRepository`, `RedisCache`, `JwtTokenService` |
| HTTP parsing/serialization, routing | Presentation | `presentation/api/v1/users/router.py` |
| Wiring concrete infrastructure to abstract ports | Composition | `composition/container.py` |

## Request lifecycle (the `RegisterUser` example)

```
HTTP POST /api/v1/users
    │
    ▼
FastAPI route (presentation/api/v1/users/router.py)
    │  parses RegisterUserRequest (Pydantic)
    ▼
RegisterUserCommand (application/users/commands/register_user.py)
    │  dispatched via Mediator.send(command, context)
    ▼
Pipeline: Logging → Performance → Validation → Authorization → Idempotency
    │
    ▼
RegisterUserHandler.handle()
    │  opens a UnitOfWork, checks email uniqueness via UserRepository
    ▼
User.register(email, display_name)          [domain]
    │  raises UserRegistered domain event
    ▼
UserRepository.add(user)                     [infrastructure]
    │  inserts the row, collects the event
    ▼
UnitOfWork.commit()                          [infrastructure]
    │  writes the outbox row in the SAME transaction, then commits
    ▼
201 Created — UserDTO mapped to UserResponse

  (asynchronously, out of band)
    OutboxRelay (arq cron job) → RedisStreamsPublisher → stream:users
        → RedisStreamsConsumer → UserRegisteredIntegrationHandler
        → NotificationSender.send_welcome_email()
```

Every arrow above crosses exactly one architectural boundary and does so
through an interface owned by the inner layer.

## Why this shape

- **Framework independence**: swap FastAPI for something else and the
  domain/application layers don't change a line.
- **Testability**: the domain and application layers are tested with zero
  infrastructure (`tests/unit`) — no database, no HTTP server, no Docker.
- **Independent evolution**: the read path (`ListUsersQuery`) and write path
  (`RegisterUserCommand`) can diverge — different caching, different
  persistence strategy — without touching each other.
- **A single obvious extension point** for every kind of change — see
  ["Adding a new bounded context"](../README.md#adding-a-new-bounded-context)
  in the README.

See also: [`domain-driven-design.md`](domain-driven-design.md),
[`application-layer.md`](application-layer.md), and the
[ADRs](architectural-decisions/) for the reasoning behind individual choices.
