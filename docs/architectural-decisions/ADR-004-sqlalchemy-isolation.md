# ADR-004: SQLAlchemy is isolated to the infrastructure layer

## Status

Accepted

## Context

It's tempting to use SQLAlchemy's declarative models directly as domain
entities — one less class to write and maintain. But an ORM model's
identity, lazy-loading, and session-attachment semantics are persistence
concerns, not business ones; letting them leak into the domain couples
business logic to a specific database library and makes domain code
untestable without a database session (PRD §61, "ORM/domain coupling").

## Decision

`app.infrastructure.persistence.models.user_model.UserModel` (the ORM
class) and `app.domain.users.entities.user.User` (the domain aggregate) are
two separate classes. `app.infrastructure.persistence.mappers.user_mapper`
is the *only* code that knows about both — explicit `to_domain()`/
`to_model()` functions, not a shared base class or a `from_orm()` method on
the aggregate itself. See [`persistence.md`](../persistence.md).

Repository interfaces (`app.domain.users.repositories.user_repository`)
expose domain vocabulary (`get_by_id(UserId) -> User | None`), never
SQLAlchemy vocabulary (no `Session`, no `Query`, no ORM model in the
signature).

## Consequences

**Positive**: `app.domain` genuinely has zero SQLAlchemy dependency
(enforced by the import-linter contract) and is importable/testable
without a database; swapping the ORM (or moving a specific repository to
raw SQL for a performance-critical read) touches only
`app.infrastructure.persistence`, never the domain or application layer.

**Negative**: every field needs to be mapped explicitly in two places (the
model and the mapper) — more boilerplate than annotating one class and
using it everywhere.

## Alternatives considered

- **SQLAlchemy models as domain entities** (rejected — the explicit PRD
  §61 anti-pattern): fewer classes, but the domain layer becomes
  untestable without a session and business methods risk triggering
  lazy-loaded queries as a side effect.
- **A generic/automatic mapper (e.g. field-name reflection)** (rejected):
  works until a field is renamed independently on either side, or a value
  object needs custom (de)serialization (e.g. `Email` normalizing case) —
  explicit mapping functions make exactly this kind of logic visible and
  testable in one place.
