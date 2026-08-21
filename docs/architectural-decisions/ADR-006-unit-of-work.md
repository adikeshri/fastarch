# ADR-006: Explicit Unit of Work, owned by the handler

## Status

Accepted

## Context

A use case often touches more than one repository call and must commit or
roll back as a single atomic transaction. Two common approaches: (a) an
implicit ambient transaction managed by a pipeline behavior wrapping every
command, or (b) an explicit `UnitOfWork` object the handler opens and
commits itself.

## Decision

`app.application.common.interfaces.unit_of_work.UnitOfWork` is an explicit
async context manager, implemented by `SqlAlchemyUnitOfWork`
(`app.infrastructure.persistence.unit_of_work`). A handler owns its
transaction boundary visibly:

```python
async with self._uow_factory() as uow:
    user = await uow.users.get_by_id(user_id)
    user.rename(new_name)
    await uow.users.save(user)
    await uow.commit()
    return UserDTO.from_domain(user)
```

There is deliberately **no** `TransactionBehavior` in the Mediator pipeline
(see [`application-layer.md`](../application-layer.md#why-theres-no-transactionbehavior))
— transaction management is a named, visible concept at the call site, not
an implicit cross-cutting concern. `__aexit__` rolls back automatically on
any unhandled exception, so a handler that raises before calling
`commit()` never leaves a half-applied change.

On `commit()`, the Unit of Work also writes every domain event collected
during the transaction to the outbox, in the same database transaction —
see [ADR-008](ADR-008-outbox-pattern.md).

## Consequences

**Positive**: the transaction boundary is visible in every handler, not
hidden in framework machinery; query handlers naturally never call
`commit()` and don't need a no-op transaction wrapper; the outbox write and
the aggregate write are trivially guaranteed to be atomic because they go
through the exact same session.

**Negative**: every handler repeats the `async with self._uow_factory():`
boilerplate (a few lines) rather than getting it "for free" from the
pipeline.

## Alternatives considered

- **Implicit transaction pipeline behavior** (rejected): would need to
  either open a transaction for every request (including read-only
  queries, wasted overhead) or introspect whether a request is a `Command`
  to decide — either way, it hides *when* a transaction starts/ends from
  the code that actually knows, which repositories it touches and in what
  order.
- **One shared, request-scoped session injected everywhere** (rejected):
  works in frameworks with a request-scoped DI container by convention
  (e.g. some ASP.NET Core setups), but makes it easy for unrelated code
  paths to accidentally share transactional state; an explicit factory per
  handler avoids that entirely.
