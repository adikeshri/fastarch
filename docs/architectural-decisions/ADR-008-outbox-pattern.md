# ADR-008: Transactional outbox for reliable event delivery

## Status

Accepted

## Context

Publishing an integration event directly from a command handler (call the
broker right after `session.commit()`, or worse, before it) creates a dual-
write problem: the database transaction and the publish call aren't atomic,
so a crash between them either loses the event or publishes one for a
change that never actually persisted. See [`outbox.md`](../outbox.md) for
the full mechanics.

## Decision

Write every domain event to an `outbox_messages` table in the *same*
database transaction as the aggregate change
(`SqlAlchemyUnitOfWork.commit()`), and publish it asynchronously from a
separate relay process (`OutboxRelay`, run as a periodic `arq` job) that
polls for unpublished rows with `SELECT ... FOR UPDATE SKIP LOCKED` and
tracks attempt count / backoff / failure state per row.

## Consequences

**Positive**: an event can never be published for a change that didn't
commit, and never silently lost if the process crashes between commit and
publish (the relay picks it up on its next poll); multiple relay instances
can run concurrently without double-publishing.

**Negative**: delivery latency is bounded by the relay's poll interval
(2s by default, configurable) rather than instantaneous; consumers must
tolerate at-least-once delivery (a crash between "publish succeeded" and
"row marked published" can redeliver) and should be idempotent on
`event_id`.

## Alternatives considered

- **Direct publish-then-commit or commit-then-publish** (rejected): the
  dual-write problem described above — no ordering avoids losing atomicity
  between two different systems.
- **Change Data Capture (CDC) off the database's write-ahead log** (e.g.
  Debezium) (not adopted as the default): a legitimate, arguably more
  "real-time" alternative that avoids polling entirely, but it requires
  operating a CDC pipeline (Kafka Connect or equivalent) as additional
  infrastructure — heavier than this template wants as a default. The
  outbox table's shape (`aggregate_id`, `event_type`, `payload`, ...) is
  compatible with adding CDC later if throughput/latency needs outgrow
  polling.
- **Two-phase commit across Postgres and the broker** (rejected): brokers
  generally don't support XA/2PC well in practice, and even where they do,
  it couples the two systems' availability tightly together.
