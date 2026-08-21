# ADR-007: Aggregates raise events; they never dispatch them

## Status

Accepted

## Context

An aggregate's behavior often needs to notify the rest of the system that
something happened (`UserRegistered`) — but if the aggregate itself calls
into a message bus or an event dispatcher to do so, it immediately depends
on infrastructure, breaking the dependency rule ([ADR-001](ADR-001-clean-architecture.md))
and making the aggregate's methods impossible to unit-test without mocking
a bus.

## Decision

`AggregateRoot.register_event()` only appends to an in-memory list;
`collect_events()` drains it. `User.register()` calls
`self.register_event(UserRegistered(...))` and returns — it has no idea
whether that event will ever be published, retried, or land in a broker at
all. See [`domain-driven-design.md`](../domain-driven-design.md#domain-event-domain_eventpy).

Dispatch is entirely an infrastructure/application concern:
`SqlAlchemyUserRepository.add()`/`.save()` collect the events into a buffer
shared with the owning `UnitOfWork`; `UnitOfWork.commit()` turns them into
outbox rows in the same transaction as the aggregate change (see
[ADR-008](ADR-008-outbox-pattern.md)).

## Consequences

**Positive**: `test_user_aggregate.py` asserts on `user.domain_events`
directly, with no mock message bus, no database, no async I/O — a domain
event is just data on a list. Delivery mechanics (outbox → relay →
broker → consumer) can change completely without `User.register()`
changing a single line.

**Negative**: it's possible to forget to route a new aggregate's events
into a repository's event sink and silently lose them — mitigated by every
repository following the same `add()`/`save()` pattern as
`SqlAlchemyUserRepository`, which is the template to copy for a new
bounded context.

## Alternatives considered

- **Aggregate calls an injected event bus directly** (rejected): couples
  the aggregate constructor/methods to an infrastructure dependency,
  defeating framework independence and complicating every domain unit
  test.
- **A global/static event dispatcher** (rejected): global mutable state,
  hard to test in isolation, and makes "was this event actually published
  as part of *this* transaction" impossible to answer without additional
  bookkeeping — exactly what the outbox pattern (transactional by
  construction) solves properly instead.
