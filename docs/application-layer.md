# Application Layer

The application layer orchestrates use cases. It does not contain business
invariants — those live in the domain (`app.domain`). What it *does* own:
transaction boundaries, repository coordination, authorization/validation
enforcement, and translating between domain objects and DTOs.

## CQRS: Commands and Queries

Every use case is a small, immutable `Command` (write) or `Query` (read)
dataclass with exactly one dedicated handler (`app.application.common.messages`):

```python
class Request(ABC, Generic[TResult]):
    required_permission: ClassVar[str | None] = None

    def validate(self) -> dict[str, list[str]]: ...


class Command(Request[TResult], ABC): ...


class Query(Request[TResult], ABC): ...
```

```python
@dataclass(frozen=True)
class RegisterUserCommand(Command[UserDTO]):
    email: str
    display_name: str

    def validate(
        self,
    ) -> dict[str, list[str]]: ...  # application-level validation, distinct from domain invariants
```

Reads and writes never share a handler, so they can evolve independently —
`ListUsersHandler` could switch to a read replica or a denormalized
projection table tomorrow without `RegisterUserHandler` changing at all.

## The Mediator and pipeline behaviors

`app.application.common.mediator.Mediator` dispatches a request to its
handler through an ordered chain of `PipelineBehavior`s — a
MediatR-style pipeline, expressed as Python function composition rather
than reproducing MediatR's API:

```python
mediator = Mediator(
    handlers={RegisterUserCommand: RegisterUserHandler(...), ...},
    behaviors=[
        LoggingBehavior(),
        PerformanceBehavior(),
        ValidationBehavior(),
        AuthorizationBehavior(),
        IdempotencyBehavior(idempotency_store),
    ],
)
result = await mediator.send(command, request_context)
```

Each behavior wraps the next step and decides whether/how to call it:

| Behavior | Responsibility |
|---|---|
| `LoggingBehavior` | Structured start/complete/failed log lines, bound with correlation id |
| `PerformanceBehavior` | Warns on slow requests (>500ms by default) |
| `ValidationBehavior` | Runs `request.validate()`, raises `ValidationException` on errors |
| `AuthorizationBehavior` | Enforces `request.required_permission` against the caller's `AuthContext` |
| `IdempotencyBehavior` | Short-circuits a replayed request carrying the same `Idempotency-Key` |

Composing them is a constructor argument — reorder, add, or remove a
behavior in `composition/container.py` without touching any handler.

### Why there's no `TransactionBehavior`

Transaction management is a *named, first-class* concept here (the Unit of
Work — see [`persistence.md`](persistence.md)), not folded into the generic
pipeline. A handler explicitly owns its transaction boundary:

```python
async def handle(self, request: Request[UserDTO]) -> UserDTO:
    async with self._uow_factory() as uow:
        ...
        await uow.commit()
        return UserDTO.from_domain(user)
```

This is deliberate and matches the "Unit of Work" pattern from *Architecture
Patterns with Python* (Percival & Gregory) rather than an implicit
ambient-transaction pipeline step: it makes the transaction boundary visible
at the call site, and it means query handlers (which never call `commit()`)
don't need a no-op transaction wrapper. See
[ADR-006](architectural-decisions/ADR-006-unit-of-work.md).

## DTOs

`app.application.users.dto.user_dto.UserDTO` is a plain, frozen dataclass —
not a Pydantic model, not the domain `User` aggregate, not an HTTP schema.
Presentation-layer schemas (`app.presentation.api.schemas`) map DTOs to JSON;
the application layer never serializes anything itself. See
[`docs/api.md`](api.md) for the full serialization chain.

`app.application.common.dto`:

- `Page[T]` / `PageRequest` — offset pagination, framework-free (PRD §41).
- `CommandResult[T]` — uniform envelope for command results where a handler
  needs to distinguish "the result of a write" from a raw DTO.

## Adding a new command or query

1. Add the `Command`/`Query` dataclass under `application/<context>/commands`
   or `queries`, with a `validate()` override if it needs application-level
   checks.
2. Add a DTO if the result shape doesn't already exist.
3. Add a handler under `application/<context>/handlers` that takes a
   `UnitOfWorkFactory` (and anything else it needs) in its constructor.
4. Register the handler in `composition/container.py`'s handler map.
5. Add a route in `presentation/api/v1/<context>` that builds the
   command/query from the HTTP request and calls `mediator.send(...)`.
6. Unit-test the handler against `FakeUnitOfWork`
   (`tests/unit/application/<context>/fakes.py`) — no infrastructure needed.

See also: [`docs/persistence.md`](persistence.md) for the `UnitOfWork`
contract, [`docs/security.md`](security.md) for how `AuthContext` and
`required_permission` fit together, and
[ADR-003](architectural-decisions/ADR-003-cqrs.md) for why CQRS at all.
