# Background Jobs

FastAPI's `BackgroundTasks` is **not** used as the general-purpose job
system here — it runs in-process, is lost on crash/restart/deploy, and
gives no retry, scheduling, or observability. It's fine for genuinely
fire-and-forget work that's acceptable to lose (e.g. a non-critical cache
warm), but nothing this template relies on for correctness goes through it.

## The port

```python
class JobQueue(ABC):
    async def enqueue(
        self,
        job_name: str,
        *args,
        job_id: str | None = None,
        defer_by: timedelta | None = None,
        **kwargs,
    ) -> str: ...
```

(`app.application.common.interfaces.job_queue`) — application code enqueues
by name; it never imports the worker library directly. `job_id` makes
enqueueing idempotent (a second call with the same id while the first job
is still pending is a no-op) — useful when a command handler wants to
schedule follow-up work exactly once even under retries.

## Default implementation: arq

Chosen over Celery because it's async-native (no thread pool bridging into
the async handlers this codebase is built around) and Redis-based (reusing
the Redis dependency already required elsewhere, rather than adding a
second broker).

- `infrastructure/background_jobs/arq_job_queue.py` — `ArqJobQueue`,
  implementing the `JobQueue` port via `arq.ArqRedis.enqueue_job`.
- `infrastructure/background_jobs/worker.py` — the actual worker process
  entrypoint: `arq app.infrastructure.background_jobs.worker.WorkerSettings`.
  Registers job functions (`relay_outbox`) and a periodic cron job (the
  outbox relay ticks every 2 seconds by default — see
  [`outbox.md`](outbox.md)), plus wires up the messaging `Consumer` in
  `on_startup`/`on_shutdown` (see [`messaging.md`](messaging.md)).

Job functions are plain async callables that build whatever infrastructure
they need from `ctx` (populated in `on_startup`) — the worker process is
independent of the web process and does **not** go through
`composition/container.py`'s `Container`, because the API and the worker
scale independently (PRD §64/§74: the API stays stateless; workers scale
on their own).

Run it locally:

```bash
make worker
# or, inside docker compose, the `worker` service does this automatically
```

## Adding a new job

1. Write an async function `async def my_job(ctx: dict, ...) -> ...` in
   (or imported by) `infrastructure/background_jobs/worker.py`.
2. Add it to `WorkerSettings.functions`.
3. Enqueue it from application code via the `JobQueue` port:
   `await job_queue.enqueue("my_job", some_arg)`.
4. For a recurring job, add a `cron(my_job, ...)` entry to
   `WorkerSettings.cron_jobs`.

## Retries and failure handling

arq retries a job automatically on unhandled exception (configurable
per-job via `max_tries`/`retry_delay` in its `@task` decoration or
`enqueue_job` call — see arq's own docs for the exact knobs). Distinguish:

- **Transient failures** (a dropped DB connection, a broker timeout) —
  fine to retry with backoff.
- **Permanent failures** (malformed input that will never succeed) —
  should not retry; log and move on, or route to a dead-letter mechanism
  (the outbox relay's own `max_attempts`/`available_at` backoff, described
  in [`outbox.md`](outbox.md), is the reference pattern for this
  distinction).
- **Business failures** (a domain exception like `EmailAlreadyRegistered`)
  are not infrastructure failures at all — don't retry them; they'll fail
  identically every time.

## Swapping to a different worker system

Implement `JobQueue` against Celery/Dramatiq/RQ's client API, register the
job functions with that system's worker process instead of arq's
`WorkerSettings`, and swap the instantiation in
`composition/container.py`. Application code that only depends on
`JobQueue.enqueue()` doesn't change.
