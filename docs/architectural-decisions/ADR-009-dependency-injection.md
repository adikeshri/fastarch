# ADR-009: A composition root, not a service locator or FastAPI-wide DI

## Status

Accepted

## Context

Something has to construct `SqlAlchemyUnitOfWork`, `RedisCache`,
`JwtTokenService`, and wire them to the ports the application layer
depends on. FastAPI's own `Depends()` system is tempting to use for this
throughout the codebase, but doing so ties construction of *business*
collaborators to a web framework, and passing a single catch-all container
object into every handler risks "service locator abuse" (PRD §61) — a
handler that receives a generic container can reach for anything, defeating
the point of declaring its actual dependencies.

## Decision

`app.composition.container.Container` is built once, in `main.py`'s
lifespan, by `build_container(settings)` — the *only* function in the
codebase allowed to import concrete infrastructure classes and instantiate
them against abstract ports. It builds the full handler map and hands a
single `Mediator` to the FastAPI app's state.

FastAPI's `Depends()` is used only at the true presentation boundary
(`presentation/api/dependencies/`) — thin glue that pulls already-built
objects (the `Mediator`, the current `AuthContext`) out of
`request.app.state.container`, never constructs infrastructure itself. A
handler's constructor declares exactly what it needs
(`uow_factory: UnitOfWorkFactory`, not `container: Container`) — see
[`application-layer.md`](../application-layer.md).

## Consequences

**Positive**: every handler's dependencies are visible in its constructor
signature, making unit tests trivial (pass a fake — see
`tests/unit/application/users/fakes.py` — no framework needed); swapping
an infrastructure adapter is a one-line change in
`composition/container.py`, isolated from everything that depends on the
port it implements.

**Negative**: adding a new handler means touching one more place
(`container.py`'s handler map) beyond the handler and command/query files
themselves — a small amount of ceremony traded for explicitness.

## Alternatives considered

- **A general-purpose DI framework** (`dependency-injector`,
  `python-inject`, etc.) (rejected): adds a dependency and its own
  conventions on top of what a single, explicit `build_container()`
  function already does clearly in plain Python; a template shouldn't
  impose a DI framework choice on every project built from it.
- **FastAPI `Depends()` everywhere, including inside handlers** (rejected):
  couples application-layer construction to FastAPI, and handlers become
  untestable without a FastAPI request context.
- **Passing the whole `Container` into every handler** (rejected — the
  service-locator anti-pattern): defeats explicit dependencies; a handler
  could reach for anything in the container regardless of what it actually
  declared needing.
