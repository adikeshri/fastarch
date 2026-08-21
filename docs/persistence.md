# Persistence

SQLAlchemy 2.x async ORM + `asyncpg`, behind the domain-owned
`UserRepository` port and the application-owned `UnitOfWork` port. Nothing
above `app.infrastructure.persistence` imports SQLAlchemy.

## Layout

```
infrastructure/persistence/
├── database.py           # engine + session factory construction
├── models/
│   ├── base.py            # DeclarativeBase + naming convention
│   └── user_model.py       # UserModel — plain ORM record, no behavior
├── mappers/
│   └── user_mapper.py      # to_domain() / to_model() — the ONLY place
│                            # that knows about both User and UserModel
├── repositories/
│   └── sqlalchemy_user_repository.py
├── outbox/
│   ├── model.py            # OutboxModel
│   └── relay.py            # OutboxRelay — see outbox.md
├── unit_of_work.py         # SqlAlchemyUnitOfWork
└── model_registry.py       # imports every model so Base.metadata is complete
```

## ORM models are not domain entities

`UserModel` (a `Mapped[...]`-annotated SQLAlchemy class) and `User` (the
domain aggregate) are two different classes that never touch each other
directly. `mappers/user_mapper.py` is the explicit, bidirectional
translation layer:

```python
def to_domain(model: UserModel) -> User: ...
def to_model(user: User) -> UserModel: ...
```

This is what PRD §61 calls out as the "ORM/domain coupling" anti-pattern to
avoid — using `UserModel` as if it were the aggregate would leak SQLAlchemy
session/identity-map semantics into business logic.

## Optimistic concurrency

Every aggregate row has an integer `version` column. `SqlAlchemyUserRepository.save()`
issues a version-checked UPDATE, not a blind one:

```python
stmt = (
    update(UserModel)
    .where(UserModel.id == user.id.value, UserModel.version == user.version)
    .values(..., version=user.version + 1)
)
result = await self._session.execute(stmt)
if result.rowcount == 0:
    raise UserConcurrencyConflict(...)
user.mark_persisted(new_version)
```

Zero rows affected means someone else committed a change first — the
repository raises `ConcurrencyConflict` (mapped to HTTP 409, see
[`api.md`](api.md)) rather than silently overwriting. The domain layer
never sees a database row, but the aggregate does carry the version it was
loaded at (`AggregateRoot.version`) so this check is possible without
leaking ORM details into `app.domain` (PRD §44).

## Unit of Work

`app.application.common.interfaces.unit_of_work.UnitOfWork` is the
transaction boundary — a handler does:

```python
async with self._uow_factory() as uow:
    user = await uow.users.get_by_id(user_id)
    user.rename(new_name)
    await uow.users.save(user)
    await uow.commit()
    return UserDTO.from_domain(user)
```

`SqlAlchemyUnitOfWork` opens one `AsyncSession` per `async with` block,
exposes `.users` (the repository), and on `commit()`:

1. Converts every domain event collected by the repository during this
   transaction into an `OutboxModel` row.
2. Commits the session — aggregate changes and outbox rows land in the
   **same** database transaction. See [`outbox.md`](outbox.md).

On any exception, `__aexit__` calls `rollback()` automatically — nothing is
half-committed.

## Migrations

Alembic, async `env.py` (`migrations/env.py`), driven by
`app.infrastructure.configuration.settings` — `DATABASE__URL` is the single
source of truth for which database migrations run against, never a
hardcoded value in `alembic.ini`.

```bash
make migrate                       # upgrade to head
make migration name="add foo bar"  # autogenerate a new revision
uv run alembic downgrade -1        # roll back one revision
```

**Safe migration practices**:

- Every migration's `downgrade()` should actually work. CI's "migrations"
  job runs `upgrade → downgrade → upgrade` against a fresh Postgres on
  every PR.
- Adding a `NOT NULL` column to an existing table: add it nullable, backfill,
  then add the constraint in a follow-up migration — don't lock a large
  table with a single blocking `ALTER TABLE ... NOT NULL`.
- Prefer additive, backward-compatible migrations when the API and schema
  deploy independently (rolling deploys): add a column before code that
  reads it ships; remove a column only after code that reads it is gone.
- Autogenerate is a starting point, not the final answer — always read the
  generated migration before committing it (`model_registry.py` ensures
  autogenerate sees every model, but it can't see data-migration logic,
  and it sometimes gets index/constraint naming or type changes wrong).

## Connection pooling

`DatabaseSettings.pool_size`/`max_overflow`/`pool_timeout_seconds` (see
[`configuration.md`](configuration.md)) — tune per environment;
`pool_pre_ping=True` is on by default so a dropped connection is detected
and replaced rather than surfacing as a mysterious query failure.
