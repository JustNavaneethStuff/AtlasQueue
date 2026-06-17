# Architecture

See [README](../README.md) for quickstart. This document describes the system design.

## Components

1. **API** — Stateless FastAPI service. Accepts task submissions, status queries, worker registration, admin stats.
2. **Queue Manager** — Application service orchestrating Postgres + Redis dual-write.
3. **Redis** — Ready queues (LIST per priority), scheduled queue (ZSET), inflight tracking, DLQ, leader lock, cancellation set.
4. **Worker** — Competing consumers via `BRPOP`. Executes Python handlers or HTTP webhooks.
5. **Scheduler** — Leader-elected process moving due tasks from ZSET to ready queues; also runs reconcilers.
6. **PostgreSQL** — Tasks, task_events (audit log), workers.

## Dual-write flow

1. Insert task in Postgres (`pending` or `scheduled`)
2. Enqueue in Redis (ready LIST or scheduled ZSET)
3. Update Postgres status to `queued` or `scheduled`
4. On Redis failure: mark `enqueue_failed`, scheduler reconciler retries

## At-least-once delivery

Workers may see duplicate delivery after crashes. Handlers should be idempotent. Inflight TTL + reconciler requeues stuck tasks.

## Scaling

- **API**: horizontal, stateless
- **Workers**: `docker compose up --scale worker=3`
- **Scheduler**: single leader via Redis lock; standby replicas
