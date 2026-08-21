# ADR-002: Tactical DDD boundaries, not strategic process

## Status

Accepted

## Context

Domain-Driven Design covers both a *strategic* process (context mapping,
event storming, discovering bounded contexts through collaboration with
domain experts) and a *tactical* toolkit (entities, aggregates, value
objects, domain events, repositories). A code template can't prescribe the
former — it's organizational work specific to a real domain — but it can
and should provide the latter as reusable, well-demonstrated building
blocks.

## Decision

Provide the tactical DDD building blocks in `app.domain.shared` (`Entity`,
`AggregateRoot`, `ValueObject`, `DomainEvent`, the domain exception
hierarchy), and demonstrate them fully in one bounded context
(`app.domain.users`). Each bounded context is a self-contained package
under `app.domain.<context>` with its own `entities/`, `value_objects/`,
`events/`, `repositories/`, `services/`, `exceptions/` — see
[`domain-driven-design.md`](../domain-driven-design.md).

The aggregate boundary decision for `User`: registration, renaming, and
deactivation are all operations on a single `User` aggregate because they
share one consistency boundary (a user's own state) and there's no
sub-entity within a user that needs independent identity or its own
transaction boundary in this example.

## Consequences

**Positive**: a new bounded context has an unambiguous template to copy
(see the README's "Adding a new bounded context" checklist); aggregate
invariants live in exactly one place and can't be bypassed by mutating
state from outside.

**Negative**: tactical DDD adds ceremony (a value object for `Email`
instead of a bare `str`) that's not justified for every field — the
guidance in `domain-driven-design.md` is explicit that value objects should
represent real domain rules, not wrap every primitive (PRD §61,
over-engineering).

## Alternatives considered

- **Anemic domain model** (data classes + separate "service" classes
  containing all behavior) — rejected as the specific anti-pattern PRD §61
  calls out; it defeats the purpose of having a domain layer at all, since
  business rules end up unenforceable from outside the aggregate's own
  methods.
- **One giant `models.py` per bounded context** instead of `entities/`,
  `value_objects/`, `events/` subpackages — rejected; splitting by
  building-block type makes the pattern legible at a glance and matches
  the reference structure a new contributor can pattern-match against.
