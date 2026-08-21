# Dependency Rules

These rules are enforced by `[tool.importlinter]` in `pyproject.toml`, run
via `make lint-arch` and `tests/architecture/test_layers.py`. If you're
unsure whether a change is allowed, run `make lint-arch` — it will tell you.

## The rules

### `app.domain`

**May depend on**: the Python standard library, other `app.domain.*` modules.

**Must never depend on**: FastAPI, Starlette, Pydantic, SQLAlchemy, Alembic,
Redis, arq, `httpx`, `jwt`, `passlib` — or any `app.application`,
`app.infrastructure`, `app.presentation`, `app.composition` module.

The domain layer must be importable and unit-testable without initializing
FastAPI, a database, or any infrastructure. Run `uv run python -c "import
app.domain"` — it should succeed even with Postgres/Redis stopped.

### `app.application`

**May depend on**: `app.domain`, other `app.application.*` modules.

**Must never depend on**: FastAPI, Starlette, SQLAlchemy, Alembic, Redis,
arq, `jwt`, `passlib` — or `app.infrastructure`, `app.presentation`,
`app.composition`.

Application code depends on *ports* (`app.application.common.interfaces`),
never on concrete infrastructure. A handler takes a `UnitOfWorkFactory`, not
a `SqlAlchemyUnitOfWork`.

Pydantic is intentionally on the forbidden list for `app.application` too —
DTOs are plain dataclasses (`app.application.users.dto.user_dto.UserDTO`),
not Pydantic models, so the application layer's data shapes don't
accidentally couple to a specific validation library.

### `app.infrastructure`

**May depend on**: `app.domain`, `app.application`, and any third-party
infrastructure library.

Infrastructure implements the ports the inner layers define. It must never
force the domain or application layer to know it exists — dependency
*inversion*, not just avoidance.

### `app.presentation`

**May depend on**: `app.application`, `app.domain` (for DTO/value types where
convenient), FastAPI, Pydantic. In this template it also imports
`app.infrastructure.configuration.settings` directly for typed config
(a passive data holder, not a service) — see the note in
[`architecture.md`](architecture.md) if you're deciding whether a similar
exception is appropriate for your own infrastructure module.

**Must not**: construct SQLAlchemy models, open a SQLAlchemy session, or
otherwise reach around the application layer into infrastructure. Routes
call the `Mediator`; they never import a repository.

### `app.composition`

Deliberately **unconstrained** — the composition root's entire job is
importing every layer and wiring concrete infrastructure to abstract ports
(`composition/container.py`). It is the one place `SqlAlchemyUnitOfWork`,
`RedisCache`, `JwtTokenService`, etc. are actually instantiated.

### `app.main`

Also unconstrained, for the same reason: it's the process entrypoint that
assembles the FastAPI app from settings + the composition root + the
presentation router.

## How it's enforced

```toml
[tool.importlinter]
root_package = "app"

[[tool.importlinter.contracts]]
name = "Domain layer is framework/infrastructure independent"
type = "forbidden"
source_modules = ["app.domain"]
forbidden_modules = ["fastapi", "sqlalchemy", ..., "app.application", ...]

[[tool.importlinter.contracts]]
name = "Layers respect strict top-down layering"
type = "layers"
layers = ["app.presentation", "app.infrastructure", "app.application", "app.domain"]
```

Run it directly:

```bash
make lint-arch
```

Or as a pytest test (useful because it fails inside your normal test run,
not just in a separate CI step):

```bash
uv run pytest tests/architecture -m architecture
```

`tests/architecture/test_layers.py` also runs a second, independent AST-based
check as a safety net — if import-linter itself ever had a configuration bug
that silently stopped checking a layer, this second check would still catch
a domain module importing SQLAlchemy directly.

## What to do when the check fails

It usually means a shortcut was taken — a route querying the database
directly, a domain entity importing a DTO, an application handler
constructing a `Redis` client. The fix is almost always to introduce or use
an existing port in `app.application.common.interfaces` and implement it in
`app.infrastructure`, then wire it in `app.composition.container`. It is
essentially never correct to relax the contract instead.
