# Infrastructure

Everything under `app.infrastructure` is a concrete implementation of a port
defined in `app.application.common.interfaces` (or, for the repository, in
`app.domain`). Nothing outside `app.infrastructure` and
`app.composition` should import these modules directly.

| Port | Interface | Implementation |
|---|---|---|
| Persistence | `UnitOfWork`, `UserRepository` | `persistence/unit_of_work.py`, `persistence/repositories/sqlalchemy_user_repository.py` |
| Caching | `Cache` | `caching/redis_cache.py` |
| Idempotency | `IdempotencyStore` | `caching/redis_idempotency_store.py` |
| Messaging | `Publisher`, `Consumer` | `messaging/redis_streams.py` (prod), `messaging/in_memory.py` (tests) |
| Background jobs | `JobQueue` | `background_jobs/arq_job_queue.py` |
| Password hashing | `PasswordHasher` | `authentication/password_hasher.py` (argon2) |
| Notifications | `NotificationSender` | `external/email/{console,smtp}_email_sender.py` |
| Auth token verification | — (not a port; a concrete service) | `authentication/jwt.py` |

## Swapping an implementation

Because everything above is a port, swapping the concrete adapter is a
one-line change in `composition/container.py`. Examples:

- **Messaging**: replace `RedisStreamsPublisher`/`RedisStreamsConsumer` with
  a Kafka or RabbitMQ adapter implementing `Publisher`/`Consumer`
  (`app.application.common.interfaces.publisher`) — see
  [`messaging.md`](messaging.md).
- **Background jobs**: replace `ArqJobQueue` with a Celery-backed adapter
  implementing `JobQueue` — see [`background-jobs.md`](background-jobs.md).
- **Notifications**: replace `ConsoleEmailSender` with `SmtpEmailSender` (or
  a provider SDK-backed adapter) — both implement `NotificationSender`, and
  `smtplib` never leaks outside `infrastructure/external/email/`.

## External service isolation

`infrastructure/external/` is the pattern for any third-party integration
(email, payments, identity providers, ...): the client library
(`smtplib`, `httpx`, a vendor SDK) is imported *only* inside that adapter
module, never elsewhere. `SmtpEmailSender` is the reference example —
`smtplib` appears nowhere else in the codebase, and `test_layers.py` would
catch it if it did (SMTP isn't in the forbidden-import list, but the same
principle is enforced by code review + the adapter pattern for anything
that should stay isolated).

## Observability infrastructure

`infrastructure/observability/`:

- `logging.py` — `structlog` configuration: JSON in production-like
  environments, redaction of sensitive keys, correlation-id injection via
  contextvars. See [`observability.md`](observability.md).
- `tracing.py` — OpenTelemetry `TracerProvider`/`MeterProvider` setup with an
  optional OTLP exporter, plus FastAPI/SQLAlchemy auto-instrumentation
  hooks.

## Configuration

`infrastructure/configuration/settings.py` — see
[`configuration.md`](configuration.md) for the full reference.

## Authorization primitives

`infrastructure/authorization/policies.py` holds the role→permission table
and a `can_act_on_own_resource()` helper for "owner or has an override
permission" checks — used explicitly by handlers that need resource-level
authorization beyond what `AuthorizationBehavior`'s `required_permission`
check alone can express. See [`security.md`](security.md).
