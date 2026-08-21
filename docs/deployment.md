# Deployment

## The application is stateless

The API process holds no local state — every request is fully served from
its arguments plus Postgres/Redis. This means it's safe to run any number
of replicas behind a load balancer and scale horizontally by adding
instances; nothing needs sticky sessions or instance-affinity.

The worker process (`arq`, see [`background-jobs.md`](background-jobs.md))
is likewise horizontally scalable — the outbox relay's
`FOR UPDATE SKIP LOCKED` query and arq's own job-claiming both make it safe
to run multiple worker instances concurrently.

## Container image

`Dockerfile` — multi-stage:

1. **builder**: installs dependencies with `uv sync --frozen` into
   `/app/.venv` (the *same* path as the runtime stage's `WORKDIR`, which
   matters — see the comment in the Dockerfile; console-script shebangs
   bake in an absolute interpreter path at install time, so building and
   running from different paths breaks `alembic`/`arq`/`uvicorn`).
2. **runtime**: `python:3.13-slim`, no build toolchain, runs as a non-root
   `app` user, `HEALTHCHECK` against `/health/live`.

```bash
make docker-build     # docker compose build
make docker-up        # postgres + redis + migrate (once) + app + worker
make docker-down       # tear down, including the postgres volume
```

## Migrations in production

Run `alembic upgrade head` as a **separate step** before the new app
version starts serving traffic — `docker-compose.yml`'s `migrate` service
(`depends_on: service_completed_successfully`) models this: it's a
one-shot container that must exit 0 before `app`/`worker` start. In a
Kubernetes-style deployment, this is a `Job` or an init container, not
something the API process does on its own startup (which would race
multiple replicas trying to migrate simultaneously).

Keep migrations backward-compatible with the *previous* running version
during a rolling deploy — see [`persistence.md`](persistence.md#migrations).

## Health checks

- **`/health/live`** — liveness. Only proves the process is up and
  responding; deliberately does **not** touch Postgres/Redis (PRD §39), so
  a slow/unreachable database can't get an otherwise-healthy pod killed and
  restarted in a loop by the orchestrator.
- **`/health/ready`** — readiness. Checks both Postgres (`SELECT 1`) and
  Redis (`PING`); returns 503 if either is unreachable. This is what should
  gate load-balancer/orchestrator traffic routing — don't send requests to
  a pod that can't reach its dependencies.

Wire liveness/readiness probes to these two paths respectively in your
orchestrator of choice (Kubernetes `livenessProbe`/`readinessProbe`, ECS
health checks, etc.) — never point both at the same path.

## Graceful shutdown

`main.py`'s `_lifespan` context manager calls `shutdown_container()` on
shutdown, which releases every resource `build_container()` opened: the
arq Redis pool, the plain Redis client, and the SQLAlchemy engine (which
closes its connection pool). `Dockerfile`'s `ENTRYPOINT` runs `uvicorn`
directly (not wrapped in a shell), so `SIGTERM` reaches the process
directly and triggers this shutdown path rather than being swallowed by an
intermediate shell process.

## Configuration

Every environment-specific value is env-driven (see
[`configuration.md`](configuration.md)) — the same image runs in every
environment; only environment variables differ. Set `ENVIRONMENT=production`
and override `AUTH__JWT_SECRET`, `SECURITY__CORS_ALLOW_ORIGINS`,
`SECURITY__TRUSTED_HOSTS`, and both `DATABASE__URL`/`REDIS__URL` per
[`security.md`](security.md).

## Logging in production

Set `OBSERVABILITY__JSON_LOGS=true` (the default) so logs are structured
JSON, ready for any log-aggregation pipeline that ingests JSON lines
(CloudWatch, Datadog, Loki, ELK, ...). Point `OBSERVABILITY__OTLP_ENDPOINT`
at your OpenTelemetry collector for traces/metrics — see
[`observability.md`](observability.md).

## Performance defaults

- Connection pooling is on by default (`DatabaseSettings.pool_size`/
  `max_overflow`, `pool_pre_ping=True`) — tune per environment's expected
  concurrency.
- Pagination is capped at `limit<=100` (`MAX_PAGE_SIZE`) so a client can't
  force an unbounded query.
- `httpx`/broker clients used inside `infrastructure/external/` adapters
  should reuse a single client instance (connection pooling) rather than
  constructing one per call — follow the pattern already in
  `SmtpEmailSender` (one long-lived settings object, thread-offloaded
  per-call) when adding a new adapter.
