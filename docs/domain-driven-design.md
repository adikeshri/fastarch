# Domain-Driven Design

This template uses *tactical* DDD patterns — the building blocks for
modeling a rich domain — inside a single service. It does not prescribe a
*strategic* DDD process (context mapping, event storming, bounded-context
discovery workshops); that's organizational work you do before writing
code, and it's out of scope for a code template.

## Building blocks (`app.domain.shared`)

### Entity (`entity.py`)

Has identity that survives attribute changes. Equality and hashing are by
identity + type, never by attribute values:

```python
class Entity(Generic[IdType]):
    def __eq__(self, other): ...  # compares self._id, not attributes
```

### Aggregate Root (`aggregate_root.py`)

An `Entity` that is additionally the transactional consistency boundary for
a cluster of objects, and that collects domain events raised by its own
behavior:

```python
class AggregateRoot(Entity[IdType]):
    def register_event(self, event: DomainEvent) -> None: ...
    def collect_events(self) -> list[DomainEvent]: ...  # drains the buffer
```

Everything a client can do to an aggregate is expressed as a method on the
aggregate (`User.register()`, `.rename()`, `.deactivate()`) — never as
direct attribute mutation from outside. This is what prevents the "anemic
domain model" anti-pattern (PRD §61): behavior lives with the data it
protects.

Optimistic concurrency lives here too: `version` and `mark_persisted()`.
The aggregate doesn't know *how* concurrency is enforced (that's the
repository's job — see [`persistence.md`](persistence.md)), only that it
has a version.

### Value Object (`value_object.py`)

Immutable, compared by value, validates its own invariants:

```python
@dataclasses.dataclass(frozen=True)
class Email(ValueObject):
    value: str

    def _validate(self) -> None:
        if not _EMAIL_PATTERN.match(self.value):
            raise InvalidValueObject(...)
```

`Email`, `DisplayName`, and `UserId` in `app.domain.users.value_objects` are
the concrete examples. A value object should be introduced when a primitive
(a `str`, a `float`) carries domain rules of its own — "an email has a
shape", "money has a currency" — not merely to wrap every field
(over-engineering, PRD §61).

### Domain Event (`domain_event.py`)

An immutable record of something that happened:

```python
@dataclasses.dataclass(frozen=True, kw_only=True)
class UserRegistered(DomainEvent):
    email: str
    display_name: str
```

The aggregate that raises an event has *no idea* how it will be delivered —
that's the outbox's job (see [`outbox.md`](outbox.md)). This is what keeps
`User.register()` a pure, side-effect-free, trivially-unit-testable method.

### Domain Service (`app.domain.users.services.reserved_name_policy`)

Business logic that doesn't naturally belong to one aggregate instance. A
domain service takes its subject as an argument rather than owning it, and
— like everything else in the domain layer — never touches infrastructure:

```python
class ReservedDisplayNamePolicy:
    def ensure_allowed(self, display_name: DisplayName) -> None: ...
```

If a rule needs data from *another* aggregate, the application layer fetches
that data and passes it in — a domain service is not a place to sneak in a
repository call.

### Domain Exceptions (`exceptions.py`)

`DomainException` and its subtypes (`InvalidValueObject`, `InvalidState`,
`BusinessRuleViolation`, `EntityNotFound`, `ConcurrencyConflict`) are the
*only* exceptions the domain layer raises. It never raises
`fastapi.HTTPException` — see `docs/api.md` for how these map to HTTP
responses in the presentation layer, one level removed from the domain.

### Repository (`app.domain.users.repositories.user_repository`)

Defined in the domain layer, because it expresses what the aggregate needs
from persistence in *domain* terms:

```python
class UserRepository(ABC):
    async def get_by_id(self, user_id: UserId) -> User | None: ...
    async def get_by_email(self, email: Email) -> User | None: ...
```

Not `get_sqlalchemy_model()`, not a generic `find(filters: dict)` — every
method reads like a sentence about the domain. See
[`persistence.md`](persistence.md) for the SQLAlchemy implementation and
[`repository pattern ADR`](architectural-decisions/ADR-005-repository-pattern.md)
for why this isn't "generic repository abuse" (PRD §61).

## The Users bounded context as the reference example

`app.domain.users` demonstrates the full pattern end to end:

| Piece | File |
|---|---|
| Aggregate | `entities/user.py` |
| Value objects | `value_objects/{user_id,email,display_name}.py` |
| Domain events | `events/user_events.py` |
| Domain service | `services/reserved_name_policy.py` |
| Repository port | `repositories/user_repository.py` |
| Domain exceptions | `exceptions/__init__.py` |

Use it as the template when adding a new bounded context — see the
["Adding a new bounded context"](../README.md#adding-a-new-bounded-context)
checklist in the README.
