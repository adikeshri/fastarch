# The Outbox Pattern

## The problem it solves

Without it, "save the aggregate" and "publish the event" are two separate
operations against two separate systems (Postgres, the broker) with no
shared transaction. Either can fail independently:

- Commit the DB row, then crash before publishing → the event is lost
  forever, even though the change it describes really happened.
- Publish first, then the DB transaction rolls back → consumers react to
  something that never actually happened.

The outbox pattern makes "the change happened" and "the event *will* be
published" a single atomic fact, by writing the event to a table in the
same transaction as the aggregate change, and publishing it out-of-band
afterward.

## How it works here

```
Application transaction (SqlAlchemyUnitOfWork)
    │
    ├── UPDATE/INSERT on the aggregate's table   (SqlAlchemyUserRepository)
    │
    └── INSERT into outbox_messages               (UnitOfWork.commit())
    │
    ▼
Commit atomically — both rows exist, or neither does
    │
    ▼
OutboxRelay (a periodic arq cron job, every 2s by default)
    │  SELECT ... WHERE status IN (pending, failed) FOR UPDATE SKIP LOCKED
    ▼
Publisher.publish(message)         → Redis Streams (or Kafka/RabbitMQ, swappable)
    │
    ├── success → status = published, processed_at = now()
    └── failure → status = failed, attempt_count += 1,
                   available_at = now() + backoff, last_error recorded
```

1. **Never publish before commit.** `UserRepository.add()`/`.save()` collect
   an aggregate's `domain_events` into a list shared with the owning
   `UnitOfWork`; nothing is written to the outbox table until
   `UnitOfWork.commit()` runs — and that INSERT is in the *same*
   `AsyncSession`/transaction as the aggregate's own INSERT/UPDATE
   (`infrastructure/persistence/unit_of_work.py`).
2. **The relay is separate and asynchronous.** `OutboxRelay.relay_once()`
   (`infrastructure/persistence/outbox/relay.py`) polls for
   `pending`/`failed` rows whose `available_at` has passed, locks them with
   `SELECT ... FOR UPDATE SKIP LOCKED` (so multiple relay instances can run
   concurrently without double-publishing the same row), and publishes each
   through the `Publisher` port.
3. **Retry with backoff, not forever.** A failed publish gets exponential
   backoff (`5s * 2^attempt`, capped) via `available_at`, and stops being
   retried once `attempt_count >= max_attempts` (`OUTBOX_MAX_ATTEMPTS`,
   default 10) — it stays `failed` in the table for operator triage instead
   of looping forever or silently vanishing.
4. **Idempotent processing.** Consumers should still be idempotent on
   `event_id` (the outbox row's primary key) even though the relay itself
   won't double-publish under normal operation — "at least once" delivery
   is the realistic guarantee across a crash between "publish succeeded"
   and "row marked published".

## The schema

`infrastructure/persistence/outbox/model.py`'s `OutboxModel`
(`outbox_messages` table): `aggregate_type`, `aggregate_id`, `event_type`,
`payload` (JSONB), `status`, `attempt_count`/`max_attempts`, `last_error`,
`created_at`/`processed_at`/`available_at`. Indexed on `(status,
created_at)` for the relay's poll query and on `aggregate_id` for
debugging "what happened to this aggregate".

## Where it plugs in

The relay's `Publisher` is Redis Streams by default
(`infrastructure/messaging/redis_streams.py`) — see
[`messaging.md`](messaging.md) for swapping it to Kafka/RabbitMQ. The relay
itself runs as an `arq` cron job (`infrastructure/background_jobs/worker.py`);
see [`background-jobs.md`](background-jobs.md).

## Adding outbox support to a new aggregate

Nothing extra to do — any aggregate that extends `AggregateRoot` and is
saved through a repository whose `add()`/`save()` forwards
`aggregate.collect_events()` into the `UnitOfWork`'s event sink gets outbox
delivery automatically. Follow the pattern in
`SqlAlchemyUserRepository.add()`/`.save()`.
