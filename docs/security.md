# Security

## Authentication

`infrastructure/authentication/jwt.py`'s `JwtTokenService` issues and
verifies HS256 JWTs (`PyJWT`), with issuer/audience/expiry checks on
verification. `presentation/api/dependencies/auth.get_current_auth_context`
resolves the bearer token (via FastAPI's `HTTPBearer(auto_error=False)`)
into an `AuthContext` — a request with no/invalid credentials becomes
*anonymous*, not a hard 401, because whether authentication is required is
a **per-use-case** decision (`Request.required_permission`), not a
per-route one. See [`application-layer.md`](application-layer.md).

`AuthSettings.jwt_secret` (`AUTH__JWT_SECRET`) **must** be overridden in
every real environment — the default is an obvious placeholder, not a
usable secret. Rotate it via your secrets manager; never commit a real
value (see `.env.example` and the pre-commit `detect-secrets` hook).

## Authorization

Two layers:

1. **RBAC on the command/query itself** — `Request.required_permission`,
   enforced automatically by `AuthorizationBehavior` for every dispatch.
   `RenameUserCommand`/`DeactivateUserCommand` require `users:write`;
   `RegisterUserCommand`/queries are public in this template.
2. **Resource-level checks** — `infrastructure/authorization/policies.py`'s
   `can_act_on_own_resource(context, resource_owner_id, or_permission=...)`,
   called explicitly by a handler when "the caller owns this specific
   resource, or has an admin override" is the rule (not currently wired
   into the Users example, since a user has no ownership relationship to
   itself beyond identity — see the docstring in that module for where to
   use it in a new bounded context, e.g. "only the order's owner or an
   admin can cancel it").

`ROLE_PERMISSIONS` is a simple, explicit table — extend it per bounded
context rather than inventing a second authorization mechanism.

## Password hashing

`PasswordHasher` port (`application/common/interfaces/password_hasher.py`),
implemented by `Argon2PasswordHasher` (`passlib[argon2]`). Argon2 was
chosen over bcrypt/PBKDF2 as the current OWASP-recommended default for new
systems. Never hash with anything homegrown, and never log a raw password
(see [`observability.md`](observability.md) on redaction).

## CORS / trusted hosts

`SecuritySettings` (`SECURITY__CORS_ALLOW_ORIGINS`, `SECURITY__TRUSTED_HOSTS`)
— both are env-driven allowlists, wired in `main.py`'s `create_app()` via
`CORSMiddleware`/`TrustedHostMiddleware`. The `.env.example` defaults are
permissive for local development (`localhost:3000`, `*`); **lock both down
explicitly per environment** — a `TrustedHosts=["*"]` in production defeats
Host-header validation entirely.

## Secrets

- No secret is ever committed — `.env.example` documents every variable
  with an obviously-fake placeholder.
- `.pre-commit-config.yaml` runs `detect-secrets` against every commit,
  with `.secrets.baseline` recording known false positives (dev-only
  `fastarch:fastarch` compose credentials, `POSTGRES_PASSWORD` keyword
  matches, etc.) — review any *new* baseline entry carefully before
  accepting it.
- CI's "security" job re-runs `detect-secrets scan --baseline .secrets.baseline`
  and `pip-audit --strict` on every PR and on `main`.

## Dependency vulnerability scanning

`pip-audit` (PR + main CI) checks the resolved dependency set against known
CVEs. `main.yml`'s "docker" job additionally scans the *built image* with
Trivy for CRITICAL/HIGH vulnerabilities, failing the build on any unfixed
one it can't ignore.

## Request validation

Pydantic validates every request body/query param before a route body
runs (`RequestValidationError` → RFC 7807 422, see [`api.md`](api.md)).
Application-level validation (`Request.validate()`, enforced by
`ValidationBehavior`) is a second, independent layer for rules that aren't
expressible as a Pydantic field constraint.

## Docker image hardening

- Multi-stage build; the runtime image has no build toolchain, no `uv`
  binary reachable outside the builder stage's layer, no dev dependencies.
- Runs as a non-root `app` user (`Dockerfile`'s `USER app`).
- `HEALTHCHECK` hits `/health/live`, not `/health/ready` — a container that
  can't reach Postgres shouldn't be killed and restarted (see
  [`deployment.md`](deployment.md)).

## What's explicitly out of scope for this template

- OAuth2/OIDC federation with an external identity provider — the JWT
  service here issues and verifies its own tokens; swapping to "verify a
  token issued by Auth0/Okta/Cognito" means replacing `JwtTokenService.verify()`
  with a call to that provider's JWKS endpoint, behind the same interface.
- Multi-tenancy / row-level tenant isolation — add a `tenant_id` to the
  relevant aggregates and repository queries; the architecture doesn't
  prevent it, it just isn't demonstrated in the Users example.
