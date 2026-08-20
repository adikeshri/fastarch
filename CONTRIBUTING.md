# Contributing

## Setup

```bash
uv sync
make precommit
make docker-up
make migrate
```

## Before opening a PR

```bash
make format
make lint
make typecheck
make lint-arch
make test
```

All of the above run in CI (`.github/workflows/pr.yml`); running them
locally first avoids a slow feedback loop.

## Ground rules

- Respect the dependency rule (`docs/dependency-rules.md`). If
  `make lint-arch` fails, that's not a lint nit — it's the whole point of
  this template.
- New bounded contexts follow the checklist in `docs/README` under "Adding
  a new bounded context".
- Prefer adding a test at the lowest layer that can express the behavior
  (domain unit test over an integration test over an e2e test).
- Schema changes need a migration, and the migration's `downgrade()` should
  actually work — CI checks `upgrade → downgrade → upgrade`.
- Significant architectural choices get an ADR (`docs/architectural-decisions/`).

## Commit style

Small, focused commits. Explain the *why* in the body when it isn't obvious
from the diff.
