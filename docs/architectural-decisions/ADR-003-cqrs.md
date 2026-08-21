# ADR-003: CQRS at the application layer

## Status

Accepted

## Context

Read and write operations against the same aggregate often have very
different scaling, caching, and consistency needs — a `GetUser` query might
benefit from a cache or a read replica, while `RegisterUser` needs a
strict, consistent write path. Sharing one "service" class or one handler
per aggregate for both tends to couple these needs together and makes it
awkward to evolve one without touching the other.

## Decision

Model every use case as a `Command` (state-changing) or `Query`
(read-only) — small, immutable dataclasses in
`app.application.<context>.{commands,queries}` — each with exactly one
dedicated handler, dispatched through a `Mediator`
(`app.application.common.mediator`). See
[`application-layer.md`](../application-layer.md).

This is CQRS at the *application/handler* level, not full CQRS with
separate read/write data stores or eventual consistency between them — the
Users example uses one Postgres schema for both. Nothing prevents
introducing a separate read model later (a materialized view, a
denormalized projection updated by consuming the aggregate's own outbox
events) for a query that needs it, without touching the command side.

## Consequences

**Positive**: `ListUsersHandler` and `RegisterUserHandler` can diverge
completely in implementation without affecting each other; the pipeline
behaviors (validation, authorization, ...) apply uniformly to both because
they operate on the shared `Request` base type, not on hand-rolled
per-method logic; testing a query handler never accidentally exercises
write-path code.

**Negative**: more files than "one method per operation on a service
class" — a simple CRUD-shaped operation still gets a command file, a
handler file, and a composition-root registration.

## Alternatives considered

- **A single `UserService` class with one method per operation**
  (rejected): works fine at small scale, but as an aggregate accumulates
  operations, the class becomes a god object (PRD §61) mixing read and
  write concerns, and it's harder to apply cross-cutting behavior
  (authorization, idempotency) uniformly.
- **Full CQRS with separate read/write databases** (rejected as the
  default): real complexity (eventual consistency, a second data store to
  keep in sync) that most services don't need from day one. The pipeline/
  handler-per-use-case structure here doesn't preclude adding it later for
  a specific query that needs it.
