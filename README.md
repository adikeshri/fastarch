# fastarch

Production-grade FastAPI template built on Clean Architecture, Domain-Driven
Design, CQRS, and SOLID principles.

This is not a tutorial or a proof of concept — it's a complete, opinionated
foundation you clone as the starting point for a real production backend
service: persistence, migrations, a transactional outbox, background jobs,
caching, auth, observability, centralized error handling, Docker, CI, and a
fully working example bounded context, all wired together and tested.

## Why this exists

Most FastAPI starters give you routes talking directly to SQLAlchemy models.
That's fast to start and painful to grow: business rules end up scattered
across route handlers, the domain becomes untestable without a live
database, and swapping any infrastructure piece (the broker, the ORM, the
auth provider) means touching code everywhere. fastarch enforces a
different shape — one where the *correct* design is the *easiest* design —
and backs the enforcement with an actual automated test, not just a
convention in a wiki page.

## Architecture at a glance

```
                    ┌─────────────────────┐
                    │    Presentation      │  FastAPI routes, Pydantic
                    │                      │  schemas, middleware
                    └──────────┬───────────┘
                               │ depends on
                               ▼
                    ┌─────────────────────┐
                    │     Application      │  Commands/Queries, handlers,
                    │                      │  Mediator pipeline, DTOs
                    └──────────┬───────────┘
                               │ depends on
                               ▼
                    ┌─────────────────────┐
                    │        Domain        │  Entities, aggregates, value
                    │                      │  objects, domain events
                    └─────────────────────┘
                               ▲
                               │ implements domain-defined ports
                    ┌──────────┴───────────┐
                    │    Infrastructure     │  Postgres/SQLAlchemy, Redis,
                    │                      │  JWT, OpenTelemetry, arq
                    └─────────────────────┘
```

**The dependency rule**: source-code dependencies point inward. The domain
has zero framework/infrastructure dependencies, and this is enforced by an
`import-linter` contract that runs as a real test
(`tests/architecture/test_layers.py`) and in CI — not a convention you have
to trust people to follow. Full details:
[`docs/architecture.md`](docs/architecture.md) and
[`docs/dependency-rules.md`](docs/dependency-rules.md).

## Technology stack

| Concern | Choice |
|---|---|
| Runtime | Python 3.13+, FastAPI, Uvicorn, Pydantic v2, pydantic-settings |
| Package management | [uv](https://docs.astral.sh/uv/) |
| Persistence | SQLAlchemy 2.x (async), `asyncpg`, PostgreSQL, Alembic |
| Caching / idempotency | Redis |
| Messaging | Redis Streams (default), swappable behind a `Publisher`/`Consumer` port — see [`docs/messaging.md`](docs/messaging.md) |
| Background jobs | [arq](https://arq-docs.helpmanual.io/), swappable behind a `JobQueue` port — see [`docs/background-jobs.md`](docs/background-jobs.md) |
| Auth | PyJWT (bearer/JWT), `passlib[argon2]` (password hashing) |
| Observability | `structlog` (JSON logs), OpenTelemetry (traces/metrics) |
| Testing | pytest, pytest-asyncio, httpx, testcontainers, polyfactory |
| Quality | Ruff (lint + format), mypy (strict), import-linter, pre-commit |
| Containers | Docker, Docker Compose |

See [`docs/`](docs/) for a full write-up of every subsystem, and
[`docs/architectural-decisions/`](docs/architectural-decisions/) for the
reasoning behind each major choice.

## Project structure

```
src/app/
├── domain/            # entities, aggregates, value objects, events — zero deps
│   ├── shared/          # Entity, AggregateRoot, ValueObject, DomainEvent, exceptions
│   └── users/            # the reference bounded context
├── application/        # use cases: commands, queries, handlers, the Mediator
│   ├── common/           # ports (interfaces/), pipeline behaviors/, DTOs
│   └── users/
├── infrastructure/      # concrete implementations of application/domain ports
│   ├── persistence/       # SQLAlchemy engine, models, mappers, repositories, outbox
│   ├── caching/, messaging/, background_jobs/, external/
│   ├── authentication/, authorization/, observability/, configuration/
├── presentation/api/    # FastAPI: routers, schemas, middleware, exception handlers
├── composition/         # container.py — the only place infra gets instantiated
└── main.py              # app factory + lifespan

tests/
├── unit/                 # domain + application — no infrastructure
├── integration/          # + real Postgres/Redis (testcontainers)
├── e2e/                  # + a real FastAPI app over HTTP
└── architecture/         # dependency-rule enforcement

migrations/               # Alembic
docs/                     # architecture write-ups + ADRs
```

## Setup

```bash
# 1. Install uv: https://docs.astral.sh/uv/getting-started/installation/
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies (creates .venv, resolves from uv.lock)
uv sync

# 3. Copy the env template and adjust if needed
cp .env.example .env

# 4. Start Postgres + Redis (+ the app + worker) via Docker
make docker-up

# 5. Apply migrations (already done automatically by docker-up's `migrate`
#    service, but this is the standalone command)
make migrate

# 6. Run the API with autoreload (outside Docker, against the same Postgres/Redis)
make dev
```

Verify it's alive:

```bash
curl localhost:8000/health/live
curl -X POST localhost:8000/api/v1/users \
  -H 'Content-Type: application/json' \
  -d '{"email": "ada@example.com", "display_name": "Ada Lovelace"}'
```

Interactive API docs: `http://localhost:8000/api/docs`.

## Local development

```bash
make dev              # run the API with autoreload
make worker           # run the arq background-job worker (outbox relay, etc.)
make lint             # ruff check + format --check
make format           # ruff check --fix + format
make typecheck        # mypy --strict
make lint-arch        # import-linter — the dependency-rule gate
make test             # everything
make test-unit        # domain + application, no infra, <1s
make test-integration # + real Postgres/Redis via testcontainers
make test-e2e         # + a real app over HTTP
make precommit        # install git hooks
```

`make help` lists every target.

## Testing

Four levels, each testing what it can with the least infrastructure
possible — see [`docs/testing.md`](docs/testing.md) for the full breakdown.
Integration and e2e tests only need a working Docker daemon (via
[testcontainers](https://testcontainers.com/)) — no manual `docker compose up`
or seeded fixtures required.

## Migrations

```bash
make migrate                       # upgrade to head
make migration name="add foo bar"  # autogenerate a new revision
uv run alembic downgrade -1        # roll back one revision
```

See [`docs/persistence.md`](docs/persistence.md#migrations) for safe
migration practices (backward-compatible rollouts, avoiding table locks on
large tables, always reading autogenerated migrations before committing).

## Docker

```bash
make docker-up     # postgres + redis + migrate (once) + app + worker
make docker-down   # tear down, including the postgres volume
make docker-build  # just build the image
```

`docker-compose.yml` runs the full stack; `docker-compose.test.yml` is a
lightweight Postgres/Redis pair for CI environments that can't do
Docker-in-Docker for testcontainers. See [`docs/deployment.md`](docs/deployment.md).

## Configuration

Everything is environment-driven through `Settings`
(`app.infrastructure.configuration.settings`) — see `.env.example` for
every variable, and [`docs/configuration.md`](docs/configuration.md) for
the reference.

## Deployment

The API is stateless and horizontally scalable; the worker scales
independently. See [`docs/deployment.md`](docs/deployment.md) for health
checks, graceful shutdown, and migration rollout practices.

## Extending the template

### Adding a new bounded context

1. `mkdir -p src/app/domain/<context>/{entities,value_objects,events,repositories,services,exceptions}`
   — model your aggregate(s), value objects, and domain events (copy the
   shape of `app.domain.users`).
2. Define repository port(s) in `domain/<context>/repositories/`.
3. `mkdir -p src/app/application/<context>/{commands,queries,handlers,dto,validators}`
   — one command/query dataclass + one handler per use case (see
   [`docs/application-layer.md`](docs/application-layer.md)).
4. Implement the repository under
   `infrastructure/persistence/repositories/`, the ORM model under
   `infrastructure/persistence/models/`, and the mapper under
   `infrastructure/persistence/mappers/` (see [`docs/persistence.md`](docs/persistence.md)).
5. Add Pydantic request/response schemas under
   `presentation/api/schemas/<context>/`.
6. Add a router under `presentation/api/v1/<context>/` and mount it in
   `presentation/api/v1/router.py`.
7. Register every new handler in `composition/container.py`'s handler map.
8. Add a migration: `make migration name="add <context> tables"`.
9. Add tests at every applicable level — unit (handlers against fakes),
   integration (the repository against real Postgres), e2e (the HTTP flow),
   and extend `tests/architecture` if the new context needs its own
   forbidden-import checks (it usually doesn't — the existing contracts
   already cover `app.domain`/`app.application` generally).

### Adding a new command

Add a `@dataclass(frozen=True)` subclass of `Command[ResultType]` in
`application/<context>/commands/`, with a `validate()` override for
application-level checks and a `required_permission` if it needs
authorization. Add a handler, register it in the composition root, add a
route. See [`docs/application-layer.md`](docs/application-layer.md).

### Adding a new query

Same shape as a command, but subclass `Query[ResultType]` and never call
`uow.commit()` in the handler. See
[`app/application/users/queries/get_user.py`](src/app/application/users/queries/get_user.py)
as the reference.

### Adding a new aggregate

Subclass `AggregateRoot[YourIdType]`
(`app.domain.shared.aggregate_root.AggregateRoot`); express every state
change as a method that enforces its own invariants and calls
`self.register_event(...)` for anything the rest of the system should react
to. See [`docs/domain-driven-design.md`](docs/domain-driven-design.md) and
`app.domain.users.entities.user.User` as the reference.

### Adding an external integration

Define a port in `application/common/interfaces/` (see
`NotificationSender` as the reference), implement it under
`infrastructure/external/<service>/` — that adapter module is the *only*
place the third-party client library (`httpx`, a vendor SDK, `smtplib`)
gets imported — and wire the concrete implementation in
`composition/container.py`. See [`docs/infrastructure.md`](docs/infrastructure.md#external-service-isolation).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Please also read
[`docs/dependency-rules.md`](docs/dependency-rules.md) before your first PR
— `make lint-arch` failing is the architecture doing its job, not a false
positive to work around.

## License

[MIT](LICENSE)
