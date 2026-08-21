# ADR-005: Domain-specific repositories, not generic CRUD

## Status

Accepted

## Context

A "generic repository" (`Repository[T]` with `get`, `list`, `add`,
`update`, `delete` for any entity type) looks appealing — write it once,
reuse it everywhere. In practice it tends to expose exactly the
database-shaped operations a domain shouldn't have to think in (arbitrary
`filter()` dicts, bulk updates that bypass aggregate invariants) and pushes
callers toward treating the aggregate as a bag of fields again (PRD §61,
"generic repository abuse").

## Decision

Each aggregate gets its own repository interface, defined in the domain
layer, with methods named for what the domain actually needs:

```python
class UserRepository(ABC):
    async def get_by_id(self, user_id: UserId) -> User | None: ...
    async def get_by_email(self, email: Email) -> User | None: ...
    async def list_page(self, *, offset: int, limit: int) -> tuple[list[User], int]: ...
    def add(self, user: User) -> None: ...
    async def save(self, user: User) -> None: ...
```

`get_by_email` exists because the domain has a real reason to look up a
user that way (uniqueness checking); there is no generic `find(**filters)`
escape hatch. See [`domain-driven-design.md`](../domain-driven-design.md#repository).

## Consequences

**Positive**: the interface documents exactly what persistence operations
the `User` aggregate's use cases actually need, in domain language; adding
a new query method is a deliberate, reviewed decision rather than an
implicit capability every caller already has via a generic filter API.

**Negative**: more interface methods to write per aggregate than one
shared generic interface — though in practice this is a handful of methods
per bounded context, not a large surface.

## Alternatives considered

- **Generic `Repository[T]`** (rejected — PRD §61's named anti-pattern):
  minimizes boilerplate but reintroduces exactly the "the domain just
  wraps a table" problem Clean Architecture is meant to avoid, and makes
  it easy to write a query that silently violates an aggregate invariant
  by operating on raw filters instead of aggregate methods.
- **Active Record** (the aggregate saves itself, e.g. `user.save()`)
  (rejected): couples the aggregate to persistence directly, which is the
  exact leak [ADR-004](ADR-004-sqlalchemy-isolation.md) exists to prevent.
