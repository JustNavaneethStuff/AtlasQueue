# Atlas Queue

[![CI](https://github.com/JustNavaneethStuff/AtlasQueue/actions/workflows/ci.yml/badge.svg)](https://github.com/JustNavaneethStuff/AtlasQueue/actions/workflows/ci.yml)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-quality distributed task queue built in Python — a portfolio project demonstrating backend engineering, distributed systems, concurrency, and infrastructure patterns.

Atlas Queue is a **lightweight alternative to Celery/Sidekiq** with a deliberate design difference: **PostgreSQL is the source of truth** for task state and audit history, while **Redis provides fast enqueue/dequeue and coordination**.

**Live repo:** https://github.com/JustNavaneethStuff/AtlasQueue

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

## Demo walkthrough

End-to-end flow you can demo in an interview or screen recording:

1. **Start the stack**
   ```bash
   docker compose up --build
   ```

2. **Submit tasks** (mix priorities and one failure)
   ```bash
   # High-priority echo
   curl -X POST http://localhost:8000/v1/tasks \
     -H "Content-Type: application/json" -H "X-API-Key: dev-api-key" \
     -d '{"name":"echo","payload":{"message":"hello"},"priority":0}'

   # Task that lands in DLQ after retries
   curl -X POST http://localhost:8000/v1/tasks \
     -H "Content-Type: application/json" -H "X-API-Key: dev-api-key" \
     -d '{"name":"fail_always","payload":{},"max_retries":2}'
   ```

3. **Watch lifecycle** — open http://localhost:5173
   - **Overview** — queue depths and status breakdown
   - **Tasks** — click a task for the event timeline
   - **Dead Letter** — replay failed tasks

4. **Metrics** — http://localhost:9090 or `GET /v1/metrics`

> **Tip:** Record a 60–90s screen capture of steps 2–3 for your portfolio README or LinkedIn.

## Design decisions (interview talking points)

### 1. PostgreSQL as source of truth

**Decision:** All task status reads come from Postgres; Redis is only the delivery mechanism.

**Why:** Celery often treats the broker as runtime state, which makes status queries and audit trails harder. Atlas Queue optimizes for **observability and debuggability**.

**Tradeoff:** Dual-write complexity (Postgres + Redis). Mitigated with enqueue reconciler and idempotent status transitions.

### 2. Per-priority Redis lists

**Decision:** Bounded priority levels (default 4) with one LIST per level; workers `BRPOP` highest priority first.

**Why:** Simple, fast dequeue — easy to reason about in interviews.

**Tradeoff:** Low-priority starvation under sustained high-priority load. Documented; future improvement is priority aging.

### 3. At-least-once delivery

**Decision:** Workers may redeliver after crashes between dequeue and ack.

**Why:** Standard for distributed queues; favors durability over exactly-once complexity.

**Tradeoff:** Handlers must be **idempotent**. Documented in SDK and ADRs.

### 4. Leader-elected scheduler

**Decision:** Single scheduler leader (Redis lock) moves due tasks from ZSET → ready queues.

**Why:** Avoids every API instance running schedule logic; clear separation of concerns.

**Tradeoff:** Brief failover window on leader crash. Lock TTL + renewal handles normal cases.

### 5. Dual executors (Python + webhook)

**Decision:** `@task` handlers for Python workloads; HTTP webhooks for language-agnostic integration.

**Why:** Shows both in-process concurrency and external HTTP resilience.

**Tradeoff:** Webhook SSRF risk — blocked private IPs in production config.

### 6. Clean Architecture

**Decision:** `domain` → `application` → `infrastructure`/`api`/`worker` with repository ports.

**Why:** Testable core, swappable adapters, clear boundaries for portfolio code review.

**Tradeoff:** More files than a script — intentional for demonstrating engineering discipline.

See also: [`docs/adr/`](docs/adr/) and [`docs/architecture.md`](docs/architecture.md).

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
