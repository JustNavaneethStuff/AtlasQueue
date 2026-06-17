# Atlas Queue

A production-quality distributed task queue built in Python — a portfolio project demonstrating backend engineering, distributed systems, concurrency, and infrastructure patterns.

Atlas Queue is a **lightweight alternative to Celery/Sidekiq** with a deliberate design difference: **PostgreSQL is the source of truth** for task state and audit history, while **Redis provides fast enqueue/dequeue and coordination**.

## Architecture

```
Client (SDK / HTTP)
       ↓
   REST API (FastAPI)
       ↓
  Queue Manager
       ↓
  Redis Queue ──→ Worker Pool ──→ Task Executor
       ↓                              ↓
  PostgreSQL  ←───────────────────────┘
       ↓
Monitoring (Prometheus + OpenTelemetry + Dashboard)
```

## Features

- Submit and track tasks with full status lifecycle
- Priority queues (per-priority Redis lists)
- Scheduled tasks (ZSET + leader-elected scheduler)
- Retry with fixed/exponential backoff
- Dead-letter queue with manual replay
- Dual execution: Python `@task` handlers + HTTP webhooks
- Worker registration and heartbeats
- Task cancellation and timeouts
- API key authentication
- Prometheus metrics and OpenTelemetry tracing
- React admin dashboard

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.13 (for local development)

### Run with Docker

```bash
docker compose up --build
```

Services:
- API: http://localhost:8000
- Dashboard: http://localhost:5173
- Prometheus: http://localhost:9090
- API docs: http://localhost:8000/docs

Default API key: `dev-api-key` (set via `X-API-Key` header)

### Submit a task

```bash
curl -X POST http://localhost:8000/v1/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key" \
  -d '{"name": "echo", "payload": {"message": "hello"}, "priority": 0}'
```

### Local development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
atlasqueue-api
```

## Why not Celery?

| Aspect | Celery | Atlas Queue |
|--------|--------|-------------|
| State | Broker-centric | PostgreSQL source of truth |
| Observability | Bolt-on | First-class events + metrics |
| Complexity | Large ecosystem | Focused, readable codebase |
| Audit trail | Limited | Append-only task events |

## Project structure

Clean Architecture with domain-driven folders:

- `domain/` — entities, value objects, ports
- `application/` — use cases, DTOs, services
- `infrastructure/` — Postgres, Redis, HTTP, observability
- `api/` — FastAPI routes
- `worker/` — dequeue and execute loop
- `scheduler/` — leader-elected scheduled task release
- `sdk/` — Python client and `@task` decorator

## Testing

```bash
pytest tests
ruff check src tests
mypy src/atlasqueue
```

## License

MIT
