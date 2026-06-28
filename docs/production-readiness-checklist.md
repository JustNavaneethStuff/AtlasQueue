# Production Readiness Checklist

## Architecture and code quality

- [x] Clean architecture layers (API, application, domain, infrastructure)
- [x] Domain exception hierarchy and centralized API error handling
- [x] Shared retry/DLQ failure handler
- [x] Repository and queue backend ports used by worker/scheduler paths

## Testing

- [x] Pytest unit, API, and integration suites
- [x] Coverage gate enforced in CI (`--cov-fail-under=60`)
- [x] Redis and Postgres integration tests with skip when unavailable

## API

- [x] Versioned `/v1` routes
- [x] OpenAPI security schemes and export script
- [x] Pagination metadata, filtering, sorting
- [x] Consistent error envelope with `code` and `request_id`

## Security

- [x] JWT login with bcrypt password hashing
- [x] Role-based authorization (`admin`, `user`, `worker`)
- [x] API key compatibility with constant-time compare
- [x] Rate limiting on submit
- [x] CORS configuration and secrets via environment variables

## Observability

- [x] Structured JSON logging
- [x] Correlation/request IDs in logs and responses
- [x] Prometheus metrics and Grafana dashboard
- [x] Health and readiness endpoints
- [x] OpenTelemetry hooks

## Performance

- [x] Redis SCAN instead of KEYS
- [x] Atomic scheduled task claim
- [x] API benchmark script and performance notes

## CI/CD and deployment

- [x] GitHub Actions: lint, typecheck, tests, Docker build, security scans, compose smoke
- [x] Dependabot configuration
- [x] Hardened Docker images (non-root) and Compose with Redis AOF + Grafana

## Documentation and interview prep

- [x] README, API docs, schema docs, sequence diagrams
- [x] LICENSE, SECURITY.md, CONTRIBUTING.md
- [x] Interview system-design notes
