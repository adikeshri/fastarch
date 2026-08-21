# Testing

Four levels, each with a distinct purpose and a distinct set of things it's
allowed to depend on.

```bash
make test               # everything
make test-unit          # domain + application — no infrastructure
make test-integration   # + real Postgres/Redis via testcontainers
make test-e2e           # + a real FastAPI app over ASGI
make test-architecture  # dependency-rule / layering checks
```

All four run in CI (`.github/workflows/pr.yml`) as separate jobs, so a
failure tells you immediately which layer broke.

## Unit tests (`tests/unit/`)

No Docker, no network, no database — these run in well under a second.

- `tests/unit/domain/` — aggregate behavior and invariants
  (`test_user_aggregate.py`), value object validation
  (`test_value_objects.py`), the shared kernel
  (`test_shared_kernel.py`), domain services
  (`test_reserved_name_policy.py`).
- `tests/unit/application/` — command/query handlers against
  **fakes**, not mocks: `tests/unit/application/users/fakes.py` implements
  `UnitOfWork`/`UserRepository` in-memory, including real
  optimistic-concurrency and event-collection semantics, so handler tests
  exercise real collaboration behavior. `tests/unit/application/common/`
  tests the `Mediator` and every pipeline behavior directly.
- `tests/unit/infrastructure/` — pure-logic infrastructure pieces that
  need no real infra (e.g. `authorization/policies.py`'s
  permission-table logic).

## Integration tests (`tests/integration/`)

Real Postgres + Redis, via [testcontainers](https://testcontainers.com/) —
`tests/integration/conftest.py` starts one container pair per test
*session* (expensive to start, so shared), but builds a fresh
`AsyncEngine` per test *function*, because an `AsyncEngine`'s connections
are bound to the event loop they were created on, and pytest-asyncio gives
each test its own loop by default. Schema is created directly from
`Base.metadata` for speed — migration *history* correctness (upgrade →
downgrade → upgrade) is a separate CI job against the real Alembic CLI, not
something the fast test loop re-verifies on every run.

Covers: the SQLAlchemy repository (including a genuine concurrency-conflict
test with two concurrent readers), the Unit of Work's atomic
aggregate+outbox commit, the outbox relay (publish/fail/retry-backoff), and
the Redis cache/idempotency-store adapters.

Only prerequisite: a working Docker daemon. No manual `docker compose up`,
no fixture data to seed by hand.

## End-to-end tests (`tests/e2e/`)

A real `FastAPI` app (`app.main.create_app(settings)`), started with its
actual lifespan (via `asgi-lifespan`'s `LifespanManager`, since httpx's
`ASGITransport` doesn't trigger `@asynccontextmanager` lifespan handlers on
its own), talking to real testcontainers Postgres/Redis, driven entirely
over HTTP via `httpx.AsyncClient`. This is the closest thing to hitting the
deployed service without deploying it — the full register → get → list →
rename → deactivate flow, the RFC 7807 error contract, JWT-authenticated
authorization, health endpoints, and OpenAPI generation are all verified
here.

## Architecture tests (`tests/architecture/`)

See [`dependency-rules.md`](dependency-rules.md#how-its-enforced). Turns
the dependency rule from a convention into a test that fails your build.

## Test data (`tests/factories/`)

`tests/factories/user_factory.py` — plain builder functions
(`make_user()`, `make_email()`, `make_display_name()`) for domain/
application tests, and a `polyfactory`-based `RegisterUserRequestFactory`
for API-payload generation. Builders take explicit keyword overrides so a
test stays readable about exactly what it's asserting on, rather than
hiding the interesting field among a wall of generated noise (PRD §49).

## Coverage

`pyproject.toml [tool.coverage.report] fail_under = 80`. Current coverage
is ~86%; the gap is intentionally uncovered demonstration adapters that
need a live broker/worker process to exercise meaningfully in a unit/
integration test (the arq worker entrypoint itself, `RedisStreamsConsumer`'s
`_run` loop, the SMTP adapter's real network call) — these are exercised at
the "does it construct correctly and satisfy its port" level, and the
outbox relay's `Publisher.publish()` call (the actual integration point) is
covered via `RecordingPublisher` in the outbox relay integration tests.

## Writing a new test

1. Can it run without infrastructure? → `tests/unit/`.
2. Does it need a real database/cache but not a full running app? →
   `tests/integration/`.
3. Does it need to go through real HTTP? → `tests/e2e/`.
4. Does it verify a layering rule? → `tests/architecture/`.

When in doubt, prefer the lowest level that can actually express the
behavior — a domain invariant belongs in a unit test even if it's *also*
implicitly exercised by an e2e test; the unit test is what tells you
precisely what broke.
