# Messaging

## Ports

`app.application.common.interfaces.publisher`:

```python
class Publisher(ABC):
    async def publish(self, message: OutboundMessage) -> None: ...


class Consumer(ABC):
    def register(self, event_type: str, handler: MessageHandler) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
```

The domain and application layers depend only on these — never on Redis,
Kafka, or any specific broker client.

## Default implementation: Redis Streams

`infrastructure/messaging/redis_streams.py` — chosen as the default because
it reuses the Redis dependency already required for caching/idempotency/
background jobs, avoiding a second piece of broker infrastructure in
`docker-compose.yml`, while still giving:

- **Consumer groups** (`XGROUP`/`XREADGROUP`) so multiple worker instances
  share the load without double-processing.
- **At-least-once delivery** with explicit acknowledgement (`XACK`) only
  after a handler succeeds.
- **Dead-lettering**: a message that fails 5 times
  (`_MAX_DELIVERIES` in `redis_streams.py`) is moved to a
  `<stream>:dead-letter` stream instead of being retried forever.

`RedisStreamsPublisher.publish()` is only ever called by the
`OutboxRelay` (see [`outbox.md`](outbox.md)) — application code never
publishes directly, which is what guarantees an event is never observable
externally before its transaction committed.

## In-memory implementation (tests)

`infrastructure/messaging/in_memory.py`'s `InMemoryPublisher` records every
published `OutboundMessage` in a list — used in unit/e2e tests that need to
assert "this event was published" without a real Redis.

## Swapping to Kafka or RabbitMQ

Implement `Publisher`/`Consumer` against the broker's async client
(`aiokafka`, `aio-pika`), following the shape of `RedisStreamsPublisher`/
`RedisStreamsConsumer`, then swap the instantiation in
`composition/container.py`. Nothing in `app.domain`, `app.application`, or
`app.presentation` changes. Considerations when doing so:

- **Kafka**: better fit if you need long retention, replay-from-offset, or
  very high throughput across many consumer groups reading the same topic
  independently.
- **RabbitMQ**: better fit for complex routing (topic/fanout exchanges) or
  when you need broker-side priority queues.
- **SNS+SQS** (or another cloud-managed pub/sub): reasonable if you're
  already all-in on one cloud provider and don't want to operate a broker.

Whatever you choose, keep the outbox → relay → publisher shape — the
transactional-safety guarantee it provides is independent of which broker
sits behind the `Publisher` port.

## Consuming events

`app.application.users.handlers.user_registered_integration_handler.UserRegisteredIntegrationHandler`
is the reference example: it implements `MessageHandler`, is registered
against a `Consumer` in the arq worker's `on_startup`
(`infrastructure/background_jobs/worker.py`), and reacts to `UserRegistered`
by sending a welcome email through the `NotificationSender` port. Follow
this shape for any new "when X happens elsewhere in the system, do Y" use
case — it belongs in the application layer (it's orchestration), not
infrastructure.
