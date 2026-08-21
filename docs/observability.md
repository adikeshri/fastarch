# Observability

## Structured logging

`structlog`, configured in `infrastructure/observability/logging.py`:

- JSON output when `OBSERVABILITY__JSON_LOGS=true` (the default; disable
  for a readable console renderer in local dev), plain console otherwise.
- Every log line automatically carries whatever's bound into
  `structlog.contextvars` for the current request — see correlation IDs,
  below.
- A `_redact_sensitive` processor strips `password`, `token`,
  `authorization`, `secret`, `access_token`, `refresh_token` keys from
  every log line, so a developer binding the wrong dict into a log call
  can't leak a credential. Never log raw request/response bodies that
  might contain these regardless — redaction is a safety net, not a
  license.

```python
logger = structlog.get_logger(__name__)
logger.info("request.started", request=type(request).__name__, user_id=...)
```

`LoggingBehavior` (the pipeline behavior, not the middleware) logs the
start/completion/failure of every command/query dispatch this way — see
[`application-layer.md`](application-layer.md).

## Correlation IDs

`presentation/api/middleware/correlation.py`'s `CorrelationIdMiddleware`:

1. Reads `X-Correlation-ID` from the incoming request, or generates one.
2. Binds it into `structlog.contextvars` for the request's lifetime.
3. Echoes it back on the response (`X-Correlation-ID` header) and includes
   it as `trace_id` in every RFC 7807 error body (see
   [`api.md`](api.md)) — so a user-reported error can be grepped straight
   out of the logs.

`presentation/api/dependencies/mediator.get_request_context` carries the
same id into `RequestContext.correlation_id`, so it's available to every
command/query handler too, not just HTTP middleware.

## Request logging

`RequestLoggingMiddleware` logs one structured line per HTTP request
(method, path, status code, duration) and sets an `X-Response-Time-Ms`
response header.

## OpenTelemetry

`infrastructure/observability/tracing.py`:

```python
configure_observability(settings.observability)  # tracer/meter providers
instrument_fastapi(app)  # HTTP spans
instrument_sqlalchemy(engine)  # DB-call spans
```

Exporters are OTLP-over-HTTP and only activate when
`OBSERVABILITY__OTLP_ENDPOINT` is set — without a collector configured,
spans/metrics are still created (so instrumentation code paths are always
exercised) but simply aren't exported anywhere. Point it at any
OTLP-compatible collector (the OpenTelemetry Collector, Grafana Tempo/
Mimir, Honeycomb, ...).

`OBSERVABILITY__TRACES_ENABLED` / `OBSERVABILITY__METRICS_ENABLED` toggle
each independently.

## What's instrumented out of the box

- **HTTP requests** — via `FastAPIInstrumentor`.
- **Database calls** — via `SQLAlchemyInstrumentor`, attached to the sync
  engine underlying the async one (`engine.sync_engine`).

Add outbound HTTP client instrumentation
(`opentelemetry-instrumentation-httpx`) the same way if/when a real
external HTTP integration is added under `infrastructure/external/`.

## Health checks

See [`deployment.md`](deployment.md#health-checks) — liveness and readiness
are a related but distinct concern from tracing/metrics.

## What never gets logged

Passwords, tokens, credentials, secrets, or raw JWTs — enforced by the
redaction processor above, and by convention: never pass a raw
`Authorization` header value or a plaintext password into a `logger.info(...)`
call, redaction is the last line of defense, not the first.
