# ADR 003: JWT Authentication with RBAC

## Status

Accepted

## Context

API key auth is simple for automation but insufficient for human operators, role separation, and interview discussions of auth design.

## Decision

Add JWT bearer tokens issued by `POST /v1/auth/login` with bcrypt-hashed credentials in Postgres. Keep API keys for backward-compatible automation (admin-equivalent).

Roles:

- `admin` — stats, DLQ replay, worker registration
- `user` — submit and cancel tasks
- `worker` — worker registration

## Alternatives

- OAuth2/OIDC only — heavier for a portfolio project
- API key only — no RBAC story

## Tradeoffs

- Extra users table and secret rotation requirements
- Dual auth paths increase middleware complexity

## Failure scenarios

- Leaked JWT — short expiry and secret rotation
- Leaked API key — rotate `API_KEY`, restrict network access

## Scalability

Stateless JWT validation scales with API replicas; user store is small and read-light.
