# Configuration

`app.infrastructure.configuration.settings.Settings` (`pydantic-settings`)
is the single source of truth for every configurable value. Nothing else in
the codebase reads `os.environ` directly.

## Loading

```python
from app.infrastructure.configuration.settings import get_settings

settings = get_settings()  # cached (@lru_cache) singleton
```

Sources, in precedence order: real environment variables > `.env` file >
field defaults. Nested groups use `env_nested_delimiter="__"`:

```bash
DATABASE__URL=postgresql+asyncpg://fastarch:fastarch@localhost:5432/fastarch
DATABASE__POOL_SIZE=10
REDIS__URL=redis://localhost:6379/0
AUTH__JWT_SECRET=...
```

See `.env.example` for the complete, documented list.

## Structure

| Group | Class | Covers |
|---|---|---|
| (root) | `Settings` | `ENVIRONMENT`, `API_PREFIX`, `PROJECT_NAME`, `DEBUG` |
| `DATABASE__*` | `DatabaseSettings` | Postgres URL, pool sizing, echo |
| `REDIS__*` | `RedisSettings` | Redis URL, max connections |
| `AUTH__*` | `AuthSettings` | JWT secret/algorithm/issuer/audience/TTL |
| `OBSERVABILITY__*` | `ObservabilitySettings` | Service name, OTLP endpoint, log level/format |
| `SECURITY__*` | `SecuritySettings` | CORS origins, trusted hosts |
| `OUTBOX_*` | (root fields) | Relay interval, batch size, max attempts |

## Environments

`Environment` (`development` / `testing` / `staging` / `production`) —
`Environment.is_production_like` gates behavior like hiding internal error
detail (see [`api.md`](api.md)) and should gate anything else environment-
sensitive you add (verbose logging, debug toolbars, permissive CORS).

## Adding a new setting

1. Add the field to the relevant settings group (or a new group if it's a
   new concern) in `settings.py`, with a sensible default.
2. Document it in `.env.example` with a placeholder/comment.
3. If it's a secret, make the default an obviously-fake value (never a
   real-looking one) and note in `.env.example` that it must be overridden.

## No secrets in version control

`.env` is gitignored; `.env.example` never contains a real value. See
[`security.md`](security.md) for the `detect-secrets` pre-commit hook that
backstops this.
