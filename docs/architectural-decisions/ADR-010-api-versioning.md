# ADR-010: URL-path API versioning, isolated to presentation

## Status

Accepted

## Context

An API will eventually need a breaking change that some clients aren't
ready for. The versioning *mechanism* (URL path, header, content
negotiation) is a transport/presentation concern; it should not leak into
how the application or domain layer thinks about a use case — a
`RegisterUserCommand` shouldn't know or care whether it was reached via
`/v1` or `/v2`.

## Decision

Version in the URL path: every route lives under `/api/v1/...`
(`presentation/api/v1/router.py`, mounted with `api_prefix` in `main.py`).
A future `/api/v2` is a new `presentation/api/v2/` package mounted
alongside `v1` — see [`api.md`](../api.md#versioning). If `v2` needs
different application behavior, it can dispatch a different command/query,
or the same one with a different presentation-layer mapping; the decision
of *what changed* between versions stays a presentation-layer routing/
schema concern unless the underlying use case genuinely changed too.

## Consequences

**Positive**: version is visible and cacheable at the HTTP layer (in logs,
in a browser URL bar, in a reverse-proxy routing rule); multiple versions
can run side by side indefinitely with no shared mutable state between
them; the application/domain layers never carry version-conditional logic.

**Negative**: URL-path versioning means the same logical resource has a
different URL per version, which some REST purists consider a violation of
"a resource has one URI" — accepted as a pragmatic tradeoff; it's by far
the most common and easiest-to-operate approach in practice (easy to
route, easy to deprecate, easy to document per version in OpenAPI).

## Alternatives considered

- **Header-based versioning** (e.g. `Accept: application/vnd.fastarch.v2+json`)
  (rejected as the default): more "correct" in some REST philosophies, but
  harder to test from a browser/curl, harder to route at a reverse proxy/
  CDN layer, and not meaningfully more decoupled from application code
  than path versioning — the same isolation principle applies either way.
- **No versioning, evolve in place with backward-compatible-only changes**
  (rejected as the sole strategy): fine for additive changes, but doesn't
  cover a genuine breaking change without a coordinated flag day across
  every client.
