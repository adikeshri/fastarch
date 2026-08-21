# ADR-001: Clean Architecture as the foundational structure

## Status

Accepted

## Context

A production backend service needs to survive changes that are much more
common than they first appear: swapping a database, adding a second API
version, replacing a message broker, or simply making the domain testable
without booting the whole stack. A typical "FastAPI + SQLAlchemy models +
routes that do everything" layout couples business rules to the web
framework and the ORM so tightly that none of these changes are
straightforward, and unit-testing business logic requires a running
database.

## Decision

Structure the codebase in four concentric layers — domain, application,
infrastructure, presentation — plus a composition root, with the
dependency rule enforced by tooling (`import-linter`, see
[`dependency-rules.md`](../dependency-rules.md)), not just documentation:

- **Domain** has zero dependencies on anything outside itself.
- **Application** depends only on domain, expressed through ports it
  defines (`app.application.common.interfaces`).
- **Infrastructure** implements those ports; the inner layers never know
  it exists.
- **Presentation** depends on application (and domain DTOs/value types
  where convenient); it never reaches around application into
  infrastructure.
- **Composition** is the only place concrete infrastructure is
  instantiated and wired to abstract ports.

## Consequences

**Positive**: the domain and application layers are unit-testable with no
infrastructure (`tests/unit/`, well under a second to run); swapping any
infrastructure adapter (see [ADR-009](ADR-009-dependency-injection.md)) is
a change confined to `composition/container.py`; a new developer has one
obvious place to put any given piece of logic.

**Negative**: more files and more indirection than a flat structure —
registering a new use case touches a command/query, a handler, a route,
and a composition-root entry, instead of just a route function. This is
the tradeoff Clean Architecture explicitly makes, and it pays off past a
fairly small size (a handful of bounded contexts); for a genuinely
throwaway prototype, it's more structure than needed.

## Alternatives considered

- **A flat "routes + models" layout** (rejected): fastest to start, but
  business logic ends up scattered across route handlers and ORM model
  methods with no enforced boundary, and testing requires a database from
  day one.
- **Hexagonal/Ports-and-Adapters as a separate pattern** (not really an
  alternative — adopted as a complement): the port/adapter vocabulary
  (`UnitOfWork`, `Publisher`, `Cache` as ports; SQLAlchemy/Redis
  implementations as adapters) is used throughout, layered inside Clean
  Architecture's four rings rather than as a competing structure.
